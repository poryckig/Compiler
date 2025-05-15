import llvmlite.ir as ir
from src.syntax_tree.ast_nodes import ThisMemberAccess

def visit_ClassDefinition(self, node):
    """Generates LLVM code for class definition."""
    print(f"DEBUG: Defining class {node.name}")
    
    # Create a list of LLVM types for the class fields
    field_types = []
    field_names = []
    
    for field in node.fields:
        field_type = self.get_llvm_type(field.field_type)
        field_types.append(field_type)
        field_names.append(field.name)
    
    # Create the class type as a struct type
    class_type = ir.LiteralStructType(field_types)
    
    # Store the class type and member information in both dictionaries
    # This is crucial - we need it in both places
    self.class_types[node.name] = (class_type, field_names, field_types)
    self.struct_types[node.name] = (class_type, field_names, field_types)  # Add to struct_types too!
    
    # Register methods (deklaracje)
    for method in node.methods:
        self._register_class_method(node.name, method)
    
    # Register constructors
    for constructor in node.constructors:
        self._register_class_constructor(node.name, constructor)
    
    print(f"DEBUG: Class {node.name} defined with fields: {field_names}")
    
    # Generate method implementations (now we'll add actual code for methods)
    for method in node.methods:
        self._implement_class_method(node.name, method)
    
    return class_type

def _implement_class_method(self, class_name, method):
    """Generates the implementation for a class method."""
    # Get the method from the class method table
    if class_name not in self.class_methods or method.name not in self.class_methods[class_name]:
        raise ValueError(f"Method {method.name} not registered for class {class_name}")
    
    function = self.class_methods[class_name][method.name]
    full_method_name = f"{class_name}.{method.name}"
    
    print(f"DEBUG: Implementing method {full_method_name}")
    
    # Save current builder and function state
    old_builder = self.builder
    old_function = getattr(self, "current_function", None)
    old_local_symbol_table = self.local_symbol_table.copy() if hasattr(self, "local_symbol_table") else {}
    old_class = getattr(self, "current_class", None)
    old_this_ptr = getattr(self, "this_ptr", None)
    
    # Set current function and class
    self.current_function = function
    self.current_class = class_name  # WAŻNE: ustawiamy aktualną klasę
    
    # Clear local symbol table
    self.local_symbol_table = {}
    
    # Create entry block for the function
    entry_block = function.append_basic_block(name="entry")
    self.builder = ir.IRBuilder(entry_block)
    
    # Save current scope
    old_scopes = self.symbol_table_stack.copy()
    old_current_scope = self.current_scope.copy() if hasattr(self, "current_scope") else {}
    
    # Set new empty scope for the function
    self.symbol_table_stack = []
    self.current_scope = {}
    
    # Get the class type information to ensure proper typing
    class_type, _, _ = self.class_types[class_name]
    
    # Create stack variable for 'this' parameter
    # Ważne - arg[0] jest wskaźnikiem do struktury klasy, więc nie potrzebujemy dodatkowego poziomu wskaźnika
    this_ptr = function.args[0]  # Używamy bezpośrednio argumentu
    
    # Store 'this' pointer in different places to ensure it's available
    self.this_ptr = this_ptr
    self.current_scope["this"] = this_ptr
    self.local_symbol_table["this"] = this_ptr
    
    # Process other parameters
    for i, param in enumerate(method.parameters):
        param_type = function.args[i+1].type
        param_var = self.builder.alloca(param_type, name=param.name)
        self.builder.store(function.args[i+1], param_var)
        
        # Add parameter to local symbol table
        self.add_local_variable(param.name, param_var)
        self.local_symbol_table[param.name] = param_var
    
    # Visit method body
    self.visit(method.body)
    
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
    self.current_class = old_class
    self.this_ptr = old_this_ptr
    
    return function

def _register_class_method(self, class_name, method):
    """Registers a class method in the symbol table."""
    # Create method name (class_name.method_name)
    full_method_name = f"{class_name}.{method.name}"
    
    # Determine return type
    return_type = self.get_llvm_type(method.return_type)
    
    # Add 'this' pointer as first parameter
    class_type, _, _ = self.class_types[class_name]
    this_type = ir.PointerType(class_type)  # Wskaźnik do klasy
    
    # Parameter types
    param_types = [this_type]  # 'this' pointer
    param_types.extend([self.get_llvm_type(param.param_type) for param in method.parameters])
    
    # Create function type
    func_type = ir.FunctionType(return_type, param_types)
    
    # Create function
    function = ir.Function(self.module, func_type, name=full_method_name)
    
    # Set names for parameters
    function.args[0].name = "this"
    for i, param in enumerate(method.parameters):
        function.args[i+1].name = param.name
    
    # Store in symbol table
    self.global_symbol_table[full_method_name] = function
    
    # Store method in class method table
    if class_name not in self.class_methods:
        self.class_methods[class_name] = {}
    self.class_methods[class_name][method.name] = function
    
    return function

