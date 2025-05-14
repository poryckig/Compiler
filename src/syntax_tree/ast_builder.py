from antlr4 import ParseTreeVisitor
from src.parser.generated.langParser import langParser
from src.parser.generated.langVisitor import langVisitor
from src.syntax_tree.ast_nodes import *

class ASTBuilder(langVisitor):
    def __init__(self):
        super().__init__()

    def visitProgram(self, ctx:langParser.ProgramContext):
        functions = []
        statements = []
        struct_definitions = []
        
        for child in ctx.children:
            if isinstance(child, langParser.FunctionDeclarationContext):
                func = self.visit(child)
                if func:
                    functions.append(func)
            elif isinstance(child, langParser.StructDefinitionContext):
                struct_def = self.visit(child)
                if struct_def:
                    struct_definitions.append(struct_def)
            elif isinstance(child, langParser.StatementContext):
                stmt = self.visit(child)
                if stmt:
                    statements.append(stmt)
        
        return Program(statements, functions, struct_definitions)

    def visitStatement(self, ctx:langParser.StatementContext):
        print(f"Statement children: {[ctx.getChild(i).getText() for i in range(ctx.getChildCount())]}")
        # Odwiedź bezpośrednio dziecko (variableDeclaration, assignment, itd.)
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            child_text = child.getText()
            print(f"Child {i}: {child_text}, type: {type(child).__name__}")
            if child_text.startswith('read'):
                print("Found read statement!")
            if child_text != ';':  # Pomijamy średnik
                return self.visit(child)
        return None

    def visitType(self, ctx:langParser.TypeContext):
        return ctx.getText()  # Zwróć 'int' lub 'float' jako string

    def visitParenExpr(self, ctx):
        return self.visit(ctx.expression())

    def visitExpression(self, ctx:langParser.ExpressionContext):
        """Obsługuje wyrażenia przekierowując do orExpression."""
        return self.visit(ctx.orExpression())

#           * * * * DECLARATION * * * *
    def visitSimpleVarDecl(self, ctx):
        var_type = ctx.type_().getText()
        name = ctx.ID().getText()
        
        initial_value = None
        if ctx.expression():
            initial_value = self.visit(ctx.expression())
        
        return VariableDeclaration(var_type, name, initial_value)
    
    def visitVariableDeclaration(self, ctx:langParser.VariableDeclarationContext):
        # Debugowanie
        # print("\nDebugging VariableDeclaration:")
        # print(f"getChildCount: {ctx.getChildCount()}")
        # for i in range(ctx.getChildCount()):
        #     print(f"Child {i}: {ctx.getChild(i).getText()}")
        # print(f"Has ID(): {hasattr(ctx, 'ID')}")
        # print(f"Has expression(): {hasattr(ctx, 'expression')}")
        
        type_node = ctx.getChild(0)
        var_type = type_node.getText()
        
        name = ctx.ID().getText()
        
        initial_value = None
        # Sprawdź, czy jest wyrażenie inicjalizujące
        if ctx.getChildCount() > 3:  # Jeśli jest więcej niż 3 dzieci (typ, ID, '=', expr)
            expr_ctx = ctx.expression()
            if expr_ctx:
                initial_value = self.visit(expr_ctx)
        
        return VariableDeclaration(var_type, name, initial_value)
    
#           * * * * ASSIGNMENT * * * * 
    def visitSimpleAssign(self, ctx):
        name = ctx.ID().getText()
        
        # Get the right-hand side expression
        right_side = self.visit(ctx.expression())
        
        # Check if it's a variable (potential struct-to-struct assignment)
        if isinstance(right_side, Variable):
            return StructToStructAssignment(name, right_side.name)
        
        # Regular assignment
        return Assignment(name, right_side)

    def visitAssignment(self, ctx:langParser.AssignmentContext):
        name = ctx.ID().getText()
        value = self.visit(ctx.expression())
        return Assignment(name, value)

