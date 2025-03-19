from antlr4 import ParseTreeVisitor
from src.parser.generated.langParser import langParser
from src.parser.generated.langVisitor import langVisitor
from src.syntax_tree.ast_nodes import *
from src.array.array_nodes import *
from src.matrix.matrix_nodes import *

class ASTBuilder(langVisitor):
    def __init__(self):
        super().__init__()

    def visitProgram(self, ctx:langParser.ProgramContext):
        statements = []
        for stmt_ctx in ctx.statement():
            stmt = self.visit(stmt_ctx)
            if stmt:
                statements.append(stmt)
        return Program(statements)

    def visitStatement(self, ctx:langParser.StatementContext):
        # Odwiedź bezpośrednio dziecko (variableDeclaration, assignment, itd.)
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            if child.getText() != ';':  # Pomijamy średnik
                return self.visit(child)
        return None

    def visitVariableDeclaration(self, ctx:langParser.VariableDeclarationContext):
        # Debugowanie
        print("\nDebugging VariableDeclaration:")
        print(f"getChildCount: {ctx.getChildCount()}")
        for i in range(ctx.getChildCount()):
            print(f"Child {i}: {ctx.getChild(i).getText()}")
        print(f"Has ID(): {hasattr(ctx, 'ID')}")
        print(f"Has expression(): {hasattr(ctx, 'expression')}")
        
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

    def visitType(self, ctx:langParser.TypeContext):
        return ctx.getText()  # Zwróć 'int' lub 'float' jako string

    def visitAssignment(self, ctx:langParser.AssignmentContext):
        name = ctx.ID().getText()
        value = self.visit(ctx.expression())
        return Assignment(name, value)

    def visitPrintStatement(self, ctx:langParser.PrintStatementContext):
        expr = self.visit(ctx.expression())
        return PrintStatement(expr)

    def visitReadStatement(self, ctx:langParser.ReadStatementContext):
        name = ctx.ID().getText()
        return ReadStatement(name)

    def visitExpression(self, ctx:langParser.ExpressionContext):
        # Obsługa nawiasów
        if ctx.getChildCount() == 3 and ctx.getChild(0).getText() == '(':
            return self.visit(ctx.expression(0))
        
        # Obsługa identyfikatorów i literałów
        if ctx.ID():
            return Variable(ctx.ID().getText())
        if ctx.INT():
            return IntegerLiteral(int(ctx.INT().getText()))
        if ctx.FLOAT():
            return FloatLiteral(float(ctx.FLOAT().getText()))
        
        # Obsługa operacji binarnych
        if ctx.getChildCount() == 3 and len(ctx.expression()) == 2:
            left = self.visit(ctx.expression(0))
            right = self.visit(ctx.expression(1))
            op = ctx.getChild(1).getText()
            return BinaryOperation(left, op, right)
        
        # Jeśli żaden z powyższych przypadków nie pasuje, 
        # delegujemy do standardowej implementacji
        return self.visitChildren(ctx)
    ###############################################
    def visitSimpleVarDecl(self, ctx):
        var_type = ctx.type_().getText()
        name = ctx.ID().getText()
        
        initial_value = None
        if ctx.expression():
            initial_value = self.visit(ctx.expression())
        
        return VariableDeclaration(var_type, name, initial_value)

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

    def visitSimpleAssign(self, ctx):
        name = ctx.ID().getText()
        value = self.visit(ctx.expression())
        return Assignment(name, value)

    def visitArrayAssign(self, ctx):
        name = ctx.ID().getText()
        index = self.visit(ctx.expression(0))
        value = self.visit(ctx.expression(1))
        return ArrayAssignment(name, index, value)

    def visitArrayAccessExpr(self, ctx):
        name = ctx.ID().getText()
        index = self.visit(ctx.expression())
        return ArrayAccess(name, index)

    # Zaktualizuj pozostałe metody dla wyrażeń
    def visitMulDivExpr(self, ctx):
        left = self.visit(ctx.expression(0))
        right = self.visit(ctx.expression(1))
        op = ctx.getChild(1).getText()
        return BinaryOperation(left, op, right)

    def visitAddSubExpr(self, ctx):
        left = self.visit(ctx.expression(0))
        right = self.visit(ctx.expression(1))
        op = ctx.getChild(1).getText()
        return BinaryOperation(left, op, right)

    def visitParenExpr(self, ctx):
        return self.visit(ctx.expression())

    def visitVarExpr(self, ctx):
        name = ctx.ID().getText()
        return Variable(name)

    def visitIntLiteral(self, ctx):
        value = int(ctx.INT().getText())
        return IntegerLiteral(value)

    def visitFloatLiteral(self, ctx):
        value = float(ctx.FLOAT().getText())
        return FloatLiteral(value)
    
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