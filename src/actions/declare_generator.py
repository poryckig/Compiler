import llvmlite.ir as ir

def visit_VariableDeclaration(self, node):
    # Określ typ LLVM na podstawie typu zmiennej
    if node.var_type == 'int':
        var_type = self.int_type
        default_value = ir.Constant(var_type, 0)
    elif node.var_type == 'float':
        var_type = self.float_type
        default_value = ir.Constant(var_type, 0.0)
    else:
        raise ValueError(f"Nieznany typ zmiennej: {node.var_type}")
        
    # Debugowanie
    print(f"Deklaracja zmiennej {node.name} typu {var_type}")
        
    # Alokuj zmienną na stosie
    var_ptr = self.builder.alloca(var_type, name=node.name)
        
    # Inicjalizuj zmienną zerami
    self.builder.store(default_value, var_ptr)
    print(f"Inicjalizacja zmiennej {node.name} zerami")
       
    # Zapisz wskaźnik do tablicy symboli
    self.symbol_table[node.name] = var_ptr
        
    # Jeśli jest wartość początkowa, przypisz ją
    if node.initial_value:
        print(f"Inicjalizacja zmiennej {node.name}")
        value = self.visit(node.initial_value)
        print(f"Wartość początkowa typu {value.type}")
            
            # Upewnij się, że typy są zgodne
        if isinstance(var_type, ir.FloatType) and isinstance(value.type, ir.IntType):
            value = self.builder.sitofp(value, var_type)
        elif isinstance(var_type, ir.IntType) and isinstance(value.type, ir.FloatType):
            value = self.builder.fptosi(value, var_type)
            
        self.builder.store(value, var_ptr)
        print(f"Zmienna {node.name} zainicjalizowana")
    return var_ptr       