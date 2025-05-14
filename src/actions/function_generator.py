import llvmlite.ir as ir

def visit_FunctionDeclaration(self, node):
    """Generates LLVM code for function declaration."""
    # Get the function from the global symbol table
    function = self.global_symbol_table[node.name]
    print(f"DEBUG: Function {node.name} returns type {function.function_type.return_type}")
    
    # Save current function and builder state
    old_function = getattr(self, "current_function", None)
    old_builder = self.builder
    old_local_symbol_table = self.local_symbol_table.copy() if hasattr(self, "local_symbol_table") else {}
    
    # Set current function
    self.current_function = function
    
    # Clear local symbol table
    self.local_symbol_table = {}
    
    # Create entry block for the function
    entry_block = function.append_basic_block(name="entry")
    self.builder = ir.IRBuilder(entry_block)
    
    # Save current scope
    old_scopes = self.symbol_table_stack.copy()
    old_current_scope = self.current_scope
    
    # Set new empty scope for the function
    self.symbol_table_stack = []
    self.current_scope = {}
    print(f"DEBUG: Wejście do nowego zakresu. Głębokość stosu: {len(self.symbol_table_stack)}")
    
    # Create stack variables for parameters
    for i, param in enumerate(node.parameters):
        param_type = function.args[i].type
        
        # Handle struct parameters specially
        if isinstance(param_type, ir.LiteralStructType):
            print(f"DEBUG: Creating local copy of struct parameter {param.name}")
            # Create local copy of the struct
            param_var = self.builder.alloca(param_type, name=param.name)
            
            # Copy each field from the parameter to local copy
            # Since param args are passed by value, we just store the param itself
            self.builder.store(function.args[i], param_var)
        else:
            # For non-struct parameters, just allocate and store as before
            param_var = self.builder.alloca(param_type, name=param.name)
            self.builder.store(function.args[i], param_var)
        
        # Add parameter to local symbol table
        self.add_local_variable(param.name, param_var)
    
    # Visit function body
    self.visit(node.body)
    
    # Add default return if block is not terminated
    if not self.builder.block.is_terminated:
        if isinstance(function.function_type.return_type, ir.VoidType):
            self.builder.ret_void()
        else:
            # Create a default return value based on the return type
            if isinstance(function.function_type.return_type, ir.IntType):
                default_return = ir.Constant(function.function_type.return_type, 0)
            elif isinstance(function.function_type.return_type, ir.FloatType) or isinstance(function.function_type.return_type, ir.DoubleType):
                default_return = ir.Constant(function.function_type.return_type, 0.0)
            elif isinstance(function.function_type.return_type, ir.LiteralStructType):
                # For struct return type, allocate a zero-initialized struct
                zero_struct = self.builder.alloca(function.function_type.return_type)
                default_return = self.builder.load(zero_struct)
            else:
                # For other types (like pointers), return null
                null_ptr = ir.Constant(function.function_type.return_type, None)
                default_return = null_ptr
                
            self.builder.ret(default_return)
    
    # Restore previous context
    self.builder = old_builder
    self.current_function = old_function
    self.local_symbol_table = old_local_symbol_table
    self.symbol_table_stack = old_scopes
    self.current_scope = old_current_scope
    
    return function

def visit_FunctionCall(self, node):
    """Generates LLVM code for function calls."""
    # Get the function from symbol table
    if node.name in self.global_symbol_table:
        function = self.global_symbol_table[node.name]
    else:
        try:
            function = self.get_variable(node.name)
        except ValueError:
            raise ValueError(f"Undefined function: {node.name}")
    
    # Check argument count
    if len(node.arguments) != len(function.args):
        raise ValueError(f"Wrong number of arguments for {node.name}: expected {len(function.args)}, got {len(node.arguments)}")
    
    # Process arguments
    args = []
    for i, arg_expr in enumerate(node.arguments):
        arg = self.visit(arg_expr)
        
        # If argument is a struct, handle it specially
        if isinstance(function.args[i].type, ir.LiteralStructType) and isinstance(arg.type, ir.PointerType):
            # Load the entire struct
            arg = self.builder.load(arg)
        
        # For other pointers, load the value
        elif isinstance(arg.type, ir.PointerType) and not (isinstance(arg.type.pointee, ir.IntType) and arg.type.pointee.width == 8):
            arg = self.builder.load(arg)
        
        # Type conversion
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
    
    # Call the function
    call = self.builder.call(function, args)
    
    # Handle void return type for expressions
    if isinstance(function.function_type.return_type, ir.VoidType):
        call.type = ir.VoidType()
    
    return call

def visit_ReturnStatement(self, node):
    """Generuje kod LLVM dla instrukcji return."""
    # Check if we're in a function
    if not hasattr(self, "current_function") or not self.current_function:
        raise ValueError("Instrukcja return poza funkcją")
    
    # Get the return type of the function
    return_type = self.current_function.function_type.return_type
    
    # Handle return without expression
    if node.expression is None:
        if isinstance(return_type, ir.VoidType):
            self.builder.ret_void()
        else:
            raise ValueError(f"Brak wyrażenia w return dla funkcji zwracającej {return_type}")
    else:
        # Process return expression
        value = self.visit(node.expression)
        
        # Load value if it's a pointer (including structs)
        if isinstance(value.type, ir.PointerType):
            # For structs, load the entire struct
            if isinstance(value.type.pointee, ir.LiteralStructType):
                print(f"DEBUG: Loading struct for return")
                value = self.builder.load(value)
            # For other pointers (except strings)
            elif not (isinstance(value.type.pointee, ir.IntType) and value.type.pointee.width == 8):
                value = self.builder.load(value)
        
        # Perform type conversion if needed
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
        
        # Return the value
        self.builder.ret(value)
    
    return None