from src.syntax_tree.ast_nodes import ASTNode

class MatrixDeclaration(ASTNode):
    def __init__(self, var_type, name, rows, cols, initial_values=None):
        self.var_type = var_type
        self.name = name
        self.rows = rows
        self.cols = cols
        self.initial_values = initial_values or []

class MatrixAccess(ASTNode):
    def __init__(self, name, row_index, col_index):
        self.name = name
        self.row_index = row_index
        self.col_index = col_index

class MatrixAssignment(ASTNode):
    def __init__(self, name, row_index, col_index, value):
        self.name = name
        self.row_index = row_index
        self.col_index = col_index
        self.value = value