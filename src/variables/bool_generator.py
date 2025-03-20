import llvmlite.ir as ir

def visit_BoolLiteral(self, node):
    """Generuje kod LLVM dla literału logicznego."""
    # Konwersja 'true'/'false' na wartości logiczne
    bool_value = 1 if node.value == 'true' else 0
    return ir.Constant(ir.IntType(1), bool_value)