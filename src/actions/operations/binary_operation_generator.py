import llvmlite.ir as ir

def visit_BinaryOperation(self, node):
    """Generuje kod LLVM dla operacji binarnej."""
    # Debugowanie
    print(f"Przetwarzanie operacji binarnej: {node.operator}")
    
    # Oblicz wartości lewego i prawego operandu
    left = self.visit(node.left)
    right = self.visit(node.right)
    
    print(f"Typ wartości lewej: {left.type}")
    print(f"Typ wartości prawej: {right.type}")
    
    # Sprawdź typy operandów
    is_float_operation = isinstance(left.type, ir.FloatType) or isinstance(right.type, ir.FloatType)
    
    # Nie obsługujemy operacji na stringach w uproszczonej implementacji
    if (isinstance(left.type, ir.PointerType) and left.type.pointee == ir.IntType(8)) or \
       (isinstance(right.type, ir.PointerType) and right.type.pointee == ir.IntType(8)):
        # Zwróć lewy operand jako wynik - prosta implementacja tylko dla literałów
        print("UWAGA: Operacje na stringach nie są obsługiwane w uproszczonej implementacji")
        return left
    
    print(f"Czy operacja zmiennoprzecinkowa: {is_float_operation}")
    
    # Wykonaj odpowiednią operację w zależności od operatora i typu
    if node.operator == '+':
        if is_float_operation:
            # Konwersja operandów
            if isinstance(left.type, ir.IntType):
                left = self.builder.sitofp(left, self.float_type)
            if isinstance(right.type, ir.IntType):
                right = self.builder.sitofp(right, self.float_type)
                
            # Wykonaj dodawanie zmiennoprzecinkowe
            print("Wykonywanie operacji fadd")
            result = self.builder.fadd(left, right)
        else:
            # Wykonaj dodawanie całkowitoliczbowe
            print("Wykonywanie operacji add")
            result = self.builder.add(left, right)
    elif node.operator == '-':
        if is_float_operation:
            # Konwersja operandów
            if isinstance(left.type, ir.IntType):
                left = self.builder.sitofp(left, self.float_type)
            if isinstance(right.type, ir.IntType):
                right = self.builder.sitofp(right, self.float_type)
                
            # Wykonaj odejmowanie zmiennoprzecinkowe
            print("Wykonywanie operacji fsub")
            result = self.builder.fsub(left, right)
        else:
            # Wykonaj odejmowanie całkowitoliczbowe
            print("Wykonywanie operacji sub")
            result = self.builder.sub(left, right)
    elif node.operator == '*':
        if is_float_operation:
            # Konwersja operandów
            if isinstance(left.type, ir.IntType):
                left = self.builder.sitofp(left, self.float_type)
            if isinstance(right.type, ir.IntType):
                right = self.builder.sitofp(right, self.float_type)
                
            # Wykonaj mnożenie zmiennoprzecinkowe
            print("Wykonywanie operacji fmul")
            result = self.builder.fmul(left, right)
        else:
            # Wykonaj mnożenie całkowitoliczbowe
            print("Wykonywanie operacji mul")
            result = self.builder.mul(left, right)
    elif node.operator == '/':
        if is_float_operation:
            # Konwersja operandów
            if isinstance(left.type, ir.IntType):
                left = self.builder.sitofp(left, self.float_type)
            if isinstance(right.type, ir.IntType):
                right = self.builder.sitofp(right, self.float_type)
                
            # Wykonaj dzielenie zmiennoprzecinkowe
            print("Wykonywanie operacji fdiv")
            result = self.builder.fdiv(left, right)
        else:
            # Wykonaj dzielenie całkowitoliczbowe
            print("Wykonywanie operacji sdiv")
            result = self.builder.sdiv(left, right)
    else:
        raise ValueError(f"Nieznany operator: {node.operator}")
    
    print(f"Typ wyniku operacji: {result.type}")
    return result