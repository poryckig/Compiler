import llvmlite.ir as ir

def visit_BinaryOperation(self, node):
    """Generuje kod LLVM dla operacji binarnej."""
    # Debugowanie
    print(f"Przetwarzanie operacji binarnej: {node.operator}")
    
    # Dla operacji short-circuit - bez zmian
    if node.operator in ['&&', 'and']:
        return self._generate_short_circuit_and(node.left, node.right)
    elif node.operator in ['||', 'or']:
        return self._generate_short_circuit_or(node.left, node.right)
    
    # Dla pozostałych operacji, oblicz wartości lewego i prawego operandu
    left = self.visit(node.left)
    right = self.visit(node.right)
    
    print(f"DEBUG: Lewy operand typu: {left.type}")
    print(f"DEBUG: Prawy operand typu: {right.type}")
    
    # Ładuj operandy, jeśli są wskaźnikami
    if isinstance(left.type, ir.PointerType) and not (isinstance(left.type.pointee, ir.IntType) and left.type.pointee.width == 8):
        print(f"DEBUG: Ładowanie lewego operandu ze wskaźnika typu: {left.type.pointee}")
        left = self.builder.load(left)
        print(f"DEBUG: Po załadowaniu lewy operand typu: {left.type}")
    
    if isinstance(right.type, ir.PointerType) and not (isinstance(right.type.pointee, ir.IntType) and right.type.pointee.width == 8):
        print(f"DEBUG: Ładowanie prawego operandu ze wskaźnika typu: {right.type.pointee}")
        right = self.builder.load(right)
        print(f"DEBUG: Po załadowaniu prawy operand typu: {right.type}")
    
    print(f"Typ wartości lewej: {left.type}")
    print(f"Typ wartości prawej: {right.type}")
    
    # Sprawdź typy operandów
    is_float_operation = isinstance(left.type, ir.FloatType) or isinstance(right.type, ir.FloatType)
    is_double_operation = isinstance(left.type, ir.DoubleType) or isinstance(right.type, ir.DoubleType)
    
    # Nie obsługujemy operacji na stringach w uproszczonej implementacji
    if (isinstance(left.type, ir.PointerType) and left.type.pointee == ir.IntType(8)) or \
       (isinstance(right.type, ir.PointerType) and right.type.pointee == ir.IntType(8)):
        # Zwróć lewy operand jako wynik - prosta implementacja tylko dla literałów
        print("UWAGA: Operacje na stringach nie są obsługiwane w uproszczonej implementacji")
        return left
    
    print(f"Czy operacja zmiennoprzecinkowa float32: {is_float_operation}")
    print(f"Czy operacja zmiennoprzecinkowa float64: {is_double_operation}")
    
    # Dopasowanie typów dla operacji zmiennoprzecinkowych
    if is_double_operation:
        # Jeśli jedna z wartości jest double, konwertujemy drugą do double
        if isinstance(left.type, ir.IntType):
            left = self.builder.sitofp(left, self.double_type)
        elif isinstance(left.type, ir.FloatType):
            left = self.builder.fpext(left, self.double_type)
            
        if isinstance(right.type, ir.IntType):
            right = self.builder.sitofp(right, self.double_type)
        elif isinstance(right.type, ir.FloatType):
            right = self.builder.fpext(right, self.double_type)
    elif is_float_operation:
        # Jeśli jedna z wartości jest float, konwertujemy drugą do float
        if isinstance(left.type, ir.IntType):
            left = self.builder.sitofp(left, self.float_type)
            
        if isinstance(right.type, ir.IntType):
            right = self.builder.sitofp(right, self.float_type)
    
    # Operator XOR
    if node.operator == '^' or node.operator == 'xor':
        # Konwersja do typu bool (i1) jeśli potrzebna
        if isinstance(left.type, ir.FloatType) or isinstance(left.type, ir.DoubleType):
            left = self.builder.fcmp_ordered('!=', left, ir.Constant(left.type, 0.0))
        elif not isinstance(left.type, ir.IntType) or left.type.width != 1:
            left = self.builder.icmp_unsigned('!=', left, ir.Constant(left.type, 0))
            
        if isinstance(right.type, ir.FloatType) or isinstance(right.type, ir.DoubleType):
            right = self.builder.fcmp_ordered('!=', right, ir.Constant(right.type, 0.0))
        elif not isinstance(right.type, ir.IntType) or right.type.width != 1:
            right = self.builder.icmp_unsigned('!=', right, ir.Constant(right.type, 0))
        
        # XOR dla wartości boolowskich
        return self.builder.xor(left, right)
    
    # Operatory porównania
    if node.operator == '==':
        if is_double_operation or is_float_operation:
            return self.builder.fcmp_ordered('==', left, right)
        else:
            return self.builder.icmp_signed('==', left, right)
    
    elif node.operator == '!=':
        if is_double_operation or is_float_operation:
            return self.builder.fcmp_ordered('!=', left, right)
        else:
            return self.builder.icmp_signed('!=', left, right)
    
    elif node.operator == '<':
        if is_double_operation or is_float_operation:
            return self.builder.fcmp_ordered('<', left, right)
        else:
            return self.builder.icmp_signed('<', left, right)
    
    elif node.operator == '>':
        if is_double_operation or is_float_operation:
            return self.builder.fcmp_ordered('>', left, right)
        else:
            return self.builder.icmp_signed('>', left, right)
    
    elif node.operator == '<=':
        if is_double_operation or is_float_operation:
            return self.builder.fcmp_ordered('<=', left, right)
        else:
            return self.builder.icmp_signed('<=', left, right)
    
    elif node.operator == '>=':
        if is_double_operation or is_float_operation:
            return self.builder.fcmp_ordered('>=', left, right)
        else:
            return self.builder.icmp_signed('>=', left, right)
    
    # Standardowe operacje arytmetyczne
    if node.operator == '+':
        if is_double_operation:
            print("Wykonywanie operacji fadd (double)")
            result = self.builder.fadd(left, right)
        elif is_float_operation:
            print("Wykonywanie operacji fadd (float)")
            result = self.builder.fadd(left, right)
        else:
            print("Wykonywanie operacji add")
            result = self.builder.add(left, right)
    elif node.operator == '-':
        if is_double_operation:
            print("Wykonywanie operacji fsub (double)")
            result = self.builder.fsub(left, right)
        elif is_float_operation:
            print("Wykonywanie operacji fsub (float)")
            result = self.builder.fsub(left, right)
        else:
            print("Wykonywanie operacji sub")
            result = self.builder.sub(left, right)
    elif node.operator == '*':
        if is_double_operation:
            print("Wykonywanie operacji fmul (double)")
            result = self.builder.fmul(left, right)
        elif is_float_operation:
            print("Wykonywanie operacji fmul (float)")
            result = self.builder.fmul(left, right)
        else:
            print("Wykonywanie operacji mul")
            result = self.builder.mul(left, right)
    elif node.operator == '/':
        if is_double_operation:
            print("Wykonywanie operacji fdiv (double)")
            result = self.builder.fdiv(left, right)
        elif is_float_operation:
            print("Wykonywanie operacji fdiv (float)")
            result = self.builder.fdiv(left, right)
        else:
            print("Wykonywanie operacji sdiv")
            result = self.builder.sdiv(left, right)
    else:
        raise ValueError(f"Nieznany operator: {node.operator}")
    
    print(f"Typ wyniku operacji: {result.type}")
    return result

