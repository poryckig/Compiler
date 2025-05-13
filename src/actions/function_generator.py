import llvmlite.ir as ir

def visit_FunctionDeclaration(self, node):
    """Generuje kod LLVM dla deklaracji funkcji."""
    # Określ typ zwracany przez funkcję
    return_type = self.get_llvm_type(node.return_type)
    print(f"DEBUG: Funkcja {node.name} zwraca typ {return_type}")
    
    # Pobierz już utworzoną funkcję
    function = self.get_variable(node.name)
    
    # Zapamietaj aktualną funkcję i builder
    old_function = getattr(self, "current_function", None)
    old_builder = self.builder
    old_local_symbol_table = self.local_symbol_table.copy() if hasattr(self, "local_symbol_table") else {}
    
    # Ustaw bieżącą funkcję
    self.current_function = function
    
    # Wyczyść lokalną tablicę symboli
    self.local_symbol_table = {}
    
    # Utwórz blok wejściowy dla funkcji
    entry_block = function.append_basic_block(name="entry")
    self.builder = ir.IRBuilder(entry_block)
    
    # Utwórz zmienne na stosie dla parametrów i załaduj wartości
    param_types = [param.type for param in function.args]
    for i, param in enumerate(node.parameters):
        # Utwórz zmienną na stosie
        param_var = self.builder.alloca(param_types[i], name=param.name)
        
        # Załaduj wartość parametru do zmiennej
        self.builder.store(function.args[i], param_var)
        
        # Zapisz w lokalnej tablicy symboli
        self.local_symbol_table[param.name] = param_var
    
    # Domyślna wartość zwracana (dla void lub jeśli brak return)
    return_type = function.function_type.return_type
    if isinstance(return_type, ir.VoidType):
        default_return = None
    else:
        if isinstance(return_type, ir.IntType):
            default_return = ir.Constant(return_type, 0)
        elif isinstance(return_type, ir.FloatType) or isinstance(return_type, ir.DoubleType):
            default_return = ir.Constant(return_type, 0.0)
        else:
            default_return = None
    
    # Przetwarzanie ciała funkcji
    self.visit(node.body)
    
    # Dodaj domyślny return, jeśli blok nie jest zakończony
    if not self.builder.block.is_terminated:
        if default_return is not None:
            self.builder.ret(default_return)
        else:
            self.builder.ret_void()
    
    # Przywróć poprzedni kontekst
    self.builder = old_builder
    self.current_function = old_function
    self.local_symbol_table = old_local_symbol_table
    
    print(f"DEBUG: Funkcja {node.name} została w pełni zaimplementowana")
    
    return function

def visit_FunctionCall(self, node):
    """Generuje kod LLVM dla wywołania funkcji."""
    # Pobierz funkcję z globalnej tablicy symboli (funkcje są globalne)
    if node.name in self.global_symbol_table:
        function = self.global_symbol_table[node.name]
    else:
        try:
            # Spróbuj znaleźć funkcję przez get_variable
            function = self.get_variable(node.name)
        except ValueError:
            raise ValueError(f"Niezdefiniowana funkcja: {node.name}")
    
    # Sprawdź liczbę argumentów
    if len(node.arguments) != len(function.args):
        raise ValueError(f"Nieprawidłowa liczba argumentów dla funkcji {node.name}. Oczekiwano {len(function.args)}, otrzymano {len(node.arguments)}")
    
    # Przetwórz argumenty
    args = []
    for i, arg_expr in enumerate(node.arguments):
        arg = self.visit(arg_expr)
        
        # Jeśli argument jest wskaźnikiem, załaduj wartość
        if isinstance(arg.type, ir.PointerType) and not (isinstance(arg.type.pointee, ir.IntType) and arg.type.pointee.width == 8):
            arg = self.builder.load(arg)
        
        # Konwersja typu, jeśli potrzebna
        expected_type = function.args[i].type
        if arg.type != expected_type:
            if isinstance(expected_type, ir.IntType) and isinstance(arg.type, ir.FloatType):
                arg = self.builder.fptosi(arg, expected_type)
            elif isinstance(expected_type, ir.IntType) and isinstance(arg.type, ir.DoubleType):
                arg = self.builder.fptosi(arg, expected_type)
            elif isinstance(expected_type, ir.FloatType) and isinstance(arg.type, ir.IntType):
                arg = self.builder.sitofp(arg, expected_type)
            elif isinstance(expected_type, ir.FloatType) and isinstance(arg.type, ir.DoubleType):
                arg = self.builder.fptrunc(arg, expected_type)
            elif isinstance(expected_type, ir.DoubleType) and isinstance(arg.type, ir.IntType):
                arg = self.builder.sitofp(arg, expected_type)
            elif isinstance(expected_type, ir.DoubleType) and isinstance(arg.type, ir.FloatType):
                arg = self.builder.fpext(arg, expected_type)
        
        args.append(arg)
    
    # Wywołaj funkcję
    call = self.builder.call(function, args)
    
    # Jeśli funkcja zwraca void, a używana jest w wyrażeniu, zwróć jakąś fikcyjną wartość
    if isinstance(function.function_type.return_type, ir.VoidType):
        print(f"DEBUG: Funkcja {node.name} zwraca void")
        # Stwórz specjalną strukturę, która wskazuje, że to jest wynik funkcji void
        call.type = ir.VoidType()
    
    return call

