import llvmlite.ir as ir

def visit_GeneratorDeclaration(self, node):
    """Generates LLVM IR for a generator function declaration."""
    print(f"DEBUG: Implementing generator {node.name}")
    
    # Get the function from the global symbol table
    if node.name not in self.global_symbol_table:
        raise ValueError(f"Generator {node.name} not found in global symbol table")
    
    function = self.global_symbol_table[node.name]
    
    # Save current function and builder state
    old_function = getattr(self, "current_function", None)
    old_builder = self.builder
    
    # Set current function
    self.current_function = function
    
    # Create entry block for the function
    entry_block = function.append_basic_block(name="entry")
    self.builder = ir.IRBuilder(entry_block)
    
    # Create stack variables for parameters
    local_params = {}
    for i, param in enumerate(node.parameters):
        param_type = function.args[i].type
        param_var = self.builder.alloca(param_type, name=param.name)
        self.builder.store(function.args[i], param_var)
        
        # Add parameter to local symbol table
        self.add_local_variable(param.name, param_var)
        local_params[param.name] = param_var
    
    # In this implementation, we'll just return the first parameter
    # This is still a simplification but slightly more advanced
    if node.parameters:
        # For a generator with parameters, return the first parameter
        param_name = node.parameters[0].name
        param_var = local_params[param_name]
        value = self.builder.load(param_var)
        self.builder.ret(value)
    else:
        # If no parameters, return 0
        return_type = function.function_type.return_type
        zero = ir.Constant(return_type, 0)
        self.builder.ret(zero)
    
    # Restore previous context
    self.builder = old_builder
    self.current_function = old_function
    
    return function

def _create_generator_next_function(self, name, state_struct, yield_type, body):
    """Creates the 'next' function for the generator that advances to the next value."""
    # Function type: bool, value = next(state_ptr)
    return_type = ir.LiteralStructType([ir.IntType(1), yield_type])
    func_type = ir.FunctionType(
        return_type,
        [ir.PointerType(state_struct)]
    )
    
    function = ir.Function(self.module, func_type, name=name)
    
    # Set parameter name
    function.args[0].name = "state_ptr"
    
    # Create blocks for state machine
    entry_block = function.append_basic_block(name="entry")
    finished_block = function.append_basic_block(name="finished")
    
    # Create yield blocks
    yield_points = self._find_yield_statements(body)
    yield_blocks = {}
    for i, yield_point in enumerate(yield_points, 1):
        yield_blocks[i] = function.append_basic_block(name=f"yield_{i}")
    
    # Create the main builder
    builder = ir.IRBuilder(entry_block)
    
    # Load current state
    state_ptr = function.args[0]
    state_field_ptr = builder.gep(state_ptr, [
        ir.Constant(ir.IntType(32), 0),
        ir.Constant(ir.IntType(32), 0)
    ], name="state_field")
    current_state = builder.load(state_field_ptr, name="current_state")
    
    # Create switch for state machine
    switch = builder.switch(current_state, finished_block)
    
    # Add cases for yield points
    for i, yield_block in yield_blocks.items():
        switch.add_case(ir.Constant(ir.IntType(32), i), yield_block)
    
    # Default case - initial state (0)
    initial_block = function.append_basic_block(name="initial")
    switch.add_case(ir.Constant(ir.IntType(32), 0), initial_block)
    
    # Finished block - return {false, default value}
    builder.position_at_end(finished_block)
    false_value = ir.Constant(ir.IntType(1), 0)
    default_value = ir.Constant(yield_type, 0)
    result = builder.alloca(return_type, name="result")
    done_field = builder.gep(result, [
        ir.Constant(ir.IntType(32), 0),
        ir.Constant(ir.IntType(32), 0)
    ])
    value_field = builder.gep(result, [
        ir.Constant(ir.IntType(32), 0),
        ir.Constant(ir.IntType(32), 1)
    ])
    builder.store(false_value, done_field)
    builder.store(default_value, value_field)
    result_val = builder.load(result)
    builder.ret(result_val)
    
    # Initial block - start the generator code
    builder.position_at_end(initial_block)
    # Here we would handle the actual generator body, processing until we hit a yield
    # For simplicity, just yield a value right away
    
    true_value = ir.Constant(ir.IntType(1), 1)
    test_value = ir.Constant(yield_type, 42)  # Placeholder value
    result = builder.alloca(return_type, name="result")
    done_field = builder.gep(result, [
        ir.Constant(ir.IntType(32), 0),
        ir.Constant(ir.IntType(32), 0)
    ])
    value_field = builder.gep(result, [
        ir.Constant(ir.IntType(32), 0),
        ir.Constant(ir.IntType(32), 1)
    ])
    builder.store(true_value, done_field)
    builder.store(test_value, value_field)
    result_val = builder.load(result)
    builder.ret(result_val)
    
    # Save the function to global symbol table
    self.global_symbol_table[name] = function
    
    return function

