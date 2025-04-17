import llvmlite.ir as ir

def visit_FloatLiteral(self, node):
    """Generuje kod LLVM dla literału zmiennoprzecinkowego."""
    value = float(node.value)
    print(f"DEBUG visit_FloatLiteral: Tworzenie literału zmiennoprzecinkowego: {value}")
    
    # Zawsze tworzymy jako float64 dla zachowania maksymalnej precyzji
    return ir.Constant(self.double_type, value)