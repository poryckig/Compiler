def visit_Variable(self, node):
    """Generuje kod LLVM dla zmiennej."""
    try:
        var_ptr = self.find_variable(node.name)
        print(f"DEBUG visit_Variable: Zmienna {node.name} typu {var_ptr.type}")
        return var_ptr
    except ValueError as e:
        raise ValueError(f"Niezadeklarowana zmienna: {node.name}")