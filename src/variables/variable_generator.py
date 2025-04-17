def visit_Variable(self, node):
    """Generuje kod LLVM dla zmiennej."""
    if node.name not in self.symbol_table:
        raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
    
    var_ptr = self.symbol_table[node.name]
    print(f"DEBUG visit_Variable: Zmienna {node.name} typu {var_ptr.type}")
    
    # NIE ładujemy wartości tutaj, bo może to być zmienna do której będziemy przypisywać
    # Wartość zostanie załadowana w funkcjach, które jej używają
    return var_ptr