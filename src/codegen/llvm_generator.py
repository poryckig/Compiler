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

from src.classs.class_generator import (
    visit_ClassDefinition, _register_class_method, _register_class_constructor,
    visit_ClassDeclaration, visit_ThisExpression, visit_ThisMemberAccess,
    visit_ThisMemberAssignment, visit_ClassInstantiation, visit_ClassMethodCall,
    _implement_class_method
)

from src.generator.generator_generator import (
    visit_GeneratorDeclaration, 
    _create_generator_next_function, 
    _find_yield_statements, 
    visit_YieldStatement,
    visit_GeneratorIterator
)

class LLVMGenerator:
    def __init__(self):
        # Initialize LLVM
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        
        # Create module
        self.module = ir.Module(name="program")
        
        # Set target triple for Windows
        if sys.platform == 'win32':
            self.module.triple = "x86_64-pc-windows-msvc"
        
        # Prepare types
        self.int_type = ir.IntType(32)
        self.float_type = ir.FloatType()      # 32-bit float (float32)
        self.double_type = ir.DoubleType()    # 64-bit float (float64)
        self.void_type = ir.VoidType()
        
        # Global symbol table dictionary
        self.global_symbol_table = {}
        
        # Symbol table scope stack
        self.symbol_table_stack = []
        
        # Currently active symbol table
        self.current_scope = {}
        
        # Local variable dictionary for current function
        self.local_symbol_table = {}
        
        # Add struct type registry
        self.struct_types = {}  # Maps struct_name -> (struct_type, [member_names], [member_types])
        
        self.class_types = {}  # Maps class_name -> (class_type, [field_names], [field_types])
        self.class_methods = {}  # Maps class_name -> {method_name -> function}
        self.class_constructors = {}  # Maps class_name -> {constructor_name -> function}
        self.current_class = None  # Current class being processed
        self.current_method = None  # Current method being processed
        self.this_ptr = None  # Current 'this' pointer
        
        # Counter for unique identifiers
        self._global_counter = self._make_counter()
        
        # Flag to track if we've found a main function
        self.has_main_function = False
        
        # Create a dummy global initialization function for global variables
        self._create_global_init_function()
        
        # Declare external functions
        self.declare_external_functions()
        
        # For compatibility, map symbol_table to global_symbol_table
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
        # Only create main if it doesn't exist in the source code
        if "main" not in self.global_symbol_table:
            # Definition of the main function
            func_type = ir.FunctionType(self.int_type, [])
            self.main_func = ir.Function(self.module, func_type, name="main")
            
            # Entry block
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
        # Generate code from AST
        self.visit(ast)
        
        # Finish the global init function
        self.builder.ret_void()
        
        # If we didn't find a main function, create a default one
        if not self.has_main_function:
            print("DEBUG: Creating default main function")
            # Define main function
            func_type = ir.FunctionType(self.int_type, [])
            self.main_func = ir.Function(self.module, func_type, name="main")
            
            # Entry block
            entry_block = self.main_func.append_basic_block(name="entry")
            self.builder = ir.IRBuilder(entry_block)
            
            # Call global init function
            self.builder.call(self.global_init_func, [])
            
            # Add return 0 to the end of main
            self.builder.ret(ir.Constant(self.int_type, 0))
        else:
            # If we have a user-defined main, add the global init call to it
            # Find all basic blocks in the main function
            main_func = self.global_symbol_table["main"]
            main_entry = main_func.basic_blocks[0]
            
            # Save the current builder
            old_builder = self.builder
            
            # Create a new builder at the start of the main function
            self.builder = ir.IRBuilder()
            self.builder.position_at_start(main_entry)
            
            # Add call to global init
            self.builder.call(self.global_init_func, [])
            
            # Restore old builder
            self.builder = old_builder
        
        # Return generated LLVM IR as string
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
        # KROK 0: Process struct and class definitions first
        for struct_def in node.struct_definitions:
            self.visit(struct_def)
        
        for class_def in node.class_definitions:
            self.visit(class_def)
        
        # KROK 1: Register all functions (declarations only, no implementation)
        for func in node.functions:
            # Check if this is the main function
            if func.name == "main":
                self.has_main_function = True
                
            # Determine return type
            return_type = self.get_llvm_type(func.return_type)
            
            # Parameter types
            param_types = [self.get_llvm_type(param.param_type) for param in func.parameters]
            
            # Function type (return type + parameter types)
            func_type = ir.FunctionType(return_type, param_types)
            
            # Create function
            function = ir.Function(self.module, func_type, name=func.name)
            
            # If this is main, save reference to it
            if func.name == "main":
                self.main_func = function
            
            # Set parameter names
            for i, param in enumerate(func.parameters):
                function.args[i].name = param.name
            
            # Store function in global symbol table
            self.global_symbol_table[func.name] = function
            print(f"DEBUG: Registered function {func.name} in STEP 1")
        
        # KROK 1.5: Register all generators
        for generator in node.generators:
            try:
                print(f"DEBUG: Registering generator: {generator.name}")
                
                # For simplicity in this initial implementation, treat generators as regular functions
                # that return their yield type
                return_type = self.get_llvm_type(generator.return_type)
                
                # Ensure parameters is never None
                if not hasattr(generator, 'parameters') or generator.parameters is None:
                    generator.parameters = []
                    print(f"WARNING: Generator {generator.name} has no parameters")
                
                # Parameter types
                param_types = []
                for param in generator.parameters:
                    print(f"DEBUG: Generator parameter: {param.name} of type {param.param_type}")
                    param_type = self.get_llvm_type(param.param_type)
                    param_types.append(param_type)
                
                # Create function type
                func_type = ir.FunctionType(return_type, param_types)
                
                # Create function
                function = ir.Function(self.module, func_type, name=generator.name)
                
                # Set parameter names
                for i, param in enumerate(generator.parameters):
                    function.args[i].name = param.name
                
                # Store function in global symbol table
                self.global_symbol_table[generator.name] = function
                print(f"DEBUG: Successfully registered generator {generator.name}")
                
            except Exception as e:
                print(f"ERROR registering generator {generator.name}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # KROK 2: Process global variables
        for stmt in node.statements:
            if isinstance(stmt, VariableDeclaration):
                self.visit(stmt)
        
        # KROK 3: Process function bodies
        for func in node.functions:
            self.visit(func)
        
        # KROK 4: Process generator bodies
        for generator in node.generators:
            try:
                self.visit(generator)
            except Exception as e:
                print(f"ERROR processing generator {generator.name}: {str(e)}")
        
        # KROK 5: Process remaining main program statements
        for stmt in node.statements:
            if not isinstance(stmt, VariableDeclaration):
                self.visit(stmt)
                
    def get_llvm_type(self, type_name):
        """Returns the LLVM type corresponding to the language type name."""
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
        elif type_name in self.struct_types:
            # Return struct type if it's a registered struct
            struct_type, _, _ = self.struct_types[type_name]
            return struct_type
        elif type_name in self.class_types:
            # Return class type if it's a registered class
            class_type, _, _ = self.class_types[type_name]
            return class_type
        else:
            # Add debug output to help diagnose issues
            print(f"DEBUG: Available struct types: {list(self.struct_types.keys())}")
            print(f"DEBUG: Available class types: {list(self.class_types.keys())}")
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
            
    def _create_global_init_function(self):
        """Create a dummy function to initialize global variables."""
        # Define a global initialization function
        func_type = ir.FunctionType(self.void_type, [])
        self.global_init_func = ir.Function(self.module, func_type, name=".global_init")
        
        # Create entry block
        entry_block = self.global_init_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(entry_block)
        
        # This function will be filled with global variable initializations
        # And closed at the end of code generation

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

LLVMGenerator.visit_ClassDefinition = visit_ClassDefinition
LLVMGenerator._register_class_method = _register_class_method
LLVMGenerator._register_class_constructor = _register_class_constructor
LLVMGenerator.visit_ClassDeclaration = visit_ClassDeclaration
LLVMGenerator.visit_ThisExpression = visit_ThisExpression
LLVMGenerator.visit_ThisMemberAccess = visit_ThisMemberAccess
LLVMGenerator.visit_ThisMemberAssignment = visit_ThisMemberAssignment
LLVMGenerator.visit_ClassInstantiation = visit_ClassInstantiation
LLVMGenerator.visit_ClassMethodCall = visit_ClassMethodCall
LLVMGenerator._implement_class_method = _implement_class_method

LLVMGenerator.visit_GeneratorDeclaration = visit_GeneratorDeclaration
LLVMGenerator._create_generator_next_function = _create_generator_next_function
LLVMGenerator._find_yield_statements = _find_yield_statements
LLVMGenerator.visit_YieldStatement = visit_YieldStatement
LLVMGenerator.visit_GeneratorIterator = visit_GeneratorIterator