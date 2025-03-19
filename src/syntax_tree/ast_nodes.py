class ASTNode:
    pass

class Program(ASTNode):
    def __init__(self, statements):
        self.statements = statements

class VariableDeclaration(ASTNode):
    def __init__(self, var_type, name, initial_value=None):
        self.var_type = var_type
        self.name = name
        self.initial_value = initial_value

class Assignment(ASTNode):
    def __init__(self, name, value):
        self.name = name
        self.value = value

class PrintStatement(ASTNode):
    def __init__(self, expression):
        self.expression = expression

class ReadStatement(ASTNode):
    def __init__(self, name, row_index=None, col_index=None, index=None):
        self.name = name
        self.row_index = row_index
        self.col_index = col_index
        self.index = index      # For array access
              
class BinaryOperation(ASTNode):
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

class Variable(ASTNode):
    def __init__(self, name):
        self.name = name

class IntegerLiteral(ASTNode):
    def __init__(self, value):
        self.value = value

class FloatLiteral(ASTNode):
    def __init__(self, value):
        self.value = value