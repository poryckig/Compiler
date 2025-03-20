import llvmlite.ir as ir

def visit_Assignment(self, node):
    """Generuje kod LLVM dla przypisania wartości do zmiennej."""
    # Sprawdź, czy zmienna jest zadeklarowana
    if node.name not in self.symbol_table:
        raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
    
    # Pobierz wskaźnik do zmiennej
    var_ptr = self.symbol_table[node.name]
    
    # Odczytaj typ zmiennej docelowej
    target_type = var_ptr.type.pointee
    
    print(f"Przypisanie do zmiennej {node.name} typu {target_type}")
    
    # Oblicz wartość do przypisania
    value = self.visit(node.value)
    print(f"Wartość do przypisania typu {value.type}")
    
    # Konwersja typu, jeśli potrzebna
    # Dla typu bool (i1) - konwersja z innych typów
    if isinstance(target_type, ir.IntType) and target_type.width == 1:
        if isinstance(value.type, ir.IntType) and value.type.width != 1:
            # Konwersja int -> bool (niezerowe wartości jako true)
            value = self.builder.icmp_unsigned('!=', value, ir.Constant(value.type, 0))
        elif isinstance(value.type, ir.FloatType):
            # Konwersja float -> bool (niezerowe wartości jako true)
            zero = ir.Constant(value.type, 0.0)
            value = self.builder.fcmp_ordered('!=', value, zero)
    # Dla typu int - konwersja z innych typów
    elif isinstance(target_type, ir.IntType):
        if isinstance(value.type, ir.IntType) and value.type.width == 1:
            # Konwersja bool -> int (true=1, false=0)
            value = self.builder.zext(value, target_type)
        elif isinstance(value.type, ir.FloatType):
            # Konwersja float -> int
            value = self.builder.fptosi(value, target_type)
    # Dla typu float - konwersja z innych typów
    elif isinstance(target_type, ir.FloatType):
        if isinstance(value.type, ir.IntType):
            if value.type.width == 1:
                # Konwersja bool -> float (true=1.0, false=0.0)
                temp_int = self.builder.zext(value, self.int_type)
                value = self.builder.sitofp(temp_int, target_type)
            else:
                # Konwersja int -> float
                value = self.builder.sitofp(value, target_type)
    
    print(f"Po konwersji typu: {value.type}")
    
    # Zapisz wartość do zmiennej
    self.builder.store(value, var_ptr)
    
    return var_ptr