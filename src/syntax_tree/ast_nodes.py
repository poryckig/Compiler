class ASTNode:
    pass

class Program(ASTNode):
    def __init__(self, statements):
        self.statements = statements

#           * * * * DECLARATION * * * * 
class VariableDeclaration(ASTNode):
    def __init__(self, var_type, name, initial_value=None):
        self.var_type = var_type
        self.name = name
        self.initial_value = initial_value

#           * * * * ASSIGNMENT * * * * 
class Assignment(ASTNode):
    def __init__(self, name, value):
        self.name = name
        self.value = value

#           * * * * BINARY OPERATIONS * * * * 
class BinaryOperation(ASTNode):
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

#           * * * * VARIABLES * * * * 
class Variable(ASTNode):
    def __init__(self, name):
        self.name = name

class IntegerLiteral(ASTNode):
    def __init__(self, value):
        self.value = value

class FloatLiteral(ASTNode):
    def __init__(self, value):
        self.value = value
        
#           * * * * I/O * * * * 
class PrintStatement(ASTNode):
    def __init__(self, expression):
        self.expression = expression

class ReadStatement(ASTNode):
    def __init__(self, name, row_index=None, col_index=None, index=None):
        self.name = name
        self.row_index = row_index
        self.col_index = col_index
        self.index = index      # For array access
        
#           * * * * ARRAY * * * * 
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

#           * * * * MATRIX * * * * 
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
        
#           * * * * STRING * * * *
class StringLiteral(ASTNode):
    def __init__(self, value):
        self.value = value      # Wartość łącznie z cudzysłowami
        
#           * * * * BOOL * * * *   
class BoolLiteral(ASTNode):
    def __init__(self, value):
        self.value = value
        
class UnaryOperation(ASTNode):
    def __init__(self, operator, operand):
        self.operator = operator
        self.operand = operand