import llvmlite.ir as ir
from src.syntax_tree.ast_nodes import StructAccess

def visit_StructDefinition(self, node):
    """Generates LLVM code for struct definition."""
    print(f"DEBUG: Defining struct {node.name}")
    
    # Create a list of LLVM types for the struct members
    member_types = []
    member_names = []
    
    for member in node.members:
        member_type = self.get_llvm_type(member.member_type)
        member_types.append(member_type)
        member_names.append(member.name)
    
    # Create the struct type without name parameter
    struct_type = ir.LiteralStructType(member_types)
    
    # Store the struct type and member information in the struct registry
    self.struct_types[node.name] = (struct_type, member_names, member_types)
    
    print(f"DEBUG: Struct {node.name} defined with members: {member_names}")
    
    return struct_type

def visit_StructDeclaration(self, node):
    """Generates LLVM code for struct variable declaration."""
    print(f"DEBUG: Declaring struct variable {node.name} of type {node.struct_type}")
    
    # Get the struct type from the registry
    if node.struct_type not in self.struct_types:
        raise ValueError(f"Undefined struct type: {node.struct_type}")
    
    struct_type, member_names, member_types = self.struct_types[node.struct_type]
    
    # Allocate memory for the struct
    var_ptr = self.builder.alloca(struct_type, name=node.name)
    
    # Store the variable in the symbol table
    self.add_local_variable(node.name, var_ptr)
    
    # Initialize the struct if initial value is provided
    if node.initial_value:
        if len(node.initial_value) > len(member_types):
            raise ValueError(f"Too many initializers for struct {node.struct_type}")
        
        for i, (value_expr, member_name) in enumerate(zip(node.initial_value, member_names)):
            value = self.visit(value_expr)
            
            # Get a pointer to the member
            zero = ir.Constant(self.int_type, 0)
            member_idx = ir.Constant(self.int_type, i)
            member_ptr = self.builder.gep(var_ptr, [zero, member_idx], name=f"{node.name}.{member_name}")
            
            # Get the target member type
            target_type = member_types[i]
            
            # Perform type conversion if needed
            if isinstance(target_type, ir.IntType) and isinstance(value.type, ir.FloatType):
                value = self.builder.fptosi(value, target_type)
                print(f"DEBUG: Converting float -> int for member {member_name}")
            elif isinstance(target_type, ir.IntType) and isinstance(value.type, ir.DoubleType):
                value = self.builder.fptosi(value, target_type)
                print(f"DEBUG: Converting double -> int for member {member_name}")
            elif isinstance(target_type, ir.FloatType) and isinstance(value.type, ir.IntType):
                value = self.builder.sitofp(value, target_type)
                print(f"DEBUG: Converting int -> float for member {member_name}")
            elif isinstance(target_type, ir.FloatType) and isinstance(value.type, ir.DoubleType):
                value = self.builder.fptrunc(value, target_type)
                print(f"DEBUG: Converting double -> float for member {member_name}")
            elif isinstance(target_type, ir.DoubleType) and isinstance(value.type, ir.IntType):
                value = self.builder.sitofp(value, target_type)
                print(f"DEBUG: Converting int -> double for member {member_name}")
            elif isinstance(target_type, ir.DoubleType) and isinstance(value.type, ir.FloatType):
                value = self.builder.fpext(value, target_type)
                print(f"DEBUG: Converting float -> double for member {member_name}")
            
            # Store the value in the member
            self.builder.store(value, member_ptr)
    
    return var_ptr

def visit_StructAccess(self, node):
    """Generates LLVM code for struct member access."""
    print(f"DEBUG: Accessing struct {node.struct_name}.{node.member_name}")
    
    # Get the struct variable from the symbol table
    struct_ptr = self.find_variable(node.struct_name)
    print(f"DEBUG: Struct pointer type: {struct_ptr.type}")
    
    # Get the struct type information
    struct_type = struct_ptr.type.pointee
    if not isinstance(struct_type, ir.LiteralStructType):
        raise ValueError(f"Variable {node.struct_name} is not a struct or class")
    
    # Try to find the struct type name in both structs and classes
    type_name = None
    field_names = None
    
    # First try struct types
    for name, (type_obj, names, _) in self.struct_types.items():
        if type_obj == struct_type:
            type_name = name
            field_names = names
            break
    
    # If not found, try class types
    if type_name is None:
        for name, (type_obj, names, _) in self.class_types.items():
            if type_obj == struct_type:
                type_name = name
                field_names = names
                break
    
    if type_name is None or field_names is None:
        raise ValueError(f"Could not find type info for {node.struct_name}")
    
    print(f"DEBUG: Found type {type_name} with fields {field_names}")
    
    # Get the member index
    if node.member_name not in field_names:
        raise ValueError(f"Struct or class {type_name} has no member named {node.member_name}")
    
    member_index = field_names.index(node.member_name)
    
    # Get a pointer to the member
    zero = ir.Constant(self.int_type, 0)
    member_idx = ir.Constant(self.int_type, member_index)
    member_ptr = self.builder.gep(struct_ptr, [zero, member_idx], name=f"{node.struct_name}.{node.member_name}")
    
    # Return the pointer to the member (don't load it)
    # This allows for both reading and writing to the member
    return member_ptr

