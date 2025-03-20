import llvmlite.ir as ir

def visit_OrExpr(self, node):
    """Generuje kod LLVM dla operacji OR z obsługą short-circuit evaluation."""
    # Pobranie pierwszego operandu
    left = self.visit(node.left)
    
    # Short-circuit OR evaluation - jeśli lewy operand jest true,
    # nie musimy oceniać prawego operandu
    
    # Tworzenie bloków dla implementacji short-circuit
    current_block = self.builder.block
    right_operand_block = self.builder.append_basic_block(name="or_right_operand")
    merge_block = self.builder.append_basic_block(name="or_merge")
    
    # Konwersja do typu bool (i1) jeśli potrzebna
    if not isinstance(left.type, ir.IntType) or left.type.width != 1:
        left = self.builder.icmp_unsigned('!=', left, ir.Constant(left.type, 0))
    
    # Skok warunkowy - jeśli lewy operand jest true, możemy pominąć ocenę prawego
    self.builder.cbranch(left, merge_block, right_operand_block)
    
    # Blok do oceny prawego operandu
    self.builder.position_at_end(right_operand_block)
    right = self.visit(node.right)
    
    # Konwersja do typu bool (i1) jeśli potrzebna
    if not isinstance(right.type, ir.IntType) or right.type.width != 1:
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

def visit_AndExpr(self, node):
    """Generuje kod LLVM dla operacji AND z obsługą short-circuit evaluation."""
    # Pobranie pierwszego operandu
    left = self.visit(node.left)
    
    # Short-circuit AND evaluation - jeśli lewy operand jest false,
    # nie musimy oceniać prawego operandu
    
    # Tworzenie bloków dla implementacji short-circuit
    current_block = self.builder.block
    right_operand_block = self.builder.append_basic_block(name="and_right_operand")
    merge_block = self.builder.append_basic_block(name="and_merge")
    
    # Konwersja do typu bool (i1) jeśli potrzebna
    if not isinstance(left.type, ir.IntType) or left.type.width != 1:
        left = self.builder.icmp_unsigned('!=', left, ir.Constant(left.type, 0))
    
    # Skok warunkowy - jeśli lewy operand jest false, możemy pominąć ocenę prawego
    self.builder.cbranch(left, right_operand_block, merge_block)
    
    # Blok do oceny prawego operandu
    self.builder.position_at_end(right_operand_block)
    right = self.visit(node.right)
    
    # Konwersja do typu bool (i1) jeśli potrzebna
    if not isinstance(right.type, ir.IntType) or right.type.width != 1:
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

def visit_NotExpr(self, node):
    """Generuje kod LLVM dla operacji NOT."""
    # Oblicz operand
    operand = self.visit(node.operand)
    
    # Konwersja do typu bool (i1) jeśli potrzebna
    if not isinstance(operand.type, ir.IntType) or operand.type.width != 1:
        operand = self.builder.icmp_unsigned('!=', operand, ir.Constant(operand.type, 0))
    
    # Operacja NOT
    return self.builder.not_(operand)

def visit_CompareExpr(self, node):
    """Generuje kod LLVM dla operacji porównania."""
    # Oblicz wartości operandów
    left = self.visit(node.left)
    right = self.visit(node.right)
    
    # Określ typ operacji na podstawie typów operandów
    is_float_operation = isinstance(left.type, ir.FloatType) or isinstance(right.type, ir.FloatType)
    
    if is_float_operation:
        # Konwersja operandów do float jeśli potrzebna
        if isinstance(left.type, ir.IntType):
            left = self.builder.sitofp(left, self.float_type)
        if isinstance(right.type, ir.IntType):
            right = self.builder.sitofp(right, self.float_type)
        
        # Operacje porównania dla liczb zmiennoprzecinkowych
        if node.operator == '==':
            return self.builder.fcmp_ordered('==', left, right)
        elif node.operator == '!=':
            return self.builder.fcmp_ordered('!=', left, right)
        elif node.operator == '<':
            return self.builder.fcmp_ordered('<', left, right)
        elif node.operator == '>':
            return self.builder.fcmp_ordered('>', left, right)
        elif node.operator == '<=':
            return self.builder.fcmp_ordered('<=', left, right)
        elif node.operator == '>=':
            return self.builder.fcmp_ordered('>=', left, right)
    else:
        # Operacje porównania dla liczb całkowitych
        if node.operator == '==':
            return self.builder.icmp_signed('==', left, right)
        elif node.operator == '!=':
            return self.builder.icmp_signed('!=', left, right)
        elif node.operator == '<':
            return self.builder.icmp_signed('<', left, right)
        elif node.operator == '>':
            return self.builder.icmp_signed('>', left, right)
        elif node.operator == '<=':
            return self.builder.icmp_signed('<=', left, right)
        elif node.operator == '>=':
            return self.builder.icmp_signed('>=', left, right)
    
    raise ValueError(f"Nieobsługiwany operator porównania: {node.operator}")

def visit_UnaryOperation(self, node):
    """Generuje kod LLVM dla operacji jednoargumentowej."""
    # Oblicz operand
    operand = self.visit(node.operand)
    
    # Operacja negacji logicznej
    if node.operator in ['!', 'not']:
        # Konwersja do typu bool (i1) jeśli potrzebna
        if not isinstance(operand.type, ir.IntType) or operand.type.width != 1:
            operand = self.builder.icmp_unsigned('!=', operand, ir.Constant(operand.type, 0))
        
        return self.builder.not_(operand)
    
    # Operacja negacji numerycznej
    elif node.operator == '-':
        if isinstance(operand.type, ir.FloatType):
            return self.builder.fneg(operand)
        else:
            return self.builder.neg(operand)
    
    # Operacja + (która właściwie nic nie robi)
    elif node.operator == '+':
        return operand
    
    raise ValueError(f"Nieobsługiwany operator jednoargumentowy: {node.operator}")