def _generate_short_circuit_and(self, left_node, right_node):
    """Generuje kod LLVM dla operacji AND z obsługą short-circuit evaluation."""
    # Pobranie pierwszego operandu
    left = self.visit(left_node)
    
    # Upewnij się, że lewy operand nie jest wskaźnikiem
    if isinstance(left.type, ir.PointerType) and not (isinstance(left.type.pointee, ir.IntType) and left.type.pointee.width == 8):
        left = self.builder.load(left)
        # print(f"Załadowano wartość ze wskaźnika. Nowy typ: {left.type}")
        
    # Short-circuit AND evaluation - jeśli lewy operand jest false,
    # nie musimy oceniać prawego operandu
    
    # Konwersja do typu bool (i1) jeśli potrzebna
    if isinstance(left.type, ir.FloatType):
        left = self.builder.fcmp_ordered('!=', left, ir.Constant(left.type, 0.0))
    elif not isinstance(left.type, ir.IntType) or left.type.width != 1:
        left = self.builder.icmp_unsigned('!=', left, ir.Constant(left.type, 0))
    
    # Tworzenie bloków dla implementacji short-circuit
    current_block = self.builder.block
    right_operand_block = self.builder.append_basic_block(name="and_right_operand")
    merge_block = self.builder.append_basic_block(name="and_merge")
    
    # Skok warunkowy - jeśli lewy operand jest false, możemy pominąć ocenę prawego
    self.builder.cbranch(left, right_operand_block, merge_block)
    
    # Blok do oceny prawego operandu
    self.builder.position_at_end(right_operand_block)
    right = self.visit(right_node)
    
    # Upewnij się, że prawy operand nie jest wskaźnikiem
    if isinstance(right.type, ir.PointerType) and not (isinstance(right.type.pointee, ir.IntType) and right.type.pointee.width == 8):
        right = self.builder.load(right)
        # print(f"Załadowano wartość ze wskaźnika. Nowy typ: {right.type}")
    
    # Konwersja do typu bool (i1) jeśli potrzebna
    if isinstance(right.type, ir.FloatType):
        right = self.builder.fcmp_ordered('!=', right, ir.Constant(right.type, 0.0))
    elif not isinstance(right.type, ir.IntType) or right.type.width != 1:
        right = self.builder.icmp_unsigned('!=', right, ir.Constant(right.type, 0))
    
    # Przejście do bloku łączącego
    self.builder.branch(merge_block)
    right_block = self.builder.block
    
    # Blok łączący wyniki
    self.builder.position_at_end(merge_block)
    
    # Utworzenie phi node dla wyboru odpowiedniej wartości
    phi = self.builder.phi(ir.IntType(1), name="and_result")
    phi.add_incoming(ir.Constant(ir.IntType(1), 0), current_block)  # Jeśli lewy operand był false
    phi.add_incoming(right, right_block)                            # Wartość z prawego operandu
    
    return phi

