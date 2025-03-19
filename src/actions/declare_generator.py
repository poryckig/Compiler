import llvmlite.ir as ir

def visit_VariableDeclaration(self, node):
    """Generuje kod LLVM dla deklaracji zmiennej."""
    # Określ typ LLVM na podstawie typu zmiennej
    if node.var_type == 'int':
        var_type = self.int_type
        default_value = ir.Constant(var_type, 0)
    elif node.var_type == 'float':
        var_type = self.float_type
        default_value = ir.Constant(var_type, 0.0)
    elif node.var_type == 'string':
        # Dla stringa używamy wskaźnika do i8
        var_type = ir.PointerType(ir.IntType(8))
        
        # Domyślna wartość to pusty string
        empty_str = "\0"
        empty_bytes = empty_str.encode('utf-8')
        empty_type = ir.ArrayType(ir.IntType(8), len(empty_bytes))
        empty_const = ir.Constant(empty_type, bytearray(empty_bytes))
        
        # Stwórz globalną zmienną dla pustego stringa
        global_id = f"empty_str.{next(self._global_counter)}"
        empty_global = ir.GlobalVariable(self.module, empty_type, name=global_id)
        empty_global.linkage = 'private'
        empty_global.global_constant = True
        empty_global.initializer = empty_const
        
        # Domyślną wartością jest wskaźnik do pustego stringa
        zero = ir.Constant(self.int_type, 0)
        default_value = self.builder.gep(empty_global, [zero, zero], name=f"{global_id}_ptr")
    else:
        raise ValueError(f"Nieznany typ zmiennej: {node.var_type}")
    
    # Debugowanie
    print(f"Deklaracja zmiennej {node.name} typu {var_type}")
    
    # Alokuj zmienną na stosie
    var_ptr = self.builder.alloca(var_type, name=node.name)
    
    # Inicjalizuj zmienną zerami/pustym stringiem
    self.builder.store(default_value, var_ptr)
    print(f"Inicjalizacja zmiennej {node.name} zerami")
    
    # Zapisz wskaźnik do tablicy symboli
    self.symbol_table[node.name] = var_ptr
    
    # Jeśli jest wartość początkowa, przypisz ją
    if node.initial_value:
        print(f"Inicjalizacja zmiennej {node.name}")
        value = self.visit(node.initial_value)
        print(f"Wartość początkowa typu {value.type}")
        
        # Automatyczna konwersja typów, jeśli potrzebna
        if isinstance(var_type, ir.IntType) and isinstance(value.type, ir.FloatType):
            value = self.builder.fptosi(value, var_type)
        elif isinstance(var_type, ir.FloatType) and isinstance(value.type, ir.IntType):
            value = self.builder.sitofp(value, var_type)
        
        self.builder.store(value, var_ptr)
        print(f"Zmienna {node.name} zainicjalizowana")
        
    return var_ptr