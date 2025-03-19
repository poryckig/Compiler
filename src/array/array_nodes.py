from src.syntax_tree.ast_nodes import ASTNode

class ArrayDeclaration(ASTNode):
    def __init__(self, var_type, name, size, initial_values=None):
        self.var_type = var_type
        self.name = name
        self.size = size
        self.initial_values = initial_values or []

class ArrayAccess(ASTNode):
    def __init__(self, name, index):
        self.name = name
        self.index = index

class ArrayAssignment(ASTNode):
    def __init__(self, name, index, value):
        self.name = name
        self.index = index
        self.value = value