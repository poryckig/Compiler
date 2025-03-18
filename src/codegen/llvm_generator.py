import llvmlite.ir as ir
import llvmlite.binding as llvm
import sys
from src.syntax_tree.ast_nodes import *

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
        self.double_type = ir.DoubleType()  # Dodaj typ double
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
    
    def visit_VariableDeclaration(self, node):
        # Określ typ LLVM na podstawie typu zmiennej
        if node.var_type == 'int':
            var_type = self.int_type
            default_value = ir.Constant(var_type, 0)
        elif node.var_type == 'float':
            var_type = self.float_type
            default_value = ir.Constant(var_type, 0.0)
        else:
            raise ValueError(f"Nieznany typ zmiennej: {node.var_type}")
        
        # Debugowanie
        print(f"Deklaracja zmiennej {node.name} typu {var_type}")
        
        # Alokuj zmienną na stosie
        var_ptr = self.builder.alloca(var_type, name=node.name)
        
        # Inicjalizuj zmienną zerami
        self.builder.store(default_value, var_ptr)
        print(f"Inicjalizacja zmiennej {node.name} zerami")
        
        # Zapisz wskaźnik do tablicy symboli
        self.symbol_table[node.name] = var_ptr
        
        # Jeśli jest wartość początkowa, przypisz ją
        if node.initial_value:
            print(f"Inicjalizacja zmiennej {node.name}")
            value = self.visit(node.initial_value)
            print(f"Wartość początkowa typu {value.type}")
            self.builder.store(value, var_ptr)
            print(f"Zmienna {node.name} zainicjalizowana")
    
    def visit_Assignment(self, node):
        # Pobierz wskaźnik do zmiennej z tablicy symboli
        if node.name not in self.symbol_table:
            raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
        
        var_ptr = self.symbol_table[node.name]
        
        # Oblicz i przypisz wartość
        value = self.visit(node.value)
        self.builder.store(value, var_ptr)
    
    def visit_PrintStatement(self, node):
        # Oblicz wartość do wydrukowania
        value = self.visit(node.expression)
        
        # Utwórz format string w zależności od typu wyrażenia
        if isinstance(value.type, ir.FloatType):
            # Format z nową linią i terminatorem null
            format_str = "%g\n\0"
            
            # Konwersja z float na double dla printf
            value = self.builder.fpext(value, ir.DoubleType())
            print(f"Konwersja float -> double dla printf")
        else:
            format_str = "%d\n\0"
        
        print(f"Print - typ wartości po konwersji: {value.type}, format: {format_str}")
        
        # Tworzymy unikalną globalną zmienną dla każdego wywołania printf
        c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                bytearray(format_str.encode("utf8")))
        
        # Generuj unikalną nazwę na podstawie liczby istniejących zmiennych
        format_count = 0
        for g in self.module.global_values:
            if hasattr(g, 'name') and g.name.startswith(".str"):
                format_count += 1
        
        global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                        name=f".str.{format_count}")
        global_format.linkage = 'internal'
        global_format.global_constant = True
        global_format.initializer = c_format_str
        
        # Konwertuj wskaźnik do formatu do i8*
        format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
        
        # Wywołaj printf z wartością typu double
        self.builder.call(self.printf_func, [format_ptr, value], name="printf_result")
    
    def visit_ReadStatement(self, node):
        # Pobierz wskaźnik do zmiennej
        if node.name not in self.symbol_table:
            raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
        
        var_ptr = self.symbol_table[node.name]
        
        # Określ format na podstawie typu zmiennej
        var_type = var_ptr.type.pointee
        
        # Debugowanie
        print(f"Typ zmiennej {node.name}: {var_type}")
        
        if isinstance(var_type, ir.IntType):
            format_str = "%d\0"  # Format dla liczb całkowitych
        elif isinstance(var_type, ir.FloatType):
            format_str = "%f\0"  # Format dla liczb zmiennoprzecinkowych
        else:
            # Awaryjnie użyj int jako domyślnego typu
            print(f"UWAGA: Nierozpoznany typ {var_type}, używam formatu %d")
            format_str = "%d\0"
        
        # Tworzymy globalną zmienną dla format stringa
        c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                bytearray(format_str.encode("utf8")))
        
        # Generuj unikalną nazwę na podstawie liczby istniejących zmiennych
        format_count = 0
        for g in self.module.global_values:
            if hasattr(g, 'name') and g.name.startswith(".str.scanf"):
                format_count += 1
        
        global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                         name=f".str.scanf.{format_count}")
        global_format.linkage = 'internal'
        global_format.global_constant = True
        global_format.initializer = c_format_str
        
        # Konwertuj wskaźnik do formatu do i8*
        format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
        
        # Wywołaj scanf
        self.builder.call(self.scanf_func, [format_ptr, var_ptr])
    
    def visit_BinaryOperation(self, node):
        # Debugowanie
        print(f"Przetwarzanie operacji binarnej: {node.operator}")
        print(f"Typ lewego operandu: {type(node.left).__name__}")
        print(f"Typ prawego operandu: {type(node.right).__name__}")
        
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
        
        # Wykonaj odpowiednią operację w zależności od operatora i typu
        if node.operator == '+':
            result = self.builder.fadd(left, right) if is_float_operation else self.builder.add(left, right)
            print("Wykonywanie operacji fadd" if is_float_operation else "Wykonywanie operacji add")
        elif node.operator == '-':
            result = self.builder.fsub(left, right) if is_float_operation else self.builder.sub(left, right)
            print("Wykonywanie operacji fsub" if is_float_operation else "Wykonywanie operacji sub")
        elif node.operator == '*':
            result = self.builder.fmul(left, right) if is_float_operation else self.builder.mul(left, right)
            print("Wykonywanie operacji fmul" if is_float_operation else "Wykonywanie operacji mul")
        elif node.operator == '/':
            result = self.builder.fdiv(left, right) if is_float_operation else self.builder.sdiv(left, right)
            print("Wykonywanie operacji fdiv" if is_float_operation else "Wykonywanie operacji sdiv")
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