def _register_class_constructor(self, class_name, constructor):
    """Registers a class constructor in the symbol table."""
    # Create constructor name (class_name.class_name)
    constructor_name = f"{class_name}.{constructor.name}"
    
    # Constructor return type is pointer to class type
    class_type, field_names, field_types = self.class_types[class_name]
    return_type = ir.PointerType(class_type)
    
    # Parameter types
    param_types = [self.get_llvm_type(param.param_type) for param in constructor.parameters]
    
    # Create function type
    func_type = ir.FunctionType(return_type, param_types)
    
    # Create function
    function = ir.Function(self.module, func_type, name=constructor_name)
    
    # Set names for parameters
    for i, param in enumerate(constructor.parameters):
        function.args[i].name = param.name
    
    # Store in symbol table
    self.global_symbol_table[constructor_name] = function
    
    # Store in global symbol table with just the class name too
    # This is essential for handling Point(...) constructor calls
    self.global_symbol_table[class_name] = function
    
    # Store constructor in class constructor table
    if class_name not in self.class_constructors:
        self.class_constructors[class_name] = {}
    self.class_constructors[class_name][constructor.name] = function
    
    # Now fill the constructor function body
    entry_block = function.append_basic_block(name="entry")
    builder = ir.IRBuilder(entry_block)
    
    # Save the current builder
    old_builder = self.builder
    self.builder = builder
    
    # Allocate memory for the new object
    obj_ptr = self.builder.alloca(class_type, name="this_obj")
    
    # Save current context
    old_scopes = self.symbol_table_stack.copy()
    old_current_scope = self.current_scope.copy()  # Make a copy
    old_class = getattr(self, "current_class", None)
    old_method = getattr(self, "current_method", None)
    old_local_symbol_table = self.local_symbol_table.copy() if hasattr(self, "local_symbol_table") else {}
    old_this_ptr = getattr(self, "this_ptr", None)  # Save previous this_ptr
    
    # Set up new context for constructor body
    self.symbol_table_stack = []
    self.current_scope = {}
    self.current_class = class_name
    self.current_method = function
    self.local_symbol_table = {}
    self.this_ptr = obj_ptr  # Store this directly in instance
    
    # Add 'this' to multiple locations to be sure
    self.current_scope["this"] = obj_ptr  # Add to current scope
    self.local_symbol_table["this"] = obj_ptr  # Add to local symbol table
    
    print(f"DEBUG: Setting this_ptr to {obj_ptr}")
    
    # Store parameters in the symbol table to make them accessible
    for i, param in enumerate(constructor.parameters):
        param_var = self.builder.alloca(param_types[i], name=param.name)
        self.builder.store(function.args[i], param_var)
        self.current_scope[param.name] = param_var  # Store directly in current_scope
        self.local_symbol_table[param.name] = param_var  # And also in local_symbol_table
    
    # Execute the constructor body
    if constructor.body:
        self.visit(constructor.body)
    
    # Restore the old context
    self.symbol_table_stack = old_scopes
    self.current_scope = old_current_scope
    self.current_class = old_class
    self.current_method = old_method
    self.local_symbol_table = old_local_symbol_table
    self.this_ptr = old_this_ptr  # Restore previous this_ptr
    
    # Return the allocated object
    self.builder.ret(obj_ptr)
    
    # Restore the old builder
    self.builder = old_builder
    
    return function

