import llvmlite.ir as ir

def visit_BinaryOperation(self, node):
    # Debugowanie
    print(f"Przetwarzanie operacji binarnej: {node.operator}")
        
    # Oblicz wartości lewego i prawego operandu
    left = self.visit(node.left)
    right = self.visit(node.right)
        
    print(f"Typ wartości lewej: {left.type}")
    print(f"Typ wartości prawej: {right.type}")
        
    # Sprawdź typy operandów
    is_float_operation = isinstance(left.type, ir.FloatType) or isinstance(right.type, ir.FloatType)
    print(f"Czy operacja zmiennoprzecinkowa: {is_float_operation}")
        
    # Jeśli jeden z operandów jest float, konwertuj drugi też na float
    if is_float_operation:
        if isinstance(left.type, ir.IntType):
            print(f"Konwersja: int -> float (lewy operand)")
            left = self.builder.sitofp(left, self.float_type)
        if isinstance(right.type, ir.IntType):
            print(f"Konwersja: int -> float (prawy operand)")
            right = self.builder.sitofp(right, self.float_type)
        
        # Upewnij się, że oba operandy mają ten sam typ
        print(f"Typy po konwersji - lewy: {left.type}, prawy: {right.type}")
        
    # Wykonaj odpowiednią operację w zależności od operatora i typu
    if node.operator == '+':
        if is_float_operation:
            print("Wykonywanie operacji fadd")
            result = self.builder.fadd(left, right)
        else:
            print("Wykonywanie operacji add")
            result = self.builder.add(left, right)
    elif node.operator == '-':
        if is_float_operation:
            print("Wykonywanie operacji fsub")
            result = self.builder.fsub(left, right)
        else:
            print("Wykonywanie operacji sub")
            result = self.builder.sub(left, right)
    elif node.operator == '*':
        if is_float_operation:
            print("Wykonywanie operacji fmul")
            result = self.builder.fmul(left, right)
        else:
            print("Wykonywanie operacji mul")
            result = self.builder.mul(left, right)
    elif node.operator == '/':
        if is_float_operation:
            print("Wykonywanie operacji fdiv")
            result = self.builder.fdiv(left, right)
        else:
            print("Wykonywanie operacji sdiv")
            result = self.builder.sdiv(left, right)
    else:
        raise ValueError(f"Nieznany operator: {node.operator}")
        
    print(f"Typ wyniku operacji: {result.type}")
    return result