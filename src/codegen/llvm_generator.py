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
from src.actions.function_generator import visit_FunctionDeclaration, visit_FunctionCall, visit_ReturnStatement

from src.structure.struct_generator import visit_StructDefinition, visit_StructDeclaration, visit_StructAccess, visit_StructAssignment, visit_StructToStructAssignment

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
        
        # Słownik zmiennych globalnych (symbol table)
        self.global_symbol_table = {}
        
        # Stos tablic symboli dla zasięgów lokalnych
        self.symbol_table_stack = []
        
        # Aktualnie aktywna tablica symboli
        self.current_scope = {}
        
        # Słownik zmiennych lokalnych dla bieżącej funkcji
        self.local_symbol_table = {}
        
        # Add struct type registry
        self.struct_types = {}  # Maps struct_name -> (struct_type, [member_names], [member_types])
        
        # Licznik dla unikalnych identyfikatorów
        self._global_counter = self._make_counter()
        
        # Funkcja main
        self.setup_main_function()
        
        # Deklaracja funkcji printf i scanf
        self.declare_external_functions()
        
        # Dodaj kompatybilność, mapując symbol_table na global_symbol_table
        self.symbol_table = self.global_symbol_table

    # Nowe metody do zarządzania zasięgami
    def enter_scope(self):
        """Wejście do nowego zakresu (bloku)."""
        # Zapisz aktualny zasięg na stosie
        self.symbol_table_stack.append(self.current_scope)
        # Utwórz nowy, pusty zasięg
        self.current_scope = {}
        print(f"DEBUG: Wejście do nowego zakresu. Głębokość stosu: {len(self.symbol_table_stack)}")

    def exit_scope(self):
        """Wyjście z bieżącego zakresu."""
        if self.symbol_table_stack:
            # Przywróć poprzedni zasięg
            self.current_scope = self.symbol_table_stack.pop()
            print(f"DEBUG: Wyjście z zakresu. Głębokość stosu: {len(self.symbol_table_stack)}")
        else:
            # Jeśli stos jest pusty, to jesteśmy w zakresie globalnym
            self.current_scope = {}
            print("DEBUG: Wyjście do zakresu globalnego")

    def add_local_variable(self, name, value):
        """Dodaje zmienną do bieżącego zakresu."""
        self.current_scope[name] = value
        print(f"DEBUG: Dodano zmienną '{name}' do bieżącego zakresu")

    def find_variable(self, name):
        """Znajduje zmienną przeszukując zasięgi od najbardziej lokalnego do globalnego."""
        # Najpierw przeszukaj bieżący zasięg
        if name in self.current_scope:
            return self.current_scope[name]
        
        # Następnie przeszukaj stos zasięgów od góry do dołu
        for scope in reversed(self.symbol_table_stack):
            if name in scope:
                return scope[name]
        
        # Wreszcie sprawdź zasięg globalny
        if name in self.global_symbol_table:
            return self.global_symbol_table[name]
        
        # Jeśli nie znaleziono zmiennej, zgłoś błąd
        raise ValueError(f"Niezadeklarowana zmienna: {name}")

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
        # KROK 0: Process struct definitions
        for struct_def in node.struct_definitions:
            self.visit(struct_def)
        
        # KROK 1: Najpierw zarejestruj wszystkie funkcje (tylko deklaracje, bez implementacji)
        for func in node.functions:
            # Określ typ zwracany przez funkcję
            return_type = self.get_llvm_type(func.return_type)
            
            # Typy parametrów
            param_types = [self.get_llvm_type(param.param_type) for param in func.parameters]
            
            # Typ funkcji (typ zwracany + typy parametrów)
            func_type = ir.FunctionType(return_type, param_types)
            
            # Utwórz funkcję
            function = ir.Function(self.module, func_type, name=func.name)
            
            # Ustaw nazwy parametrów
            for i, param in enumerate(func.parameters):
                function.args[i].name = param.name
            
            # Zapisz funkcję w globalnej tablicy symboli
            self.global_symbol_table[func.name] = function
            print(f"DEBUG: Zarejestrowano funkcję {func.name} w KROKU 1")
        
        # KROK 2: Przetwórz zmienne globalne
        for stmt in node.statements:
            if isinstance(stmt, VariableDeclaration):
                self.visit(stmt)
        
        # KROK 3: Przetwórz ciała funkcji
        for func in node.functions:
            self.visit(func)
        
        # KROK 4: Przetwórz pozostałe instrukcje głównego programu
        for stmt in node.statements:
            if not isinstance(stmt, VariableDeclaration):
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
        elif type_name == 'void':
            return ir.VoidType()
        else:
            raise ValueError(f"Nieznany typ: {type_name}")
        
    def get_variable(self, name):
        """Pobiera zmienną z odpowiedniej tablicy symboli (lokalnej lub globalnej)."""
        # Najpierw szukamy w lokalnej tablicy symboli
        if hasattr(self, "local_symbol_table") and name in self.local_symbol_table:
            return self.local_symbol_table[name]
        
        # Jeśli nie znaleziono, szukamy w globalnej tablicy
        if name in self.global_symbol_table:
            return self.global_symbol_table[name]
        
        # Jeśli nie znaleziono w żadnej tablicy, zgłoś błąd
        raise ValueError(f"Niezadeklarowana zmienna: {name}")

    def set_variable(self, name, value, is_global=False):
        """Ustawia zmienną w odpowiedniej tablicy symboli."""
        if is_global or not hasattr(self, "current_function"):
            self.global_symbol_table[name] = value
        else:
            self.local_symbol_table[name] = value

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

LLVMGenerator.visit_FunctionDeclaration = visit_FunctionDeclaration
LLVMGenerator.visit_FunctionCall = visit_FunctionCall
LLVMGenerator.visit_ReturnStatement = visit_ReturnStatement

LLVMGenerator.visit_StructDefinition = visit_StructDefinition
LLVMGenerator.visit_StructDeclaration = visit_StructDeclaration
LLVMGenerator.visit_StructAccess = visit_StructAccess
LLVMGenerator.visit_StructAssignment = visit_StructAssignment
LLVMGenerator.visit_StructToStructAssignment = visit_StructToStructAssignment