def visit_StructAssignment(self, node):
    """Generates LLVM code for struct member assignment."""
    print(f"DEBUG: Assigning to struct {node.struct_name}.{node.field_name}")
    
    # Get a pointer to the member
    member_ptr = self.visit_StructAccess(StructAccess(node.struct_name, node.field_name))
    
    # Get the value to assign
    value = self.visit(node.value)
    
    # Get the field type
    field_type = member_ptr.type.pointee
    
    # If value is a pointer, load the value first
    if isinstance(value.type, ir.PointerType) and not (
            isinstance(value.type.pointee, ir.IntType) and value.type.pointee.width == 8):
        print(f"DEBUG: Loading value from pointer {value.type} before assignment")
        value = self.builder.load(value)
    
    # Perform type conversion if needed
    if isinstance(field_type, ir.IntType) and isinstance(value.type, ir.FloatType):
        value = self.builder.fptosi(value, field_type)
        print(f"DEBUG: Converting float -> int for member {node.field_name}")
    elif isinstance(field_type, ir.IntType) and isinstance(value.type, ir.DoubleType):
        value = self.builder.fptosi(value, field_type)
        print(f"DEBUG: Converting double -> int for member {node.field_name}")
    elif isinstance(field_type, ir.FloatType) and isinstance(value.type, ir.IntType):
        value = self.builder.sitofp(value, field_type)
        print(f"DEBUG: Converting int -> float for member {node.field_name}")
    elif isinstance(field_type, ir.FloatType) and isinstance(value.type, ir.DoubleType):
        value = self.builder.fptrunc(value, field_type)
        print(f"DEBUG: Converting double -> float for member {node.field_name}")
    elif isinstance(field_type, ir.DoubleType) and isinstance(value.type, ir.IntType):
        value = self.builder.sitofp(value, field_type)
        print(f"DEBUG: Converting int -> double for member {node.field_name}")
    elif isinstance(field_type, ir.DoubleType) and isinstance(value.type, ir.FloatType):
        value = self.builder.fpext(value, field_type)
        print(f"DEBUG: Converting float -> double for member {node.field_name}")
    
    # Store the value in the member
    self.builder.store(value, member_ptr)
    
    return value

def visit_StructToStructAssignment(self, node):
    """Handles assignment of an entire struct to another struct."""
    print(f"DEBUG: Struct-to-struct assignment from {node.src_name} to {node.dest_name}")
    
    # Get the source and destination structs
    dest_ptr = self.find_variable(node.dest_name)
    src_ptr = self.find_variable(node.src_name)
    
    # Get struct type information
    dest_type = dest_ptr.type.pointee
    src_type = src_ptr.type.pointee
    
    if not isinstance(dest_type, ir.LiteralStructType) or not isinstance(src_type, ir.LiteralStructType):
        raise ValueError(f"Both variables in struct assignment must be structs")
    
    # Find the struct type names
    dest_type_name = None
    src_type_name = None
    
    for name, (type_obj, _, _) in self.struct_types.items():
        if type_obj == dest_type:
            dest_type_name = name
        if type_obj == src_type:
            src_type_name = name
    
    if dest_type_name != src_type_name:
        raise ValueError(f"Cannot assign {src_type_name} to {dest_type_name}")
    
    # Get member information
    _, member_names, _ = self.struct_types[dest_type_name]
    
    # Copy each member from source to destination
    for i, member_name in enumerate(member_names):
        # Get pointers to the source and destination members
        zero = ir.Constant(self.int_type, 0)
        index = ir.Constant(self.int_type, i)
        
        src_member_ptr = self.builder.gep(src_ptr, [zero, index], name=f"{node.src_name}.{member_name}")
        dest_member_ptr = self.builder.gep(dest_ptr, [zero, index], name=f"{node.dest_name}.{member_name}")
        
        # Load value from source
        src_value = self.builder.load(src_member_ptr)
        
        # Store in destination
        self.builder.store(src_value, dest_member_ptr)
    
    print(f"DEBUG: Completed struct assignment from {node.src_name} to {node.dest_name}")
    return None