def _generate_short_circuit_or(self, left_node, right_node):
    """Generuje kod LLVM dla operacji OR z obsługą short-circuit evaluation."""
    # Pobranie pierwszego operandu
    left = self.visit(left_node)
    
    # Upewnij się, że lewy operand nie jest wskaźnikiem
    if isinstance(left.type, ir.PointerType) and not (isinstance(left.type.pointee, ir.IntType) and left.type.pointee.width == 8):
        left = self.builder.load(left)
        # print(f"Załadowano wartość ze wskaźnika. Nowy typ: {left.type}")
    
    # Short-circuit OR evaluation - jeśli lewy operand jest true,
    # nie musimy oceniać prawego operandu
    
    # Konwersja do typu bool (i1) jeśli potrzebna
    if isinstance(left.type, ir.FloatType):
        left = self.builder.fcmp_ordered('!=', left, ir.Constant(left.type, 0.0))
    elif not isinstance(left.type, ir.IntType) or left.type.width != 1:
        left = self.builder.icmp_unsigned('!=', left, ir.Constant(left.type, 0))
    
    # Tworzenie bloków dla implementacji short-circuit
    current_block = self.builder.block
    right_operand_block = self.builder.append_basic_block(name="or_right_operand")
    merge_block = self.builder.append_basic_block(name="or_merge")
    
    # Skok warunkowy - jeśli lewy operand jest true, możemy pominąć ocenę prawego
    self.builder.cbranch(left, merge_block, right_operand_block)
    
    # Blok do oceny prawego operandu
    self.builder.position_at_end(right_operand_block)
    right = self.visit(right_node)
    
    # Upewnij się, że prawy operand nie jest wskaźnikiem
    if isinstance(right.type, ir.PointerType) and not (isinstance(right.type.pointee, ir.IntType) and right.type.pointee.width == 8):
        right = self.builder.load(right)
        # print(f"Załadowano wartość ze wskaźnika. Nowy typ: {right.type}")
    
    # Konwersja do typu bool (i1) jeśli potrzebna
    if isinstance(right.type, ir.FloatType):
        right = self.builder.fcmp_ordered('!=', right, ir.Constant(right.type, 0.0))
    elif not isinstance(right.type, ir.IntType) or right.type.width != 1:
        right = self.builder.icmp_unsigned('!=', right, ir.Constant(right.type, 0))
    
    # Przejście do bloku łączącego
    self.builder.branch(merge_block)
    right_block = self.builder.block
    
    # Blok łączący wyniki
    self.builder.position_at_end(merge_block)
    
    # Utworzenie phi node dla wyboru odpowiedniej wartości
    phi = self.builder.phi(ir.IntType(1), name="or_result")
    phi.add_incoming(ir.Constant(ir.IntType(1), 1), current_block)  # Jeśli lewy operand był true
    phi.add_incoming(right, right_block)                            # Wartość z prawego operandu
    
    return phi