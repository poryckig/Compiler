import llvmlite.ir as ir

def visit_VariableDeclaration(self, node):
    """Generuje kod LLVM dla deklaracji zmiennej."""
    # Określ typ LLVM na podstawie typu zmiennej
    var_type = self.get_llvm_type(node.var_type)
    
    # Debugowanie
    print(f"Deklaracja zmiennej {node.name} typu {var_type}")
    
    # Określ, czy zmienna jest globalna
    is_global = not hasattr(self, "current_function")
    
    if is_global:
        # Globalne zmienne deklarowane na poziomie modułu
        global_var = ir.GlobalVariable(self.module, var_type, name=node.name)
        global_var.linkage = 'common'
        global_var.align = 4  # Standardowe wyrównanie
        
        # Inicjalizacja wartością domyślną
        if isinstance(var_type, ir.IntType):
            default_value = ir.Constant(var_type, 0)
        elif isinstance(var_type, ir.FloatType) or isinstance(var_type, ir.DoubleType):
            default_value = ir.Constant(var_type, 0.0)
        else:
            # Dla innych typów (np. wskaźników) inicjalizacja zerami
            default_value = ir.Constant(var_type, None)
        
        global_var.initializer = default_value
        print(f"Inicjalizacja globalnej zmiennej {node.name} wartością domyślną")
        
        # Zapisz wskaźnik do globalnej tablicy symboli
        self.global_symbol_table[node.name] = global_var
        
        # Jeśli jest wartość początkowa, przypisz ją
        if node.initial_value:
            print(f"Inicjalizacja globalnej zmiennej {node.name} wartością początkową")
            
            # Utworzenie instrukcji w bloku głównym
            current_block = self.builder.block
            current_pos = self.builder.block.instructions[-1] if self.builder.block.instructions else None
            
            value = self.visit(node.initial_value)
            
            # DODANA SEKCJA: Załaduj wartość ze wskaźnika, jeśli to wskaźnik (ale nie string)
            if isinstance(value.type, ir.PointerType) and not (isinstance(value.type.pointee, ir.IntType) and value.type.pointee.width == 8):
                print(f"Ładowanie wartości ze wskaźnika typu: {value.type.pointee}")
                value = self.builder.load(value)
                print(f"Po załadowaniu typ wartości: {value.type}")
            
            # Konwersja typu, jeśli potrzebna
            if var_type != value.type:
                if isinstance(var_type, ir.IntType) and isinstance(value.type, ir.FloatType):
                    value = self.builder.fptosi(value, var_type)
                elif isinstance(var_type, ir.IntType) and isinstance(value.type, ir.DoubleType):
                    value = self.builder.fptosi(value, var_type)
                elif isinstance(var_type, ir.FloatType) and isinstance(value.type, ir.IntType):
                    value = self.builder.sitofp(value, var_type)
                elif isinstance(var_type, ir.FloatType) and isinstance(value.type, ir.DoubleType):
                    value = self.builder.fptrunc(value, var_type)
                elif isinstance(var_type, ir.DoubleType) and isinstance(value.type, ir.IntType):
                    value = self.builder.sitofp(value, var_type)
                elif isinstance(var_type, ir.DoubleType) and isinstance(value.type, ir.FloatType):
                    value = self.builder.fpext(value, var_type)
            
            # Zapisz wartość początkową
            self.builder.store(value, global_var)
            print(f"Zmienna globalna {node.name} zainicjalizowana wartością początkową")
            
        return global_var
    else:
        # Lokalne zmienne na stosie - istniejący kod bez zmian
        var_ptr = self.builder.alloca(var_type, name=node.name)
        
        # Tworzenie domyślnej wartości (0) dla odpowiedniego typu
        if isinstance(var_type, ir.IntType):
            default_value = ir.Constant(var_type, 0)
        elif isinstance(var_type, ir.FloatType):
            default_value = ir.Constant(var_type, 0.0)
        elif isinstance(var_type, ir.DoubleType):
            default_value = ir.Constant(var_type, 0.0)
        elif isinstance(var_type, ir.PointerType):
            # Dla stringa - pusty string
            empty_str = "\0"
            empty_bytes = empty_str.encode('utf-8')
            empty_type = ir.ArrayType(ir.IntType(8), len(empty_bytes))
            empty_const = ir.Constant(empty_type, bytearray(empty_bytes))
            
            global_id = f"empty_str.{next(self._global_counter)}"
            empty_global = ir.GlobalVariable(self.module, empty_type, name=global_id)
            empty_global.linkage = 'private'
            empty_global.global_constant = True
            empty_global.initializer = empty_const
            
            zero = ir.Constant(self.int_type, 0)
            default_value = self.builder.gep(empty_global, [zero, zero], name=f"{global_id}_ptr")
        else:
            raise ValueError(f"Nieznany typ zmiennej: {node.var_type}")
        
        # Inicjalizacja zmiennej wartością domyślną
        self.builder.store(default_value, var_ptr)
        print(f"Inicjalizacja zmiennej {node.name} wartością domyślną")
        
        # Zapisz wskaźnik do lokalnej tablicy symboli
        self.local_symbol_table[node.name] = var_ptr
        
        # Jeśli jest wartość początkowa, przypisz ją
        if node.initial_value:
            print(f"Inicjalizacja zmiennej {node.name} wartością początkową")
            value = self.visit(node.initial_value)
            print(f"Wartość początkowa typu {value.type}")
            
            # DODANA SEKCJA: Załaduj wartość ze wskaźnika, jeśli to wskaźnik (ale nie string)
            if isinstance(value.type, ir.PointerType) and not (isinstance(value.type.pointee, ir.IntType) and value.type.pointee.width == 8):
                print(f"Ładowanie wartości ze wskaźnika typu: {value.type.pointee}")
                value = self.builder.load(value)
                print(f"Po załadowaniu typ wartości: {value.type}")
            
            # Konwersja typu, jeśli potrzebna
            if isinstance(var_type, ir.IntType) and isinstance(value.type, ir.FloatType):
                value = self.builder.fptosi(value, var_type)
                print(f"Konwersja float -> int")
            elif isinstance(var_type, ir.IntType) and isinstance(value.type, ir.DoubleType):
                value = self.builder.fptosi(value, var_type)
                print(f"Konwersja double -> int")
            elif isinstance(var_type, ir.FloatType) and isinstance(value.type, ir.IntType):
                value = self.builder.sitofp(value, var_type)
                print(f"Konwersja int -> float")
            elif isinstance(var_type, ir.FloatType) and isinstance(value.type, ir.DoubleType):
                value = self.builder.fptrunc(value, var_type)
                print(f"Konwersja double -> float")
            elif isinstance(var_type, ir.DoubleType) and isinstance(value.type, ir.IntType):
                value = self.builder.sitofp(value, var_type)
                print(f"Konwersja int -> double")
            elif isinstance(var_type, ir.DoubleType) and isinstance(value.type, ir.FloatType):
                value = self.builder.fpext(value, var_type)
                print(f"Konwersja float -> double")
            
            # Zapisz wartość początkową
            self.builder.store(value, var_ptr)
            print(f"Zmienna {node.name} zainicjalizowana wartością początkową")
        
        return var_ptr