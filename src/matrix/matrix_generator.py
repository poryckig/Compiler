import llvmlite.ir as ir
import llvmlite.binding as llvm

def visit_MatrixDeclaration(self, node):
    """Generuje kod LLVM dla deklaracji macierzy."""
    # Określ typ elementu macierzy
    if node.var_type == 'int':
        element_type = self.int_type
    elif node.var_type == 'float':
        element_type = self.float_type
    else:
        raise ValueError(f"Nieznany typ macierzy: {node.var_type}")
    
    print(f"Deklaracja macierzy {node.name} typu {node.var_type}[{node.rows}][{node.cols}]")
    
    # Utwórz typ tablicy dla wierszy
    row_type = ir.ArrayType(element_type, node.cols)
    
    # Utwórz typ macierzy (tablica wierszy)
    matrix_type = ir.ArrayType(row_type, node.rows)
    
    # Alokuj pamięć dla macierzy
    matrix_ptr = self.builder.alloca(matrix_type, name=node.name)
    
    # Zapisz informacje o macierzy do tablicy symboli
    # Zapisujemy krotkę: (wskaźnik, typ elementu, liczba wierszy, liczba kolumn)
    self.symbol_table[node.name] = (matrix_ptr, element_type, node.rows, node.cols)
    
    # Inicjalizacja macierzy, jeśli podano wartości początkowe
    if node.initial_values:
        print(f"Inicjalizacja macierzy {node.name} {len(node.initial_values)}x{len(node.initial_values[0]) if node.initial_values else 0} wartościami")
        
        # Inicjalizacja wiersz po wierszu
        for i, row_values in enumerate(node.initial_values):
            if i >= node.rows:
                print(f"Ostrzeżenie: Macierz {node.name} zainicjalizowana większą liczbą wierszy niż rozmiar {node.rows}")
                break
            
            # Inicjalizacja kolumna po kolumnie
            for j, value_node in enumerate(row_values):
                if j >= node.cols:
                    print(f"Ostrzeżenie: Wiersz {i} macierzy {node.name} zainicjalizowany większą liczbą elementów niż rozmiar {node.cols}")
                    break
                
                # Uzyskaj wartość początkową
                value = self.visit(value_node)
                
                # Uzyskaj wskaźnik do elementu macierzy [i][j]
                zero = ir.Constant(self.int_type, 0)
                i_idx = ir.Constant(self.int_type, i)
                j_idx = ir.Constant(self.int_type, j)
                
                # Oblicz wskaźnik do wiersza
                row_ptr = self.builder.gep(matrix_ptr, [zero, i_idx], name=f"{node.name}_row_{i}")
                
                # Oblicz wskaźnik do elementu
                element_ptr = self.builder.gep(row_ptr, [zero, j_idx], name=f"{node.name}_elem_{i}_{j}")
                
                # Zapisz wartość do elementu
                self.builder.store(value, element_ptr)
    
    return matrix_ptr