#           * * * * BINARY OPERATIONS * * * * 
    def visitAddSubExpr(self, ctx):
        """Obsługuje dodawanie i odejmowanie."""
        # Pobierz pierwszy operand (pierwszy "multiplyingExpression")
        left = self.visit(ctx.multiplyingExpression(0))
        
        # Dla każdego operatora i operandu
        for i in range(len(ctx.children) // 2):
            # Sprawdź, czy mamy wystarczającą liczbę dzieci
            op_index = i * 2 + 1
            right_index = i * 2 + 2
            
            if op_index < len(ctx.children) and right_index < len(ctx.children):
                # Pobierz operator i prawy operand
                op = ctx.children[op_index].getText()
                right = self.visit(ctx.multiplyingExpression(i + 1))
                
                # Utwórz operację binarną
                left = BinaryOperation(left, op, right)
        
        return left

    def visitMulDivExpr(self, ctx):
        """Obsługuje mnożenie i dzielenie."""
        # Pobierz pierwszy operand (pierwszy "primaryExpression")
        left = self.visit(ctx.primaryExpression(0))
        
        # Dla każdego operatora i operandu
        for i in range(len(ctx.children) // 2):
            # Sprawdź, czy mamy wystarczającą liczbę dzieci
            op_index = i * 2 + 1
            right_index = i * 2 + 2
            
            if op_index < len(ctx.children) and right_index < len(ctx.children):
                # Pobierz operator i prawy operand
                op = ctx.children[op_index].getText()
                right = self.visit(ctx.primaryExpression(i + 1))
                
                # Utwórz operację binarną
                left = BinaryOperation(left, op, right)
        
        return left
    
#           * * * * VARIABLES * * * * 
    def visitVarExpr(self, ctx):
        name = ctx.ID().getText()
        return Variable(name)

    def visitIntLiteral(self, ctx):
        value = int(ctx.INT().getText())
        return IntegerLiteral(value)

    def visitFloatLiteral(self, ctx):
        value_text = ctx.FLOAT().getText()
        value = float(value_text)
        return FloatLiteral(value)
    
#           * * * * I/O * * * * 
    def visitPrintStatement(self, ctx:langParser.PrintStatementContext):
        expr = self.visit(ctx.expression())
        return PrintStatement(expr)

    def visitReadStatement(self, ctx:langParser.ReadStatementContext):
        print("Debug - visitReadStatement called")
        print(f"Context children: {[ctx.getChild(i).getText() for i in range(ctx.getChildCount())]}")
        name = ctx.ID().getText()
        print(f"Read statement for variable: {name}")
        return ReadStatement(name)
    
#           * * * * ARRAY * * * * 
    def visitArrayDecl(self, ctx):
        var_type = ctx.type_().getText()
        name = ctx.ID().getText()
        size = int(ctx.INT().getText())
        
        initial_values = []
        if ctx.arrayInitializer():
            # Odwiedź wszystkie wyrażenia w inicjalizatorze
            for expr_ctx in ctx.arrayInitializer().expression():
                initial_values.append(self.visit(expr_ctx))
        
        return ArrayDeclaration(var_type, name, size, initial_values)
    
    def visitArrayInitializer(self, ctx):
        values = []
        for expr_ctx in ctx.expression():
            values.append(self.visit(expr_ctx))
        return values
    
    def visitArrayAssign(self, ctx):
        name = ctx.ID().getText()
        index = self.visit(ctx.expression(0))
        value = self.visit(ctx.expression(1))
        return ArrayAssignment(name, index, value)

    def visitArrayAccessExpr(self, ctx):
        name = ctx.ID().getText()
        index = self.visit(ctx.expression())
        return ArrayAccess(name, index)
    
#           * * * * MATRIX * * * * 
    def visitMatrixDecl(self, ctx):
        var_type = ctx.type_().getText()
        name = ctx.ID().getText()
        rows = int(ctx.INT(0).getText())
        cols = int(ctx.INT(1).getText())
        
        initial_values = []
        if ctx.matrixInitializer():
            # Odwiedź wszystkie wyrażenia inicjalizujące
            for row_ctx in ctx.matrixInitializer().arrayInitializer():
                row_values = []
                for expr_ctx in row_ctx.expression():
                    row_values.append(self.visit(expr_ctx))
                initial_values.append(row_values)
        
        return MatrixDeclaration(var_type, name, rows, cols, initial_values)

    def visitMatrixAccessExpr(self, ctx):
        name = ctx.ID().getText()
        row_index = self.visit(ctx.expression(0))
        col_index = self.visit(ctx.expression(1))
        return MatrixAccess(name, row_index, col_index)

    def visitMatrixAssign(self, ctx):
        name = ctx.ID().getText()
        row_index = self.visit(ctx.expression(0))
        col_index = self.visit(ctx.expression(1))
        value = self.visit(ctx.expression(2))
        return MatrixAssignment(name, row_index, col_index, value)

    def visitMatrixRead(self, ctx):
        name = ctx.ID().getText()
        row_index = self.visit(ctx.expression(0))
        col_index = self.visit(ctx.expression(1))
        return ReadStatement(name, row_index, col_index)
    
#           * * * * STRING * * * *
    def visitStringLiteral(self, ctx):
        value = ctx.STRING().getText()
        return StringLiteral(value)
    
#           * * * * BOOL * * * *
    def visitOrExpression(self, ctx):
        left = self.visit(ctx.xorExpression(0))
        
        for i in range(1, len(ctx.xorExpression())):
            right = self.visit(ctx.xorExpression(i))
            operator = ctx.getChild(i*2 - 1).getText()  # '||' lub 'or'
            left = BinaryOperation(left, operator, right)
        
        return left

    def visitAndExpression(self, ctx):
        left = self.visit(ctx.notExpression(0))
        
        for i in range(1, len(ctx.notExpression())):
            right = self.visit(ctx.notExpression(i))
            operator = ctx.getChild(i*2 - 1).getText()  # '&&' lub 'and'
            left = BinaryOperation(left, operator, right)
        
        return left

    def visitXorExpression(self, ctx):
        left = self.visit(ctx.andExpression(0))
        
        for i in range(1, len(ctx.andExpression())):
            right = self.visit(ctx.andExpression(i))
            operator = ctx.getChild(i*2 - 1).getText()  # '^' lub 'xor'
            left = BinaryOperation(left, operator, right)
        
        return left

    def visitNotExpression(self, ctx):
        if ctx.getChildCount() == 2:  # '!' lub 'not' + expression
            operand = self.visit(ctx.notExpression())
            operator = ctx.getChild(0).getText()  # '!' lub 'not'
            return UnaryOperation(operator, operand)
        else:
            return self.visit(ctx.comparisonExpression())

    def visitComparisonExpression(self, ctx):
        left = self.visit(ctx.additiveExpression(0))
        
        if ctx.comparisonOperator():
            right = self.visit(ctx.additiveExpression(1))
            operator = ctx.comparisonOperator().getText()
            return BinaryOperation(left, operator, right)
        
        return left

    def visitAdditiveExpression(self, ctx):
        left = self.visit(ctx.multiplicativeExpression(0))
        
        for i in range(1, len(ctx.multiplicativeExpression())):
            right = self.visit(ctx.multiplicativeExpression(i))
            operator = ctx.getChild(i*2 - 1).getText()  # '+' lub '-'
            left = BinaryOperation(left, operator, right)
        
        return left

    def visitMultiplicativeExpression(self, ctx):
        left = self.visit(ctx.primaryExpression(0))
        
        for i in range(1, len(ctx.primaryExpression())):
            right = self.visit(ctx.primaryExpression(i))
            operator = ctx.getChild(i*2 - 1).getText()  # '*' lub '/'
            left = BinaryOperation(left, operator, right)
        
        return left

    def visitPrimaryExpression(self, ctx):
        # Sprawdzamy bezpośrednio, czy tekst to literał logiczny
        if ctx.getChildCount() == 1:
            text = ctx.getChild(0).getText()
            if text == 'true' or text == 'false':
                return BoolLiteral(text)
        
        if ctx.getChildCount() == 3 and ctx.getChild(0).getText() == '(':
            # Wyrażenie w nawiasach
            expressions = ctx.expression()
            if expressions:
                if isinstance(expressions, list):
                    # Jeśli expression() zwraca listę, bierzemy pierwszy element
                    return self.visit(expressions[0])
                else:
                    # Jeśli expression() nie zwraca listy, używamy go bezpośrednio
                    return self.visit(expressions)
        
        if ctx.functionCall():
            # Wywołanie funkcji
            return self.visit(ctx.functionCall())
        
        if ctx.ID():
            # Sprawdź, czy to nie jest literał logiczny
            id_text = ctx.ID().getText()
            if id_text == 'true' or id_text == 'false':
                return BoolLiteral(id_text)
            
            if ctx.getChildCount() > 1:
                if ctx.getChildCount() == 4:  # ID[expr]
                    name = ctx.ID().getText()
                    expressions = ctx.expression()
                    if isinstance(expressions, list):
                        index = self.visit(expressions[0])
                    else:
                        index = self.visit(expressions)
                    return ArrayAccess(name, index)
                else:  # ID[expr][expr]
                    name = ctx.ID().getText()
                    expressions = ctx.expression()
                    if isinstance(expressions, list):
                        row_index = self.visit(expressions[0])
                        col_index = self.visit(expressions[1])
                    else:
                        # Ten przypadek powinien być obsługiwany inaczej, bo potrzebujemy dwóch indeksów
                        raise ValueError("Niepoprawna struktura dostępu do macierzy")
                    return MatrixAccess(name, row_index, col_index)
            else:
                return Variable(ctx.ID().getText())
        
        if ctx.INT():
            return IntegerLiteral(int(ctx.INT().getText()))
        
        if ctx.FLOAT():
            return FloatLiteral(float(ctx.FLOAT().getText()))
        
        if ctx.STRING():
            return StringLiteral(ctx.STRING().getText())
        
        if ctx.BOOL():
            return BoolLiteral(ctx.BOOL().getText())
        
        # Jeśli żaden z przypadków nie pasuje, wypisz strukturę kontekstu
        print("DEBUG: Struktura primaryExpression:")
        for i in range(ctx.getChildCount()):
            print(f"Child {i}: {ctx.getChild(i).getText()}")
        if hasattr(ctx, 'expression'):
            print(f"Expression method: {ctx.expression()}")
        
        raise ValueError(f"Nieobsługiwany przypadek w primaryExpression: {ctx.getText()}")
    
    def visitBasicExpr(self, ctx):
        return self.visit(ctx.orExpression())

    def visitAssignExpr(self, ctx):
        name = ctx.ID().getText()
        value = self.visit(ctx.expression())
        return Assignment(name, value)
    
    def visitSimpleRead(self, ctx):
        print("Debug - visitSimpleRead called")
        name = ctx.ID().getText()
        print(f"Simple read for variable: {name}")
        return ReadStatement(name)
    
    def visitArrayRead(self, ctx):
        name = ctx.ID().getText()
        index = self.visit(ctx.expression())
        return ReadStatement(name, index=index)
    
    def visitIfStatement(self, ctx:langParser.IfStatementContext):
        condition = self.visit(ctx.expression())
        then_block = self.visit(ctx.blockStatement(0))
        
        else_block = None
        if ctx.getChildCount() > 5:  # Jeśli jest 'else'
            if ctx.ifStatement():  # else if
                else_block = self.visit(ctx.ifStatement())
            else:  # else { ... }
                else_block = self.visit(ctx.blockStatement(1))
        
        return IfStatement(condition, then_block, else_block)

    def visitSwitchStatement(self, ctx:langParser.SwitchStatementContext):
        expression = self.visit(ctx.expression())
        
        cases = []
        for case_ctx in ctx.switchCase():
            case_value = self.visit(case_ctx.expression())
            case_statements = []
            for stmt_ctx in case_ctx.statement():
                stmt = self.visit(stmt_ctx)
                if stmt:
                    case_statements.append(stmt)
            cases.append(SwitchCase(case_value, case_statements))
        
        default_case = None
        if ctx.defaultCase():
            default_statements = []
            for stmt_ctx in ctx.defaultCase().statement():
                stmt = self.visit(stmt_ctx)
                if stmt:
                    default_statements.append(stmt)
            default_case = DefaultCase(default_statements)
        
        return SwitchStatement(expression, cases, default_case)

    def visitBreakStatement(self, ctx:langParser.BreakStatementContext):
        return BreakStatement()

    def visitWhileStatement(self, ctx:langParser.WhileStatementContext):
        condition = self.visit(ctx.expression())
        body = self.visit(ctx.blockStatement())
        return WhileStatement(condition, body)

    def visitForStatement(self, ctx:langParser.ForStatementContext):
        # Inicjalizacja
        init = None
        if ctx.forInit():
            if ctx.forInit().variableDeclaration():
                init = self.visit(ctx.forInit().variableDeclaration())
            elif ctx.forInit().assignment():
                init = self.visit(ctx.forInit().assignment())
        
        # Warunek
        condition = None
        if ctx.expression():
            condition = self.visit(ctx.expression())
        
        # Aktualizacja
        update = None
        if ctx.forUpdate():
            update = self.visit(ctx.forUpdate().expression())
        
        # Ciało pętli
        body = self.visit(ctx.blockStatement())
        
        return ForStatement(init, condition, update, body)

    def visitBlockStatement(self, ctx:langParser.BlockStatementContext):
        statements = []
        for stmt_ctx in ctx.statement():
            stmt = self.visit(stmt_ctx)
            if stmt:
                statements.append(stmt)
        return Block(statements)

    def visitFunctionDeclaration(self, ctx:langParser.FunctionDeclarationContext):
        return_type = ctx.type_().getText()
        name = ctx.ID().getText()
        
        parameters = []
        if ctx.parameterList():
            for param_ctx in ctx.parameterList().parameter():
                param_type = param_ctx.type_().getText()
                param_name = param_ctx.ID().getText()
                parameters.append(Parameter(param_type, param_name))
        
        body = self.visit(ctx.blockStatement())
        
        return FunctionDeclaration(return_type, name, parameters, body)

    def visitFunctionCall(self, ctx:langParser.FunctionCallContext):
        name = ctx.ID().getText()
        
        arguments = []
        if ctx.argumentList():
            for expr_ctx in ctx.argumentList().expression():
                argument = self.visit(expr_ctx)
                arguments.append(argument)
        
        return FunctionCall(name, arguments)

    def visitReturnStatement(self, ctx:langParser.ReturnStatementContext):
        expression = None
        if ctx.expression():
            expression = self.visit(ctx.expression())
        
        return ReturnStatement(expression)
    
    def visitStructDefinition(self, ctx):
        name = ctx.ID().getText()
        members = []
        
        for member_ctx in ctx.structMember():
            member_type = member_ctx.type_().getText()
            member_name = member_ctx.ID().getText()
            members.append(StructMember(member_type, member_name))
        
        return StructDefinition(name, members)

    def visitStructVarDecl(self, ctx):
        struct_type = ctx.ID(0).getText()
        name = ctx.ID(1).getText()
        
        initial_value = None
        if ctx.structInitializer():
            initial_values = []
            for expr_ctx in ctx.structInitializer().expression():
                initial_values.append(self.visit(expr_ctx))
            initial_value = initial_values
        
        return StructDeclaration(struct_type, name, initial_value)

    def visitStructMemberAccess(self, ctx):
        struct_name = ctx.ID(0).getText()
        member_name = ctx.ID(1).getText()
        return StructAccess(struct_name, member_name)

    def visitStructMemberAssign(self, ctx):
        struct_name = ctx.ID(0).getText()
        member_name = ctx.ID(1).getText()
        value = self.visit(ctx.expression())
        return StructAssignment(struct_name, member_name, value)