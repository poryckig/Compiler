import llvmlite.ir as ir

def visit_Assignment(self, node):
    """Generuje kod LLVM dla przypisania."""
    # Pobierz zmienną, do której przypisujemy wartość
    var_ptr = self.get_variable(node.name)
    
    # Pobierz typ zmiennej
    var_type = var_ptr.type.pointee
    
    # Oblicz wartość wyrażenia
    # Zmiana: używamy node.value zamiast node.expression
    value = self.visit(node.value)
    
    # Jeśli wartość jest wskaźnikiem, załaduj jej zawartość (z wyjątkiem stringów)
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
    
    # Przypisz wartość do zmiennej
    self.builder.store(value, var_ptr)
    
    return value