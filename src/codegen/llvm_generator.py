import llvmlite.ir as ir
import llvmlite.binding as llvm
import sys
from src.syntax_tree.ast_nodes import *
from src.variables.variable_generator import visit_Variable
from src.variables.integer_generator import visit_IntegerLiteral
from src.variables.float_generator import visit_FloatLiteral
from src.actions.declare_generator import visit_VariableDeclaration
from src.actions.assign_generator import visit_Assignment
from src.actions.operations.binary_operation_generator import visit_BinaryOperation, _generate_short_circuit_and, _generate_short_circuit_or
from src.actions.operations.logical_operation_generator import visit_OrExpr, visit_AndExpr, visit_NotExpr, visit_CompareExpr, visit_UnaryOperation
from src.IO.IO_generator import visit_PrintStatement, handle_float_read, visit_ReadStatement
from src.array.array_generator import visit_ArrayDeclaration, visit_ArrayAccess, visit_ArrayAssignment
from src.matrix.matrix_generator import visit_MatrixDeclaration, visit_MatrixAccess, visit_MatrixAssignment, _emit_matrix_error_message, _check_matrix_bounds_and_store
from src.variables.string_generator import visit_StringLiteral
from src.variables.bool_generator import visit_BoolLiteral

from src.actions.control_flow_generator import visit_IfStatement, visit_SwitchStatement, visit_BreakStatement, visit_WhileStatement, visit_ForStatement, visit_Block

class LLVMGenerator:
    def __init__(self):
        # Inicjalizacja LLVM
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        
        # Tworzenie modułu
        self.module = ir.Module(name="program")
        
        # Ustaw target triple dla Windows
        if sys.platform == 'win32':
            self.module.triple = "x86_64-pc-windows-msvc"
        
        # Przygotowanie typów
        self.int_type = ir.IntType(32)
        self.float_type = ir.FloatType()      # 32-bitowy float (float32)
        self.double_type = ir.DoubleType()    # 64-bitowy float (float64)
        self.void_type = ir.VoidType()
        
        # Słownik zmiennych (symbol table)
        self.symbol_table = {}
        
        # Licznik dla unikalnych identyfikatorów
        self._global_counter = self._make_counter()
        
        # Funkcja main
        self.setup_main_function()
        
        # Deklaracja funkcji printf i scanf
        self.declare_external_functions()

    def _make_counter(self):
        """Pomocnicza funkcja do generowania unikalnych identyfikatorów."""
        counter = 0
        while True:
            yield counter
            counter += 1
    
    def setup_main_function(self):
        # Definicja funkcji main
        func_type = ir.FunctionType(self.int_type, [])
        self.main_func = ir.Function(self.module, func_type, name="main")
        
        # Blok wejściowy
        self.entry_block = self.main_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(self.entry_block)
    
    def declare_external_functions(self):
        # Deklaracja printf dla instrukcji print
        printf_type = ir.FunctionType(
            self.int_type, [ir.PointerType(ir.IntType(8))], var_arg=True
        )
        self.printf_func = ir.Function(self.module, printf_type, name="my_printf")
        
        # Deklaracja scanf dla instrukcji read
        scanf_type = ir.FunctionType(
            self.int_type, [ir.PointerType(ir.IntType(8))], var_arg=True
        )
        self.scanf_func = ir.Function(self.module, scanf_type, name="my_scanf")
    
    def generate(self, ast):
        # Generowanie kodu z AST
        self.visit(ast)
        
        # Dodanie return 0 na końcu main
        self.builder.ret(ir.Constant(self.int_type, 0))
        
        # Zwróć wygenerowany LLVM IR jako string
        return str(self.module)
    
    def visit(self, node):
        # Wzorzec Visitor dla różnych typów węzłów AST
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node):
        raise NotImplementedError(f"No visit method for {type(node).__name__}")

    # Implementacje metod wizytatora dla różnych typów węzłów
    
    def visit_Program(self, node):
        # Odwiedź wszystkie instrukcje programu
        for stmt in node.statements:
            self.visit(stmt)
            
    def get_llvm_type(self, type_name):
        """Zwraca typ LLVM odpowiadający nazwie typu z języka."""
        print(f"DEBUG get_llvm_type: Mapowanie typu {type_name}")
        if type_name == 'int':
            return self.int_type
        elif type_name == 'float' or type_name == 'float32':
            return self.float_type
        elif type_name == 'float64':
            return self.double_type
        elif type_name == 'bool':
            return ir.IntType(1)
        elif type_name == 'string':
            return ir.PointerType(ir.IntType(8))
        else:
            raise ValueError(f"Nieznany typ: {type_name}")

# Przypisanie metod do klasy
LLVMGenerator.visit_Variable = visit_Variable
LLVMGenerator.visit_IntegerLiteral = visit_IntegerLiteral
LLVMGenerator.visit_FloatLiteral = visit_FloatLiteral

LLVMGenerator.visit_VariableDeclaration = visit_VariableDeclaration
LLVMGenerator.visit_Assignment = visit_Assignment

LLVMGenerator.visit_BinaryOperation = visit_BinaryOperation
    
LLVMGenerator.visit_PrintStatement = visit_PrintStatement
LLVMGenerator.visit_ReadStatement = visit_ReadStatement
    
LLVMGenerator.visit_ArrayDeclaration = visit_ArrayDeclaration
LLVMGenerator.visit_ArrayAccess = visit_ArrayAccess
LLVMGenerator.visit_ArrayAssignment = visit_ArrayAssignment    
        
LLVMGenerator.visit_MatrixDeclaration = visit_MatrixDeclaration
LLVMGenerator.visit_MatrixAccess = visit_MatrixAccess
LLVMGenerator.visit_MatrixAssignment = visit_MatrixAssignment
LLVMGenerator._emit_matrix_error_message = _emit_matrix_error_message
LLVMGenerator._check_matrix_bounds_and_store = _check_matrix_bounds_and_store

LLVMGenerator.visit_StringLiteral = visit_StringLiteral

LLVMGenerator.visit_BoolLiteral = visit_BoolLiteral

LLVMGenerator.visit_OrExpr = visit_OrExpr
LLVMGenerator.visit_AndExpr = visit_AndExpr
LLVMGenerator.visit_NotExpr = visit_NotExpr
LLVMGenerator.visit_CompareExpr = visit_CompareExpr
LLVMGenerator.visit_UnaryOperation = visit_UnaryOperation

LLVMGenerator._generate_short_circuit_and = _generate_short_circuit_and
LLVMGenerator._generate_short_circuit_or = _generate_short_circuit_or

LLVMGenerator.handle_float_read = handle_float_read

LLVMGenerator.visit_IfStatement = visit_IfStatement
LLVMGenerator.visit_SwitchStatement = visit_SwitchStatement
LLVMGenerator.visit_BreakStatement = visit_BreakStatement
LLVMGenerator.visit_WhileStatement = visit_WhileStatement
LLVMGenerator.visit_ForStatement = visit_ForStatement
LLVMGenerator.visit_Block = visit_Block