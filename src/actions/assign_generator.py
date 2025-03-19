import llvmlite.ir as ir

def visit_Assignment(self, node):
    """Generuje kod LLVM dla przypisania wartości do zmiennej."""
    # Pobierz wskaźnik do zmiennej z tablicy symboli
    if node.name not in self.symbol_table:
        raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
        
    var_ptr = self.symbol_table[node.name]
        
    # Oblicz wartość do przypisania
    value = self.visit(node.value)
        
    # Automatyczna konwersja typów, jeśli potrzebna
    var_type = var_ptr.type.pointee
    value_type = value.type
        
    if isinstance(var_type, ir.IntType) and isinstance(value_type, ir.FloatType):
        # Konwersja float -> int (utrata precyzji)
        value = self.builder.fptosi(value, var_type)
    elif isinstance(var_type, ir.FloatType) and isinstance(value_type, ir.IntType):
        # Konwersja int -> float
        value = self.builder.sitofp(value, var_type)
        
    # Zapisz wartość do zmiennej
    self.builder.store(value, var_ptr)