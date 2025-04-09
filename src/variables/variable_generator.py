def visit_Variable(self, node):
    # Pobierz wskaźnik do zmiennej
    if node.name not in self.symbol_table:
        raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
        
    var_ptr = self.symbol_table[node.name]
        
    # Debugowanie
    # print(f"Odczytywanie zmiennej {node.name} typu {var_ptr.type.pointee}")
        
    # Wczytaj wartość ze zmiennej
    loaded_value = self.builder.load(var_ptr, name=f"{node.name}_val")
    # print(f"Wczytana wartość typu: {loaded_value.type}")
    return loaded_value