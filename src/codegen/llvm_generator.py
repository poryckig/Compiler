import llvmlite.ir as ir
import llvmlite.binding as llvm
import sys
from src.actions.declare_generator import visit_VariableDeclaration
from src.actions.assign_generator import visit_Assignment
from src.syntax_tree.ast_nodes import *
from src.IO.IO_nodes import *
from src.IO.IO_generator import visit_PrintStatement, visit_ReadStatement
from src.array.array_nodes import *
from src.array.array_generator import visit_ArrayDeclaration, visit_ArrayAccess, visit_ArrayAssignment
from src.matrix.matrix_nodes import *
from src.matrix.matrix_generator import visit_MatrixDeclaration, visit_MatrixAccess, visit_MatrixAssignment, _emit_matrix_error_message, _check_matrix_bounds_and_store

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
        self.float_type = ir.FloatType()
        self.double_type = ir.DoubleType()
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
        # Deklaracja printf dla instrukcji print - bez prefiksu podkreślenia
        printf_type = ir.FunctionType(
            self.int_type, [ir.PointerType(ir.IntType(8))], var_arg=True
        )
        self.printf_func = ir.Function(self.module, printf_type, name="printf")
        
        # Deklaracja scanf dla instrukcji read - bez prefiksu podkreślenia
        scanf_type = ir.FunctionType(
            self.int_type, [ir.PointerType(ir.IntType(8))], var_arg=True
        )
        self.scanf_func = ir.Function(self.module, scanf_type, name="scanf")
    
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
    
    def visit_BinaryOperation(self, node):
        # Debugowanie
        print(f"Przetwarzanie operacji binarnej: {node.operator}")
        
        # Oblicz wartości lewego i prawego operandu
        left = self.visit(node.left)
        right = self.visit(node.right)
        
        print(f"Typ wartości lewej: {left.type}")
        print(f"Typ wartości prawej: {right.type}")
        
        # Sprawdź typy operandów
        is_float_operation = isinstance(left.type, ir.FloatType) or isinstance(right.type, ir.FloatType)
        print(f"Czy operacja zmiennoprzecinkowa: {is_float_operation}")
        
        # Jeśli jeden z operandów jest float, konwertuj drugi też na float
        if is_float_operation:
            if isinstance(left.type, ir.IntType):
                print(f"Konwersja: int -> float (lewy operand)")
                left = self.builder.sitofp(left, self.float_type)
            if isinstance(right.type, ir.IntType):
                print(f"Konwersja: int -> float (prawy operand)")
                right = self.builder.sitofp(right, self.float_type)
        
            # Upewnij się, że oba operandy mają ten sam typ
            print(f"Typy po konwersji - lewy: {left.type}, prawy: {right.type}")
        
        # Wykonaj odpowiednią operację w zależności od operatora i typu
        if node.operator == '+':
            if is_float_operation:
                print("Wykonywanie operacji fadd")
                result = self.builder.fadd(left, right)
            else:
                print("Wykonywanie operacji add")
                result = self.builder.add(left, right)
        elif node.operator == '-':
            if is_float_operation:
                print("Wykonywanie operacji fsub")
                result = self.builder.fsub(left, right)
            else:
                print("Wykonywanie operacji sub")
                result = self.builder.sub(left, right)
        elif node.operator == '*':
            if is_float_operation:
                print("Wykonywanie operacji fmul")
                result = self.builder.fmul(left, right)
            else:
                print("Wykonywanie operacji mul")
                result = self.builder.mul(left, right)
        elif node.operator == '/':
            if is_float_operation:
                print("Wykonywanie operacji fdiv")
                result = self.builder.fdiv(left, right)
            else:
                print("Wykonywanie operacji sdiv")
                result = self.builder.sdiv(left, right)
        else:
            raise ValueError(f"Nieznany operator: {node.operator}")
        
        print(f"Typ wyniku operacji: {result.type}")
        return result
    
    def visit_Variable(self, node):
        # Pobierz wskaźnik do zmiennej
        if node.name not in self.symbol_table:
            raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
        
        var_ptr = self.symbol_table[node.name]
        
        # Debugowanie
        print(f"Odczytywanie zmiennej {node.name} typu {var_ptr.type.pointee}")
        
        # Wczytaj wartość ze zmiennej
        loaded_value = self.builder.load(var_ptr, name=f"{node.name}_val")
        print(f"Wczytana wartość typu: {loaded_value.type}")
        return loaded_value
    
    def visit_IntegerLiteral(self, node):
        # Zwróć stałą całkowitą
        return ir.Constant(self.int_type, node.value)
    
    def visit_FloatLiteral(self, node):
        # Debugowanie
        print(f"Tworzenie literału zmiennoprzecinkowego: {node.value}")
        
        # Konwersja do poprawnej wartości float
        float_value = float(node.value)
        print(f"Wartość po konwersji: {float_value}")
        
        # Zwróć stałą zmiennoprzecinkową
        constant = ir.Constant(self.float_type, float_value)
        print(f"Tworzę stałą zmiennoprzecinkową typu: {constant.type}")
        return constant

LLVMGenerator.visit_VariableDeclaration = visit_VariableDeclaration
LLVMGenerator.visit_Assignment = visit_Assignment
    
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