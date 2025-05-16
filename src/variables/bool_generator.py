import llvmlite.ir as ir

def visit_BoolLiteral(self, node):
    """Generates LLVM code for boolean literals."""
    print(f"DEBUG: Generating boolean literal: {node.value}")
    
    # Create a constant of i1 type (LLVM's boolean type)
    value = 1 if node.value == True else 0
    return ir.Constant(ir.IntType(1), value)