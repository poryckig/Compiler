import llvmlite.ir as ir
import llvmlite.binding as llvm
from src.syntax_tree.ast_nodes import *

class LLVMGenerator:
    def __init__(self):
        # Inicjalizacja LLVM
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        
        # Tworzenie modułu
        self.module = ir.Module(name="program")
        
        # Przygotowanie typów
        self.int_type = ir.IntType(32)
        self.float_type = ir.FloatType()
        self.void_type = ir.VoidType()
        
        # Słownik zmiennych (symbol table)
        self.symbol_table = {}
        
        # Funkcja main
        self.setup_main_function()
        
        # Deklaracja funkcji printf i scanf
        self.declare_external_functions()
    
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
        self.printf_func = ir.Function(self.module, printf_type, name="printf")
        
        # Deklaracja scanf dla instrukcji read
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
    
    def visit_VariableDeclaration(self, node):
        # Określ typ LLVM na podstawie typu zmiennej
        if node.var_type == 'int':
            var_type = self.int_type
        elif node.var_type == 'float':
            var_type = self.float_type
        else:
            raise ValueError(f"Nieznany typ zmiennej: {node.var_type}")
        
        # Alokuj zmienną na stosie
        var_ptr = self.builder.alloca(var_type, name=node.name)
        
        # Zapisz wskaźnik do tablicy symboli
        self.symbol_table[node.name] = var_ptr
        
        # Jeśli jest wartość początkowa, przypisz ją
        if node.initial_value:
            value = self.visit(node.initial_value)
            self.builder.store(value, var_ptr)
    
    def visit_Assignment(self, node):
        # Pobierz wskaźnik do zmiennej z tablicy symboli
        if node.name not in self.symbol_table:
            raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
        
        var_ptr = self.symbol_table[node.name]
        
        # Oblicz i przypisz wartość
        value = self.visit(node.value)
        self.builder.store(value, var_ptr)
    
    def visit_PrintStatement(self, node):
        # Utwórz format string w zależności od typu wyrażenia
        # (na razie zakładamy, że wszystko jest int)
        format_str = "%d\n"  # Format dla liczb całkowitych
        c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                bytearray(format_str.encode("utf8")))
        
        # Tworzymy globalną zmienną dla format stringa
        global_format = ir.GlobalVariable(self.module, c_format_str.type, name=".str")
        global_format.linkage = 'internal'
        global_format.global_constant = True
        global_format.initializer = c_format_str
        
        # Obliczamy wartość do wydrukowania
        value = self.visit(node.expression)
        
        # Konwertuj wskaźnik do formatu do i8*
        format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
        
        # Wywołaj printf
        self.builder.call(self.printf_func, [format_ptr, value])
    
    def visit_ReadStatement(self, node):
        # Podobnie jak przy print, ale używamy scanf
        if node.name not in self.symbol_table:
            raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
        
        var_ptr = self.symbol_table[node.name]
        
        # Format string dla scanf
        format_str = "%d"  # Format dla liczb całkowitych
        c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                bytearray(format_str.encode("utf8")))
        
        # Tworzymy globalną zmienną dla format stringa
        global_format = ir.GlobalVariable(self.module, c_format_str.type, name=".str.scanf")
        global_format.linkage = 'internal'
        global_format.global_constant = True
        global_format.initializer = c_format_str
        
        # Konwertuj wskaźnik do formatu do i8*
        format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
        
        # Wywołaj scanf
        self.builder.call(self.scanf_func, [format_ptr, var_ptr])
    
    def visit_BinaryOperation(self, node):
        # Oblicz wartości lewego i prawego operandu
        left = self.visit(node.left)
        right = self.visit(node.right)
        
        # Wykonaj odpowiednią operację w zależności od operatora
        if node.operator == '+':
            return self.builder.add(left, right)
        elif node.operator == '-':
            return self.builder.sub(left, right)
        elif node.operator == '*':
            return self.builder.mul(left, right)
        elif node.operator == '/':
            return self.builder.sdiv(left, right)  # sdiv dla liczb całkowitych ze znakiem
        else:
            raise ValueError(f"Nieznany operator: {node.operator}")
    
    def visit_Variable(self, node):
        # Pobierz wskaźnik do zmiennej
        if node.name not in self.symbol_table:
            raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
        
        var_ptr = self.symbol_table[node.name]
        
        # Wczytaj wartość ze zmiennej
        return self.builder.load(var_ptr)
    
    def visit_IntegerLiteral(self, node):
        # Zwróć stałą całkowitą
        return ir.Constant(self.int_type, node.value)
    
    def visit_FloatLiteral(self, node):
        # Zwróć stałą zmiennoprzecinkową
        return ir.Constant(self.float_type, node.value)