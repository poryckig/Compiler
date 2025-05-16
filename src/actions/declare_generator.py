import llvmlite.ir as ir

def visit_VariableDeclaration(self, node):
    """Generates LLVM code for variable declaration."""
    # Determine LLVM type based on variable type
    try:
        var_type = self.get_llvm_type(node.var_type)
    except ValueError as e:
        # Check if this is a struct type
        if node.var_type in self.struct_types:
            var_type, _, _ = self.struct_types[node.var_type]
        else:
            print(f"Deklaracja zmiennej {node.name} typu {node.var_type}")
            raise ValueError(f"Nieznany typ zmiennej: {node.var_type}")
    
    print(f"Deklaracja zmiennej {node.name} typu {var_type}")
    
    # Check if the builder is available
    if self.builder is None:
        raise ValueError(f"Builder is None when declaring variable {node.name}")
    
    # Determine if the variable is global
    is_global = not self.symbol_table_stack  # Empty stack means global scope
    
    if is_global:
        # Global variables declared at module level
        global_var = ir.GlobalVariable(self.module, var_type, name=node.name)
        global_var.linkage = 'common'
        global_var.align = 4  # Standard alignment
        
        # Initialize with default value
        if isinstance(var_type, ir.IntType):
            default_value = ir.Constant(var_type, 0)
        elif isinstance(var_type, ir.FloatType) or isinstance(var_type, ir.DoubleType):
            default_value = ir.Constant(var_type, 0.0)
        elif isinstance(var_type, ir.LiteralStructType):
            # For struct types, create a zero-initialized struct
            default_value = ir.Constant(var_type, None)
        else:
            # For other types (e.g., pointers) initialize with zeros
            default_value = ir.Constant(var_type, None)
        
        global_var.initializer = default_value
        print(f"Inicjalizacja globalnej zmiennej {node.name} wartością domyślną")
        
        # Save pointer to global symbol table
        self.global_symbol_table[node.name] = global_var
        
        # If there's an initial value, assign it
        if node.initial_value:
            print(f"Inicjalizacja globalnej zmiennej {node.name} wartością początkową")
            
            # Create instruction in main block
            current_block = self.builder.block
            current_pos = self.builder.block.instructions[-1] if self.builder.block.instructions else None
            
            value = self.visit(node.initial_value)
            
            # ADDED SECTION: Load value from pointer if it's a pointer (but not string)
            if isinstance(value.type, ir.PointerType) and not (isinstance(value.type.pointee, ir.IntType) and value.type.pointee.width == 8):
                print(f"Ładowanie wartości ze wskaźnika typu: {value.type.pointee}")
                value = self.builder.load(value)
                print(f"Po załadowaniu typ wartości: {value.type}")
            
            # Type conversion if needed
            if var_type != value.type:
                if isinstance(var_type, ir.IntType) and isinstance(value.type, ir.FloatType):
                    value = self.builder.fptosi(value, var_type)
                elif isinstance(var_type, ir.IntType) and isinstance(value.type, ir.DoubleType):
                    value = self.builder.fptosi(value, var_type)
                elif isinstance(var_type, ir.FloatType) and isinstance(value.type, ir.IntType):
                    value = self.builder.sitofp(value, var_type)
                elif isinstance(var_type, ir.FloatType) and isinstance(value.type, ir.DoubleType):
                    value = self.builder.fptrunc(value, var_type)
                elif isinstance(var_type, ir.DoubleType) and isinstance(value.type, ir.IntType):
                    value = self.builder.sitofp(value, var_type)
                elif isinstance(var_type, ir.DoubleType) and isinstance(value.type, ir.FloatType):
                    value = self.builder.fpext(value, var_type)
            
            # Store initial value
            self.builder.store(value, global_var)
            print(f"Zmienna globalna {node.name} zainicjalizowana wartością początkową")
            
        return global_var
    else:
        # Local variables on stack - modify for structs
        var_ptr = self.builder.alloca(var_type, name=node.name)
        
        # Create default value (0) for appropriate type
        if isinstance(var_type, ir.IntType):
            default_value = ir.Constant(var_type, 0)
        elif isinstance(var_type, ir.FloatType):
            default_value = ir.Constant(var_type, 0.0)
        elif isinstance(var_type, ir.DoubleType):
            default_value = ir.Constant(var_type, 0.0)
        elif isinstance(var_type, ir.LiteralStructType):
            # For struct types, we don't need to initialize with a default value
            # Just create the variable and we'll initialize fields individually
            self.add_local_variable(node.name, var_ptr)
            self.local_symbol_table[node.name] = var_ptr
            print(f"Inicjalizacja zmiennej struktury {node.name}")
            
            # Handle struct initializer if provided
            if node.initial_value:
                if isinstance(node.initial_value, list):
                    # Initialize from a list of values (struct initializer)
                    struct_type_name = None
                    for name, (type_obj, _, _) in self.struct_types.items():
                        if type_obj == var_type:
                            struct_type_name = name
                            break
                            
                    if struct_type_name:
                        _, member_names, _ = self.struct_types[struct_type_name]
                        
                        # Initialize each member with the corresponding value
                        for i, (member_name, value_expr) in enumerate(zip(member_names, node.initial_value)):
                            value = self.visit(value_expr)
                            
                            # Get pointer to member
                            zero = ir.Constant(self.int_type, 0)
                            idx = ir.Constant(self.int_type, i)
                            member_ptr = self.builder.gep(var_ptr, [zero, idx], name=f"{node.name}.{member_name}")
                            
                            # Store value in member
                            self.builder.store(value, member_ptr)
                else:
                    # Initialize from another struct
                    value = self.visit(node.initial_value)
                    # If this is a function call that returns a struct
                    if not isinstance(value.type, ir.PointerType):
                        self.builder.store(value, var_ptr)
                    # If this is a reference to another struct
                    else:
                        src_value = self.builder.load(value)
                        self.builder.store(src_value, var_ptr)
            
            return var_ptr
        elif isinstance(var_type, ir.PointerType):
            # For string - empty string
            empty_str = "\0"
            empty_bytes = empty_str.encode('utf-8')
            empty_type = ir.ArrayType(ir.IntType(8), len(empty_bytes))
            empty_const = ir.Constant(empty_type, bytearray(empty_bytes))
            
            global_id = f"empty_str.{next(self._global_counter)}"
            empty_global = ir.GlobalVariable(self.module, empty_type, name=global_id)
            empty_global.linkage = 'private'
            empty_global.global_constant = True
            empty_global.initializer = empty_const
            
            zero = ir.Constant(self.int_type, 0)
            default_value = self.builder.gep(empty_global, [zero, zero], name=f"{global_id}_ptr")
        else:
            raise ValueError(f"Nieznany typ zmiennej: {node.var_type}")
        
        # Initialize variable with default value - skip for struct types
        if not isinstance(var_type, ir.LiteralStructType):
            self.builder.store(default_value, var_ptr)
            print(f"Inicjalizacja zmiennej {node.name} wartością domyślną")
        
        # Add variable to current scope
        self.add_local_variable(node.name, var_ptr)
        
        # Save pointer to local symbol table
        self.local_symbol_table[node.name] = var_ptr
        
        # If there's an initial value, assign it - skip for struct types handled above
        if node.initial_value and not isinstance(var_type, ir.LiteralStructType):
            print(f"Inicjalizacja zmiennej {node.name} wartością początkową")
            value = self.visit(node.initial_value)
            print(f"Wartość początkowa typu {value.type}")
            
            # ADDED SECTION: Load value from pointer if it's a pointer (but not string)
            if isinstance(value.type, ir.PointerType) and not (isinstance(value.type.pointee, ir.IntType) and value.type.pointee.width == 8):
                print(f"Ładowanie wartości ze wskaźnika typu: {value.type.pointee}")
                value = self.builder.load(value)
                print(f"Po załadowaniu typ wartości: {value.type}")
            
            # Type conversion if needed
            if isinstance(var_type, ir.IntType) and isinstance(value.type, ir.FloatType):
                value = self.builder.fptosi(value, var_type)
                print(f"Konwersja float -> int")
            elif isinstance(var_type, ir.IntType) and isinstance(value.type, ir.DoubleType):
                value = self.builder.fptosi(value, var_type)
                print(f"Konwersja double -> int")
            elif isinstance(var_type, ir.FloatType) and isinstance(value.type, ir.IntType):
                value = self.builder.sitofp(value, var_type)
                print(f"Konwersja int -> float")
            elif isinstance(var_type, ir.FloatType) and isinstance(value.type, ir.DoubleType):
                value = self.builder.fptrunc(value, var_type)
                print(f"Konwersja double -> float")
            elif isinstance(var_type, ir.DoubleType) and isinstance(value.type, ir.IntType):
                value = self.builder.sitofp(value, var_type)
                print(f"Konwersja int -> double")
            elif isinstance(var_type, ir.DoubleType) and isinstance(value.type, ir.FloatType):
                value = self.builder.fpext(value, var_type)
                print(f"Konwersja float -> double")
            
            # Store initial value
            self.builder.store(value, var_ptr)
            print(f"Zmienna {node.name} zainicjalizowana wartością początkową")
        
        return var_ptr