def visit_MatrixAccess(self, node):
    """Generuje kod LLVM dla dostępu do elementu macierzy."""
    # Pobierz informacje o macierzy
    if node.name not in self.symbol_table:
        raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
    
    matrix_info = self.symbol_table[node.name]
    if not isinstance(matrix_info, tuple) or len(matrix_info) != 4:
        raise ValueError(f"Zmienna {node.name} nie jest macierzą")
    
    matrix_ptr, element_type, rows, cols = matrix_info
    
    # Oblicz indeksy
    row_index = self.visit(node.row_index)
    col_index = self.visit(node.col_index)
    
    # Tworzymy stałą, bezpieczną wartość do zwrócenia w przypadku błędu
    safe_value = ir.Constant(element_type, 0)
    
    # Tworzymy bloki LLVM
    current_block = self.builder.block
    row_check_block = self.builder.append_basic_block(name=f"{node.name}_row_check")
    row_in_bounds_block = self.builder.append_basic_block(name=f"{node.name}_row_in_bounds")
    row_out_of_bounds_block = self.builder.append_basic_block(name=f"{node.name}_row_out_of_bounds")
    col_check_block = self.builder.append_basic_block(name=f"{node.name}_col_check")
    col_in_bounds_block = self.builder.append_basic_block(name=f"{node.name}_col_in_bounds")
    col_out_of_bounds_block = self.builder.append_basic_block(name=f"{node.name}_col_out_of_bounds")
    merge_block = self.builder.append_basic_block(name=f"{node.name}_merge")
    
    # Przejdź do bloku sprawdzania wiersza
    self.builder.branch(row_check_block)
    self.builder.position_at_end(row_check_block)
    
    # Sprawdź czy indeks wiersza < rows
    rows_const = ir.Constant(self.int_type, rows)
    is_row_too_large = self.builder.icmp_signed('>=', row_index, rows_const)
    self.builder.cbranch(is_row_too_large, row_out_of_bounds_block, row_in_bounds_block)
    
    # Obsługa przypadku poza zakresem wiersza
    self.builder.position_at_end(row_out_of_bounds_block)
    # Wypisz komunikat o błędzie
    self._emit_matrix_error_message(
        node.name, 
        "Error: Row index out of range in matrix '%s' [0-%d][0-%d]\n\0", 
        row_index, rows, cols
    )
    # Przejdź do bloku końcowego
    self.builder.branch(merge_block)
    
    # Obsługa przypadku w zakresie wiersza - przejdź do sprawdzenia kolumny
    self.builder.position_at_end(row_in_bounds_block)
    self.builder.branch(col_check_block)
    
    # Sprawdzanie zakresu kolumny
    self.builder.position_at_end(col_check_block)
    cols_const = ir.Constant(self.int_type, cols)
    is_col_too_large = self.builder.icmp_signed('>=', col_index, cols_const)
    self.builder.cbranch(is_col_too_large, col_out_of_bounds_block, col_in_bounds_block)
    
    # Obsługa przypadku poza zakresem kolumny
    self.builder.position_at_end(col_out_of_bounds_block)
    # Wypisz komunikat o błędzie
    self._emit_matrix_error_message(
        node.name, 
        "Error: Column index out of range in matrix '%s' [0-%d][0-%d]\n\0", 
        col_index, rows, cols
    )
    # Przejdź do bloku końcowego
    self.builder.branch(merge_block)
    
    # Obsługa przypadku w zakresie kolumny - normalny dostęp
    self.builder.position_at_end(col_in_bounds_block)
    zero = ir.Constant(self.int_type, 0)
    row_ptr = self.builder.gep(matrix_ptr, [zero, row_index], name=f"{node.name}_row")
    element_ptr = self.builder.gep(row_ptr, [zero, col_index], name=f"{node.name}_elem")
    matrix_value = self.builder.load(element_ptr, name=f"{node.name}_value")
    self.builder.branch(merge_block)
    
    # Blok łączący - wybierz odpowiednią wartość
    self.builder.position_at_end(merge_block)
    phi = self.builder.phi(element_type, name=f"{node.name}_phi")
    phi.add_incoming(safe_value, row_out_of_bounds_block)
    phi.add_incoming(safe_value, col_out_of_bounds_block)
    phi.add_incoming(matrix_value, col_in_bounds_block)
    
    return phi

def visit_MatrixAssignment(self, node):
    """Generuje kod LLVM dla przypisania do elementu macierzy."""
    # Pobierz informacje o macierzy
    if node.name not in self.symbol_table:
        raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
    
    matrix_info = self.symbol_table[node.name]
    if not isinstance(matrix_info, tuple) or len(matrix_info) != 4:
        raise ValueError(f"Zmienna {node.name} nie jest macierzą")
    
    matrix_ptr, element_type, rows, cols = matrix_info
    
    # Oblicz indeksy i wartość
    row_index = self.visit(node.row_index)
    col_index = self.visit(node.col_index)
    value = self.visit(node.value)
    
    # Automatyczna konwersja typów jak w C
    if isinstance(element_type, ir.IntType) and isinstance(value.type, ir.FloatType):
        # Konwersja float -> int (utrata precyzji)
        value = self.builder.fptosi(value, element_type)
    elif isinstance(element_type, ir.FloatType) and isinstance(value.type, ir.IntType):
        # Konwersja int -> float
        value = self.builder.sitofp(value, element_type)
    
    # Sprawdzanie zakresu dla wiersza i kolumny
    self._check_matrix_bounds_and_store(node.name, matrix_ptr, element_type, rows, cols, row_index, col_index, value)
    
    return None

