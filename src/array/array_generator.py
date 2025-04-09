import llvmlite.ir as ir
import llvmlite.binding as llvm

def visit_ArrayDeclaration(self, node):
    # Określ typ elementów tablicy
    if node.var_type == 'int':
        element_type = self.int_type
    elif node.var_type == 'float':
        element_type = self.float_type
    else:
        raise ValueError(f"Nieznany typ tablicy: {node.var_type}")
        
    # print(f"Deklaracja tablicy {node.name} typu {node.var_type}[{node.size}]")
        
    # Utwórz typ tablicy
    array_type = ir.ArrayType(element_type, node.size)
        
    # Alokuj tablicę na stosie
    array_ptr = self.builder.alloca(array_type, name=node.name)
        
    # Zapisz informacje o tablicy do tablicy symboli
    # Zapisujemy krotkę: (wskaźnik, typ elementu, rozmiar)
    self.symbol_table[node.name] = (array_ptr, element_type, node.size)
        
    # Inicjalizacja tablicy, jeśli podano wartości początkowe
    if node.initial_values:
        # print(f"Inicjalizacja tablicy {node.name} {len(node.initial_values)} wartościami")
        for i, value_node in enumerate(node.initial_values):
            if i >= node.size:
                print(f"Ostrzeżenie: Tablica {node.name} zainicjalizowana większą liczbą elementów niż rozmiar {node.size}")
                break
                
            # Uzyskaj wartość początkową
            value = self.visit(value_node)
                
            # Uzyskaj wskaźnik do i-tego elementu
            zero = ir.Constant(self.int_type, 0)
            idx = ir.Constant(self.int_type, i)
            element_ptr = self.builder.gep(array_ptr, [zero, idx], name=f"{node.name}_elem_{i}")
                
            # Zapisz wartość do elementu
            self.builder.store(value, element_ptr)
        
    return array_ptr

def visit_ArrayAccess(self, node):
    # Pobierz informacje o tablicy
    if node.name not in self.symbol_table:
        raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
        
    array_info = self.symbol_table[node.name]
    if not isinstance(array_info, tuple) or len(array_info) != 3:
        raise ValueError(f"Zmienna {node.name} nie jest tablicą")
        
    array_ptr, element_type, size = array_info
      
    # Oblicz indeks
    index = self.visit(node.index)
      
    # Dodaj sprawdzanie zakresu w czasie wykonania
    size_const = ir.Constant(self.int_type, size)
        
    # Tworzenie bloków dla sprawdzania zakresu
    current_block = self.builder.block
    in_bounds_block = self.builder.append_basic_block(name=f"{node.name}_in_bounds")
    out_of_bounds_block = self.builder.append_basic_block(name=f"{node.name}_out_of_bounds")
    merge_block = self.builder.append_basic_block(name=f"{node.name}_merge")
        
    # Sprawdzenie czy indeks < size
    is_too_large = self.builder.icmp_signed('>=', index, size_const)
        
    # Skocz do odpowiedniego bloku w zależności od wyniku
    self.builder.cbranch(is_too_large, out_of_bounds_block, in_bounds_block)
        
    # Obsługa przypadku poza zakresem
    self.builder.position_at_end(out_of_bounds_block)
        
    # Przygotowanie formatu dla printf - z terminatorem null
    error_msg = "Error: Index out of range in array '%s' [0-%d]\n\0"
    error_bytes = error_msg.encode('ascii')
        
    # Stała dla komunikatu błędu
    c_error_msg = ir.Constant(ir.ArrayType(ir.IntType(8), len(error_bytes)), 
                        bytearray(error_bytes))
        
    # Generuj unikalną nazwę dla komunikatu błędu
    error_count = sum(1 for g in self.module.global_values 
                    if hasattr(g, 'name') and g.name.startswith(".error"))
        
    error_msg_global = ir.GlobalVariable(self.module, c_error_msg.type, 
                                    name=f".error.{error_count}")
    error_msg_global.linkage = 'internal'
    error_msg_global.global_constant = True
    error_msg_global.initializer = c_error_msg
        
    # Konwertuj wskaźnik do formatu do i8*
    error_msg_ptr = self.builder.bitcast(error_msg_global, ir.PointerType(ir.IntType(8)))
        
    # Przygotuj nazwę tablicy jako stałą string
    name_str = node.name + "\0"
    name_bytes = name_str.encode('ascii')
        
    c_name_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(name_bytes)), 
                        bytearray(name_bytes))
        
    name_global = ir.GlobalVariable(self.module, c_name_str.type, 
                                name=f".str.name.{error_count}")
    name_global.linkage = 'internal'
    name_global.global_constant = True
    name_global.initializer = c_name_str
        
    name_ptr = self.builder.bitcast(name_global, ir.PointerType(ir.IntType(8)))
        
    # Oblicz rozmiar - 1 dla prawidłowego zakresu
    max_index = self.builder.sub(size_const, ir.Constant(self.int_type, 1))
        
    # Wypisz komunikat o błędzie - użyj stringów
    self.builder.call(self.printf_func, [error_msg_ptr, name_ptr, max_index])
        
    # Zwróć bezpieczną wartość (0) i przejdź do bloku końcowego
    safe_value = ir.Constant(element_type, 0)
    self.builder.branch(merge_block)
        
    # Obsługa przypadku w zakresie
    self.builder.position_at_end(in_bounds_block)
        
    # Standardowy dostęp do tablicy
    zero = ir.Constant(self.int_type, 0)
    element_ptr = self.builder.gep(array_ptr, [zero, index], name=f"{node.name}_elem")
    normal_value = self.builder.load(element_ptr, name=f"{node.name}_value")
    self.builder.branch(merge_block)
        
    # Blok łączący - wybierz odpowiednią wartość
    self.builder.position_at_end(merge_block)
    phi = self.builder.phi(element_type, name=f"{node.name}_phi")
    phi.add_incoming(safe_value, out_of_bounds_block)
    phi.add_incoming(normal_value, in_bounds_block)
        
    return phi