def _find_yield_statements(self, node):
    """Find all yield statements in the function body."""
    # This is a placeholder - you'll need to implement a proper visitor
    # to find all yield statements in the AST
    yield_points = []
    return yield_points

def visit_YieldStatement(self, node):
    """Simplified yield implementation that just returns the value."""
    print(f"DEBUG: Processing yield statement")
    
    # Make sure we're in a generator function
    if not hasattr(self, "current_function") or not self.current_function:
        raise ValueError("Yield statement outside of generator function")
    
    # Process yield expression
    value = self.visit(node.expression)
    
    # Load value if it's a pointer
    if isinstance(value.type, ir.PointerType) and not (
            isinstance(value.type.pointee, ir.IntType) and value.type.pointee.width == 8):
        value = self.builder.load(value)
    
    # Return the value (in a simplified implementation)
    self.builder.ret(value)
    
    return None

def visit_GeneratorIterator(self, node):
    """Generates LLVM code to iterate over a generator."""
    # Get the generator
    generator_ptr = self.visit(node.generator)
    
    # Create basic blocks for the loop
    cond_block = self.builder.append_basic_block("iter_cond")
    body_block = self.builder.append_basic_block("iter_body")
    end_block = self.builder.append_basic_block("iter_end")
    
    # Jump to condition block
    self.builder.branch(cond_block)
    
    # Condition block - call next() and check if done
    self.builder.position_at_end(cond_block)
    
    # Get next function pointer from generator
    next_func_ptr_ptr = self.builder.gep(generator_ptr, [
        ir.Constant(ir.IntType(32), 0),
        ir.Constant(ir.IntType(32), 1)
    ], name="next_func_ptr_ptr")
    next_func_ptr = self.builder.load(next_func_ptr_ptr, name="next_func_ptr")
    
    # Get state pointer from generator
    state_ptr_ptr = self.builder.gep(generator_ptr, [
        ir.Constant(ir.IntType(32), 0),
        ir.Constant(ir.IntType(32), 0)
    ], name="state_ptr_ptr")
    state_ptr = self.builder.load(state_ptr_ptr, name="state_ptr")
    
    # Call next function
    result = self.builder.call(next_func_ptr, [state_ptr], name="next_result")
    
    # Extract done flag and value
    result_type = result.type
    done_ptr = self.builder.extract_value(result, 0, name="done")
    value = self.builder.extract_value(result, 1, name="value")
    
    # Store value in iterator variable if provided
    if hasattr(node, 'variable'):
        var_ptr = self.get_variable(node.variable)
        self.builder.store(value, var_ptr)
    
    # Branch based on done flag
    self.builder.cbranch(done_ptr, body_block, end_block)
    
    # Body block - user provided code
    self.builder.position_at_end(body_block)
    
    # Visit body statements if any
    if hasattr(node, 'body'):
        self.visit(node.body)
    
    # Jump back to condition
    self.builder.branch(cond_block)
    
    # End block - loop is done
    self.builder.position_at_end(end_block)
    
    return None