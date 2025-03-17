from antlr4 import ParseTreeVisitor
from src.parser.generated.langParser import langParser
from src.parser.generated.langVisitor import langVisitor
from src.syntax_tree.ast_nodes import *

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