def visit_ClassDeclaration(self, node):
    """Generates LLVM code for class variable declaration."""
    print(f"DEBUG: Declaring class variable {node.name} of type {node.class_type}")
    
    # Get the class type
    if node.class_type not in self.class_types:
        raise ValueError(f"Undefined class type: {node.class_type}")
    
    class_type, field_names, field_types = self.class_types[node.class_type]
    
    # Allocate memory for the instance itself
    instance_ptr = self.builder.alloca(class_type, name=node.name)
    
    # If we have constructor arguments, call the constructor
    if node.constructor_args:
        print(f"DEBUG: Calling constructor with args: {node.constructor_args}")
        
        # Get constructor function
        constructor_name = node.class_type
        if constructor_name not in self.global_symbol_table:
            raise ValueError(f"Constructor not found for class {node.class_type}")
        
        constructor = self.global_symbol_table[constructor_name]
        
        # Process arguments
        args = []
        for arg_expr in node.constructor_args:
            arg = self.visit(arg_expr)
            
            # Load value if it's a pointer
            if isinstance(arg.type, ir.PointerType) and not (
                    isinstance(arg.type.pointee, ir.IntType) and arg.type.pointee.width == 8):
                arg = self.builder.load(arg)
            
            args.append(arg)
        
        # Call constructor
        result = self.builder.call(constructor, args, name=f"{node.name}_init")
        
        # Copy the constructed object to our local instance
        # Get only the value, not the pointer
        constructed_obj = self.builder.load(result)
        self.builder.store(constructed_obj, instance_ptr)
    
    # Store the instance pointer in the symbol table
    self.add_local_variable(node.name, instance_ptr)
    
    return instance_ptr

def visit_ThisExpression(self, node):
    """Generates LLVM code for 'this' expression."""
    print(f"DEBUG: Accessing this_ptr: {self.this_ptr}")
    print(f"DEBUG: Current class: {self.current_class}")
    print(f"DEBUG: Current scope keys: {list(self.current_scope.keys())}")
    print(f"DEBUG: Local symbol table keys: {list(self.local_symbol_table.keys())}")
    
    # First check the direct instance variable
    if hasattr(self, "this_ptr") and self.this_ptr is not None:
        return self.this_ptr
    
    # Then try current_scope
    if "this" in self.current_scope:
        return self.current_scope["this"]
    
    # Then try local_symbol_table
    if hasattr(self, "local_symbol_table") and "this" in self.local_symbol_table:
        return self.local_symbol_table["this"]
    
    # Finally try method parameters
    if hasattr(self, "current_method") and self.current_method:
        if self.current_method.args and self.current_method.args[0].name == "this":
            return self.current_method.args[0]
    
    raise ValueError("Could not find 'this' pointer in current context")

def visit_ThisMemberAccess(self, node):
    """Generates LLVM code for this.member access."""
    print(f"DEBUG: Accessing this.{node.member_name}")
    
    # First check if we're in a class context
    if not hasattr(self, "current_class") or not self.current_class:
        raise ValueError("'this' reference outside of class method")
    
    # Get the class name
    class_name = self.current_class
    
    # Get class type information
    if class_name not in self.class_types:
        raise ValueError(f"Unknown class: {class_name}")
    
    class_type, field_names, _ = self.class_types[class_name]
    
    # Get 'this' pointer - try different sources
    if hasattr(self, "this_ptr") and self.this_ptr is not None:
        this_ptr = self.this_ptr
    elif "this" in self.current_scope:
        this_ptr = self.current_scope["this"]
    elif "this" in self.local_symbol_table:
        this_ptr = self.local_symbol_table["this"]
    else:
        raise ValueError("Could not find 'this' pointer")
    
    print(f"DEBUG: Found this_ptr: {this_ptr}, type: {this_ptr.type}")
    
    # Check if the member exists
    if node.member_name not in field_names:
        raise ValueError(f"Class {class_name} has no field named {node.member_name}")
    
    field_index = field_names.index(node.member_name)
    
    # If this_ptr is not a pointer, we need to create a temporary allocation
    if not isinstance(this_ptr.type, ir.PointerType):
        # Allocate temp storage
        temp_ptr = self.builder.alloca(class_type, name="this_temp")
        # Store the value
        self.builder.store(this_ptr, temp_ptr)
        # Update this_ptr to use the pointer
        this_ptr = temp_ptr
    
    # Get a pointer to the field
    zero = ir.Constant(self.int_type, 0)
    field_idx = ir.Constant(self.int_type, field_index)
    
    # Get pointer to the field
    field_ptr = self.builder.gep(this_ptr, [zero, field_idx], name=f"this.{node.member_name}")
    
    return field_ptr