def visit_ArrayAssignment(self, node):
    # Pobierz informacje o tablicy
    if node.name not in self.symbol_table:
        raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
        
    array_info = self.symbol_table[node.name]
    if not isinstance(array_info, tuple) or len(array_info) != 3:
        raise ValueError(f"Zmienna {node.name} nie jest tablicą")
        
    array_ptr, element_type, size = array_info
        
    # Oblicz indeks i wartość
    index = self.visit(node.index)
    value = self.visit(node.value)
        
    # Automatyczna konwersja typów jak w C
    if isinstance(element_type, ir.IntType) and isinstance(value.type, ir.FloatType):
        # Konwersja float -> int (utrata precyzji)
        value = self.builder.fptosi(value, element_type)
    elif isinstance(element_type, ir.FloatType) and isinstance(value.type, ir.IntType):
        # Konwersja int -> float
        value = self.builder.sitofp(value, element_type)
        
    # Dodaj sprawdzanie zakresu w czasie wykonania
    size_const = ir.Constant(self.int_type, size)
        
    # Tworzenie bloków dla sprawdzania zakresu
    current_block = self.builder.block
    in_bounds_block = self.builder.append_basic_block(name=f"{node.name}_assign_in_bounds")
    out_of_bounds_block = self.builder.append_basic_block(name=f"{node.name}_assign_out_of_bounds")
    merge_block = self.builder.append_basic_block(name=f"{node.name}_assign_merge")
        
    # Sprawdzenie czy indeks < size
    is_too_large = self.builder.icmp_signed('>=', index, size_const)
        
    # Skocz do odpowiedniego bloku w zależności od wyniku
    self.builder.cbranch(is_too_large, out_of_bounds_block, in_bounds_block)
        
    # Obsługa przypadku poza zakresem
    self.builder.position_at_end(out_of_bounds_block)
        
    # Przygotowanie formatu dla printf - z terminatorem null
    error_msg = "Error: Assignment out of range in array '%s' [0-%d]\n\0"
    error_bytes = error_msg.encode('ascii')
        
    # Stała dla komunikatu błędu
    c_error_msg = ir.Constant(ir.ArrayType(ir.IntType(8), len(error_bytes)), 
                        bytearray(error_bytes))
        
    # Generuj unikalną nazwę dla komunikatu błędu
    error_count = sum(1 for g in self.module.global_values 
                    if hasattr(g, 'name') and g.name.startswith(".error"))
        
    error_msg_global = ir.GlobalVariable(self.module, c_error_msg.type, 
                                    name=f".error.{error_count}")
    error_msg_global.linkage = 'internal'
    error_msg_global.global_constant = True
    error_msg_global.initializer = c_error_msg
        
    # Konwertuj wskaźnik do formatu do i8*
    error_msg_ptr = self.builder.bitcast(error_msg_global, ir.PointerType(ir.IntType(8)))
        
    # Przygotuj nazwę tablicy jako stałą string
    name_str = node.name + "\0"
    name_bytes = name_str.encode('ascii')
        
    c_name_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(name_bytes)), 
                        bytearray(name_bytes))
        
    name_global = ir.GlobalVariable(self.module, c_name_str.type, 
                                name=f".str.name.{error_count}")
    name_global.linkage = 'internal'
    name_global.global_constant = True
    name_global.initializer = c_name_str
        
    name_ptr = self.builder.bitcast(name_global, ir.PointerType(ir.IntType(8)))
        
    # Oblicz rozmiar - 1 dla prawidłowego zakresu
    max_index = self.builder.sub(size_const, ir.Constant(self.int_type, 1))
        
    # Wypisz komunikat o błędzie
    self.builder.call(self.printf_func, [error_msg_ptr, name_ptr, max_index])
        
    # Pomiń przypisanie i przejdź do bloku końcowego
    self.builder.branch(merge_block)
        
    # Obsługa przypadku w zakresie
    self.builder.position_at_end(in_bounds_block)
        
    # Standardowy zapis do tablicy
    zero = ir.Constant(self.int_type, 0)
    element_ptr = self.builder.gep(array_ptr, [zero, index], name=f"{node.name}_elem")
    self.builder.store(value, element_ptr)
    self.builder.branch(merge_block)
        
    # Blok łączący
    self.builder.position_at_end(merge_block)