def visit_ReturnStatement(self, node):
    """Generuje kod LLVM dla instrukcji return."""
    # Sprawdź, czy jesteśmy w funkcji
    if not hasattr(self, "current_function") or not self.current_function:
        raise ValueError("Instrukcja return poza funkcją")
    
    # Pobierz typ zwracany funkcji
    return_type = self.current_function.function_type.return_type
    
    # Obsługa return bez wyrażenia
    if node.expression is None:
        if isinstance(return_type, ir.VoidType):
            self.builder.ret_void()
        else:
            # Zwróć wartość domyślną dla danego typu
            if isinstance(return_type, ir.IntType):
                self.builder.ret(ir.Constant(return_type, 0))
            elif isinstance(return_type, ir.FloatType) or isinstance(return_type, ir.DoubleType):
                self.builder.ret(ir.Constant(return_type, 0.0))
            elif isinstance(return_type, ir.PointerType):
                # Dla wskaźników (np. stringów) zwróć wskaźnik zerowy
                null_ptr = ir.Constant(return_type, None)
                self.builder.ret(null_ptr)
            else:
                raise ValueError(f"Brak wyrażenia w return dla funkcji zwracającej {return_type}")
    else:
        # Przetwórz wyrażenie zwracane
        value = self.visit(node.expression)
        
        # Jeśli wartość jest wskaźnikiem, załaduj ją - ALE NIE DLA STRINGÓW
        if isinstance(value.type, ir.PointerType) and not (isinstance(value.type.pointee, ir.IntType) and value.type.pointee.width == 8):
            value = self.builder.load(value)
        
        # Konwersja typu, jeśli potrzebna
        if value.type != return_type:
            if isinstance(return_type, ir.IntType) and isinstance(value.type, ir.FloatType):
                value = self.builder.fptosi(value, return_type)
            elif isinstance(return_type, ir.IntType) and isinstance(value.type, ir.DoubleType):
                value = self.builder.fptosi(value, return_type)
            elif isinstance(return_type, ir.FloatType) and isinstance(value.type, ir.IntType):
                value = self.builder.sitofp(value, return_type)
            elif isinstance(return_type, ir.FloatType) and isinstance(value.type, ir.DoubleType):
                value = self.builder.fptrunc(value, return_type)
            elif isinstance(return_type, ir.DoubleType) and isinstance(value.type, ir.IntType):
                value = self.builder.sitofp(value, return_type)
            elif isinstance(return_type, ir.DoubleType) and isinstance(value.type, ir.FloatType):
                value = self.builder.fpext(value, return_type)
        
        # Zwróć wartość
        self.builder.ret(value)
    
    return None