def visit_ThisMemberAssignment(self, node):
    """Generates LLVM code for this.member assignment."""
    # Get the 'this' pointer
    this_ptr = self.visit_ThisExpression(None)
    
    # Get the class name
    class_name = self.current_class
    if not class_name:
        raise ValueError("Could not determine current class")
    
    # Get the class type information
    if class_name not in self.class_types:
        raise ValueError(f"Class {class_name} not defined")
    
    class_type_info = self.class_types[class_name]
    field_names = class_type_info[1]
    
    if node.member_name not in field_names:
        raise ValueError(f"Class {class_name} has no field named {node.member_name}")
    
    field_index = field_names.index(node.member_name)
    
    # Get a pointer to the field
    zero = ir.Constant(self.int_type, 0)
    field_idx = ir.Constant(self.int_type, field_index)
    member_ptr = self.builder.gep(this_ptr, [zero, field_idx], name=f"this.{node.member_name}")
    
    # Get the value to assign
    value = self.visit(node.value)
    
    # If value is a pointer, load the value first
    if isinstance(value.type, ir.PointerType) and not (
            isinstance(value.type.pointee, ir.IntType) and value.type.pointee.width == 8):
        value = self.builder.load(value)
    
    # Get the target field type
    field_type = member_ptr.type.pointee
    
    # Perform type conversion if needed
    if isinstance(field_type, ir.IntType) and isinstance(value.type, ir.FloatType):
        value = self.builder.fptosi(value, field_type)
    elif isinstance(field_type, ir.IntType) and isinstance(value.type, ir.DoubleType):
        value = self.builder.fptosi(value, field_type)
    elif isinstance(field_type, ir.FloatType) and isinstance(value.type, ir.IntType):
        value = self.builder.sitofp(value, field_type)
    elif isinstance(field_type, ir.FloatType) and isinstance(value.type, ir.DoubleType):
        value = self.builder.fptrunc(value, field_type)
    elif isinstance(field_type, ir.DoubleType) and isinstance(value.type, ir.IntType):
        value = self.builder.sitofp(value, field_type)
    elif isinstance(field_type, ir.DoubleType) and isinstance(value.type, ir.FloatType):
        value = self.builder.fpext(value, field_type)
    
    # Store the value in the field
    self.builder.store(value, member_ptr)
    
    return value

def visit_ClassInstantiation(self, node):
    """Generates LLVM code for class instantiation."""
    print(f"DEBUG: Instantiating class {node.class_name}")
    
    # Check if class exists
    if node.class_name not in self.class_types:
        raise ValueError(f"Undefined class: {node.class_name}")
    
    # Get constructor
    constructor_name = node.class_name
    if constructor_name not in self.global_symbol_table:
        raise ValueError(f"Constructor not found for class {node.class_name}")
    
    constructor = self.global_symbol_table[constructor_name]
    
    # Process arguments
    args = []
    for arg_expr in node.arguments:
        arg = self.visit(arg_expr)
        
        # Load value if it's a pointer
        if isinstance(arg.type, ir.PointerType) and not (
                isinstance(arg.type.pointee, ir.IntType) and arg.type.pointee.width == 8):
            arg = self.builder.load(arg)
        
        args.append(arg)
    
    # Call constructor
    instance_ptr = self.builder.call(constructor, args, name="temp_instance")
    
    return instance_ptr

def visit_ClassMethodCall(self, node):
    """Generates LLVM code for object method call."""
    print(f"DEBUG: Calling method {node.obj_name}.{node.method_name}")
    
    # Get the object from the symbol table
    obj_ptr = self.find_variable(node.obj_name)
    
    # Get the object type
    obj_type = obj_ptr.type.pointee
    if not isinstance(obj_type, ir.LiteralStructType):
        raise ValueError(f"{node.obj_name} is not an object")
    
    # Find the class name for this object
    class_name = None
    for name, (type_obj, _, _) in self.class_types.items():
        if type_obj == obj_type:
            class_name = name
            break
    
    if not class_name:
        raise ValueError(f"Could not determine class type for {node.obj_name}")
    
    # Check if the class has this method
    if class_name not in self.class_methods or node.method_name not in self.class_methods[class_name]:
        raise ValueError(f"Class {class_name} has no method named {node.method_name}")
    
    # Get the method
    method = self.class_methods[class_name][node.method_name]
    
    # Process arguments
    args = [obj_ptr]  # First argument is 'this' pointer
    
    for arg_expr in node.arguments:
        arg = self.visit(arg_expr)
        
        # Load value if it's a pointer
        if isinstance(arg.type, ir.PointerType) and not (
                isinstance(arg.type.pointee, ir.IntType) and arg.type.pointee.width == 8):
            arg = self.builder.load(arg)
        
        args.append(arg)
    
    # Call the method
    result = self.builder.call(method, args, name=f"{node.obj_name}_{node.method_name}_call")
    
    return result