def _emit_matrix_error_message(self, matrix_name, error_format, index, rows, cols):
    """Pomocnicza metoda do generowania komunikatów błędów dla macierzy."""
    error_bytes = error_format.encode('ascii')
    
    # Stała dla komunikatu błędu
    c_error_msg = ir.Constant(ir.ArrayType(ir.IntType(8), len(error_bytes)), 
                           bytearray(error_bytes))
    
    # Generuj unikalną nazwę dla komunikatu błędu
    error_count = sum(1 for g in self.module.global_values 
                    if hasattr(g, 'name') and g.name.startswith(".matrix_error"))
    
    error_msg_global = ir.GlobalVariable(self.module, c_error_msg.type, 
                                       name=f".matrix_error.{error_count}")
    error_msg_global.linkage = 'internal'
    error_msg_global.global_constant = True
    error_msg_global.initializer = c_error_msg
    
    # Konwertuj wskaźnik do formatu do i8*
    error_msg_ptr = self.builder.bitcast(error_msg_global, ir.PointerType(ir.IntType(8)))
    
    # Przygotuj nazwę macierzy jako stałą string
    name_str = matrix_name + "\0"
    name_bytes = name_str.encode('ascii')
    
    c_name_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(name_bytes)), 
                          bytearray(name_bytes))
    
    name_global = ir.GlobalVariable(self.module, c_name_str.type, 
                                  name=f".str.matrix.{error_count}")
    name_global.linkage = 'internal'
    name_global.global_constant = True
    name_global.initializer = c_name_str
    
    name_ptr = self.builder.bitcast(name_global, ir.PointerType(ir.IntType(8)))
    
    # Oblicz maksymalne indeksy
    rows_minus_one = self.builder.sub(ir.Constant(self.int_type, rows), ir.Constant(self.int_type, 1))
    cols_minus_one = self.builder.sub(ir.Constant(self.int_type, cols), ir.Constant(self.int_type, 1))
    
    # Wypisz komunikat o błędzie
    self.builder.call(self.printf_func, [error_msg_ptr, name_ptr, rows_minus_one, cols_minus_one])

def _check_matrix_bounds_and_store(self, matrix_name, matrix_ptr, element_type, rows, cols, row_index, col_index, value):
    """Pomocnicza metoda do sprawdzania zakresu i zapisu dla macierzy."""
    # Tworzenie bloków dla sprawdzania zakresu
    current_block = self.builder.block
    row_check_block = self.builder.append_basic_block(name=f"{matrix_name}_store_row_check")
    row_in_bounds_block = self.builder.append_basic_block(name=f"{matrix_name}_store_row_in_bounds")
    row_out_of_bounds_block = self.builder.append_basic_block(name=f"{matrix_name}_store_row_out_of_bounds")
    col_check_block = self.builder.append_basic_block(name=f"{matrix_name}_store_col_check")
    col_in_bounds_block = self.builder.append_basic_block(name=f"{matrix_name}_store_col_in_bounds")
    col_out_of_bounds_block = self.builder.append_basic_block(name=f"{matrix_name}_store_col_out_of_bounds")
    merge_block = self.builder.append_basic_block(name=f"{matrix_name}_store_merge")
    
    # Przejdź do bloku sprawdzania wiersza
    self.builder.branch(row_check_block)
    self.builder.position_at_end(row_check_block)
    
    # Sprawdź czy indeks wiersza < rows
    rows_const = ir.Constant(self.int_type, rows)
    is_row_too_large = self.builder.icmp_signed('>=', row_index, rows_const)
    self.builder.cbranch(is_row_too_large, row_out_of_bounds_block, row_in_bounds_block)
    
    # Obsługa przypadku poza zakresem wiersza
    self.builder.position_at_end(row_out_of_bounds_block)
    # Wypisz komunikat o błędzie
    self._emit_matrix_error_message(
        matrix_name, 
        "Error: Row index out of range in matrix assignment '%s' [0-%d][0-%d]\n\0", 
        row_index, rows, cols
    )
    # Przejdź do bloku końcowego
    self.builder.branch(merge_block)
    
    # Obsługa przypadku w zakresie wiersza - przejdź do sprawdzenia kolumny
    self.builder.position_at_end(row_in_bounds_block)
    self.builder.branch(col_check_block)
    
    # Sprawdzanie zakresu kolumny
    self.builder.position_at_end(col_check_block)
    cols_const = ir.Constant(self.int_type, cols)
    is_col_too_large = self.builder.icmp_signed('>=', col_index, cols_const)
    self.builder.cbranch(is_col_too_large, col_out_of_bounds_block, col_in_bounds_block)
    
    # Obsługa przypadku poza zakresem kolumny
    self.builder.position_at_end(col_out_of_bounds_block)
    # Wypisz komunikat o błędzie
    self._emit_matrix_error_message(
        matrix_name, 
        "Error: Column index out of range in matrix assignment '%s' [0-%d][0-%d]\n\0", 
        col_index, rows, cols
    )
    # Przejdź do bloku końcowego
    self.builder.branch(merge_block)
    
    # Obsługa przypadku w zakresie kolumny - wykonaj przypisanie
    self.builder.position_at_end(col_in_bounds_block)
    zero = ir.Constant(self.int_type, 0)
    row_ptr = self.builder.gep(matrix_ptr, [zero, row_index], name=f"{matrix_name}_store_row")
    element_ptr = self.builder.gep(row_ptr, [zero, col_index], name=f"{matrix_name}_store_elem")
    self.builder.store(value, element_ptr)
    self.builder.branch(merge_block)
    
    # Blok łączący - zakończ instrukcję
    self.builder.position_at_end(merge_block)