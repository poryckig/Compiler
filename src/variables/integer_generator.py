import llvmlite.ir as ir

def visit_IntegerLiteral(self, node):
    # Zwróć stałą całkowitą
    return ir.Constant(self.int_type, node.value)