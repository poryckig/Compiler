class ASTNode:
    pass

class Program:
    def __init__(self):
        self.struct_definitions = []
        self.class_definitions = []
        self.functions = []
        self.generators = []
        self.statements = []

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
        
#           * * * * IF * * * *   
class IfStatement:
    def __init__(self, condition, then_block, else_block=None):
        self.condition = condition
        self.then_block = then_block
        self.else_block = else_block  # Może być None, Block lub zagnieżdżony IfStatement

#           * * * * SWITCH * * * *   
class SwitchStatement:
    def __init__(self, expression, cases, default_case=None):
        self.expression = expression
        self.cases = cases  # Lista par (wartość, blok)
        self.default_case = default_case  # Opcjonalny blok domyślny

class SwitchCase:
    def __init__(self, value, statements):
        self.value = value
        self.statements = statements

class DefaultCase:
    def __init__(self, statements):
        self.statements = statements

class BreakStatement:
    def __init__(self):
        pass  # Nie potrzeba żadnych parametrów dla break

#           * * * * WHILE * * * * 
class WhileStatement:
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

#           * * * * FOR * * * * 
class ForStatement:
    def __init__(self, init, condition, update, body):
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body

#           * * * * BLOCK * * * * 
class Block:
    def __init__(self, statements):
        self.statements = statements if statements else []
        
#           * * * * FUNCTION * * * * 
class FunctionDeclaration:
    def __init__(self, return_type, name, parameters, body):
        self.return_type = return_type  # Typ zwracany przez funkcję
        self.name = name                # Nazwa funkcji
        self.parameters = parameters    # Lista par (typ, nazwa)
        self.body = body                # Blok kodu funkcji

class Parameter:
    def __init__(self, param_type, name):
        self.param_type = param_type
        self.name = name

class FunctionCall:
    def __init__(self, name, arguments):
        self.name = name        # Nazwa wywoływanej funkcji
        self.arguments = arguments  # Lista wyrażeń argumentów

class ReturnStatement:
    def __init__(self, expression=None):
        self.expression = expression  # Opcjonalne wyrażenie

#           * * * * STRUCT * * * * 
class StructDefinition(ASTNode):
    def __init__(self, name, members):
        self.name = name
        self.members = members  # List of StructMember objects

class StructMember(ASTNode):
    def __init__(self, member_type, name):
        self.member_type = member_type
        self.name = name

class StructDeclaration(ASTNode):
    def __init__(self, struct_type, name, initial_value=None):
        self.struct_type = struct_type  # The struct type name
        self.name = name
        self.initial_value = initial_value

class StructAccess(ASTNode):
    def __init__(self, struct_name, member_name):
        self.struct_name = struct_name
        self.member_name = member_name

class StructAssignment(ASTNode):
    def __init__(self, struct_name, field_name, value):
        self.struct_name = struct_name
        self.field_name = field_name
        self.value = value
        
class StructToStructAssignment(ASTNode):
    def __init__(self, dest_name, src_name):
        self.dest_name = dest_name
        self.src_name = src_name

#           * * * * CLASS * * * * 
class ClassDefinition(ASTNode):
    def __init__(self, name, fields, methods, constructors):
        self.name = name
        self.fields = fields      # List of class fields (similar to struct members)
        self.methods = methods    # List of class methods
        self.constructors = constructors  # List of constructors

class ClassField(ASTNode):
    def __init__(self, field_type, name):
        self.field_type = field_type
        self.name = name

class ClassMethod(ASTNode):
    def __init__(self, return_type, name, parameters, body):
        self.return_type = return_type
        self.name = name
        self.parameters = parameters
        self.body = body

class ClassConstructor(ASTNode):
    def __init__(self, name, parameters, body):
        self.name = name
        self.parameters = parameters
        self.body = body

class ClassDeclaration(ASTNode):
    def __init__(self, class_type, name, constructor_args=None):
        self.class_type = class_type
        self.name = name
        self.constructor_args = constructor_args

class ThisExpression(ASTNode):
    def __init__(self):
        pass

class ThisMemberAccess(ASTNode):
    def __init__(self, member_name):
        self.member_name = member_name

class ThisMemberAssignment(ASTNode):
    def __init__(self, member_name, value):
        self.member_name = member_name
        self.value = value

class ClassInstantiation(ASTNode):
    def __init__(self, class_name, arguments):
        self.class_name = class_name
        self.arguments = arguments

class ClassMethodCall(ASTNode):
    def __init__(self, obj_name, method_name, arguments):
        self.obj_name = obj_name
        self.method_name = method_name
        self.arguments = arguments
        
#           * * * * FUNCTION-GENERATOR * * * *         
class GeneratorDeclaration:
    def __init__(self, return_type, name, parameters, body):
        self.return_type = return_type
        self.name = name
        self.parameters = parameters or []  # Ensure it's never None
        self.body = body

class YieldStatement:
    def __init__(self, expression):
        self.expression = expression