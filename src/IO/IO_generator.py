import llvmlite.ir as ir
import llvmlite.binding as llvm

def visit_PrintStatement(self, node):
    """Generuje kod LLVM dla instrukcji print."""
    # Oblicz wartość do wydrukowania
    value = self.visit(node.expression)
    
    if isinstance(value.type, ir.PointerType) and value.type.pointee == ir.IntType(8):
        # Dla stringów
        format_str = "%s\n\0"
    elif isinstance(value.type, ir.FloatType):
        # Dla liczb zmiennoprzecinkowych
        format_str = "%.1f\n\0"
        # Konwersja float na double dla printf
        value = self.builder.fpext(value, ir.DoubleType())
    elif isinstance(value.type, ir.IntType) and value.type.width == 1:
        # Dla wartości logicznych
        
        # Tworzenie bloków dla warunkowego wyświetlania "true" lub "false"
        true_block = self.builder.append_basic_block(name="print_true")
        false_block = self.builder.append_basic_block(name="print_false")
        merge_block = self.builder.append_basic_block(name="print_bool_end")
        
        # Warunek skoku
        self.builder.cbranch(value, true_block, false_block)
        
        # Blok dla "true"
        self.builder.position_at_end(true_block)
        
        # Format dla "true"
        true_format = "true\n\0"
        true_format_bytes = true_format.encode("ascii")
        true_format_type = ir.ArrayType(ir.IntType(8), len(true_format_bytes))
        true_format_const = ir.Constant(true_format_type, bytearray(true_format_bytes))
        
        true_format_global = ir.GlobalVariable(self.module, true_format_type, name=f"fmt.true.{next(self._global_counter)}")
        true_format_global.linkage = 'private'
        true_format_global.global_constant = True
        true_format_global.initializer = true_format_const
        
        true_format_ptr = self.builder.bitcast(true_format_global, ir.PointerType(ir.IntType(8)))
        
        # Wywołaj printf dla "true"
        self.builder.call(self.printf_func, [true_format_ptr])
        self.builder.branch(merge_block)
        
        # Blok dla "false"
        self.builder.position_at_end(false_block)
        
        # Format dla "false"
        false_format = "false\n\0"
        false_format_bytes = false_format.encode("ascii")
        false_format_type = ir.ArrayType(ir.IntType(8), len(false_format_bytes))
        false_format_const = ir.Constant(false_format_type, bytearray(false_format_bytes))
        
        false_format_global = ir.GlobalVariable(self.module, false_format_type, name=f"fmt.false.{next(self._global_counter)}")
        false_format_global.linkage = 'private'
        false_format_global.global_constant = True
        false_format_global.initializer = false_format_const
        
        false_format_ptr = self.builder.bitcast(false_format_global, ir.PointerType(ir.IntType(8)))
        
        # Wywołaj printf dla "false"
        self.builder.call(self.printf_func, [false_format_ptr])
        self.builder.branch(merge_block)
        
        # Blok końcowy
        self.builder.position_at_end(merge_block)
        
        # Nie ma bezpośredniej wartości do zwrócenia, wszystko zostało obsłużone w blokach
        return None
    else:
        # Dla liczb całkowitych
        format_str = "%d\n\0"
    
    # Format dla pozostałych typów
    format_bytes = format_str.encode("ascii")
    format_type = ir.ArrayType(ir.IntType(8), len(format_bytes))
    format_const = ir.Constant(format_type, bytearray(format_bytes))
    
    format_global = ir.GlobalVariable(self.module, format_type, name=f"fmt.{next(self._global_counter)}")
    format_global.linkage = 'private'
    format_global.global_constant = True
    format_global.initializer = format_const
    
    format_ptr = self.builder.bitcast(format_global, ir.PointerType(ir.IntType(8)))
    
    # Wywołaj printf
    self.builder.call(self.printf_func, [format_ptr, value])
    
def visit_ReadStatement(self, node):
    """Generuje kod LLVM dla instrukcji read."""
    # Sprawdź typ odczytu - zmienna, tablica czy macierz
    if hasattr(node, 'row_index') and node.row_index is not None and hasattr(node, 'col_index') and node.col_index is not None:
        # Odczyt do elementu macierzy
        if node.name not in self.symbol_table:
            raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
            
        matrix_info = self.symbol_table[node.name]
        if not isinstance(matrix_info, tuple) or len(matrix_info) != 4:
            raise ValueError(f"Zmienna {node.name} nie jest macierzą")
            
        matrix_ptr, element_type, rows, cols = matrix_info
            
        # Oblicz indeksy
        row_index = self.visit(node.row_index)
        col_index = self.visit(node.col_index)
            
        # Sprawdź zakresy
        rows_const = ir.Constant(self.int_type, rows)
        cols_const = ir.Constant(self.int_type, cols)
            
        # Tworzenie bloków dla sprawdzania zakresu
        current_block = self.builder.block
        row_check_block = self.builder.append_basic_block(name=f"{node.name}_read_row_check")
        row_in_bounds_block = self.builder.append_basic_block(name=f"{node.name}_read_row_in_bounds")
        row_out_of_bounds_block = self.builder.append_basic_block(name=f"{node.name}_read_row_out_of_bounds")
        col_check_block = self.builder.append_basic_block(name=f"{node.name}_read_col_check")
        col_in_bounds_block = self.builder.append_basic_block(name=f"{node.name}_read_col_in_bounds")
        col_out_of_bounds_block = self.builder.append_basic_block(name=f"{node.name}_read_col_out_of_bounds")
        merge_block = self.builder.append_basic_block(name=f"{node.name}_read_merge")
            
        # Przejdź do bloku sprawdzania wiersza
        self.builder.branch(row_check_block)
        self.builder.position_at_end(row_check_block)
            
        # Sprawdź czy indeks wiersza < rows
        is_row_too_large = self.builder.icmp_signed('>=', row_index, rows_const)
        self.builder.cbranch(is_row_too_large, row_out_of_bounds_block, row_in_bounds_block)
            
        # Obsługa przypadku poza zakresem wiersza
        self.builder.position_at_end(row_out_of_bounds_block)
        self._emit_matrix_error_message(
            node.name, 
            "Error: Row index out of range in matrix read '%s' [0-%d][0-%d]\n\0", 
            row_index, rows, cols
        )
        self.builder.branch(merge_block)
            
        # Obsługa przypadku w zakresie wiersza
        self.builder.position_at_end(row_in_bounds_block)
        self.builder.branch(col_check_block)
            
        # Sprawdzanie kolumny
        self.builder.position_at_end(col_check_block)
        is_col_too_large = self.builder.icmp_signed('>=', col_index, cols_const)
        self.builder.cbranch(is_col_too_large, col_out_of_bounds_block, col_in_bounds_block)
            
        # Obsługa przypadku poza zakresem kolumny
        self.builder.position_at_end(col_out_of_bounds_block)
        self._emit_matrix_error_message(
            node.name, 
            "Error: Column index out of range in matrix read '%s' [0-%d][0-%d]\n\0", 
            col_index, rows, cols
        )
        self.builder.branch(merge_block)
            
        # Obsługa przypadku w zakresie kolumny
        self.builder.position_at_end(col_in_bounds_block)
            
        # Odczyt z stdin do elementu macierzy
        zero = ir.Constant(self.int_type, 0)
        row_ptr = self.builder.gep(matrix_ptr, [zero, row_index], name=f"{node.name}_read_row")
        element_ptr = self.builder.gep(row_ptr, [zero, col_index], name=f"{node.name}_read_elem")
            
        # Określ format na podstawie typu elementu
        if isinstance(element_type, ir.IntType):
            format_str = "%d\0"  # Format dla liczb całkowitych
        elif isinstance(element_type, ir.FloatType):
            format_str = "%f\0"  # Format dla liczb zmiennoprzecinkowych
        else:
            raise ValueError(f"Nieobsługiwany typ dla operacji read: {element_type}")
            
        # Tworzymy globalną zmienną dla format stringa
        c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                bytearray(format_str.encode("utf8")))
            
        # Generuj unikalną nazwę
        format_count = sum(1 for g in self.module.global_values 
                        if hasattr(g, 'name') and g.name.startswith(".str.scanf.matrix"))
            
        global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                        name=f".str.scanf.matrix.{format_count}")
        global_format.linkage = 'internal'
        global_format.global_constant = True
        global_format.initializer = c_format_str
            
        # Konwertuj wskaźnik do formatu do i8*
        format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
            
        # Wywołaj scanf
        self.builder.call(self.scanf_func, [format_ptr, element_ptr])
        self.builder.branch(merge_block)
            
        # Blok łączący
        self.builder.position_at_end(merge_block)
            
    elif hasattr(node, 'index') and node.index is not None:
        # [...]
        pass
    else:
        # Odczyt do pojedynczej zmiennej
        if node.name not in self.symbol_table:
            raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
            
        var_info = self.symbol_table[node.name]
        
        # Sprawdź typ zmiennej
        if isinstance(var_info, tuple):
            raise ValueError(f"Zmienna {node.name} jest tablicą lub macierzą, nie pojedynczą zmienną")
            
        var_ptr = var_info
        var_type = var_ptr.type.pointee
        
        # Określ format na podstawie typu zmiennej
        if isinstance(var_type, ir.IntType):
            if var_type.width == 1:  # Typ logiczny (boolean)
                # Dla wartości logicznych wczytujemy liczbę całkowitą
                format_str = "%d\0"
                
                # Tworzymy tymczasową zmienną dla wczytania wartości całkowitej
                tmp_var = self.builder.alloca(ir.IntType(32), name=f"{node.name}_tmp")
                
                # Tworzymy globalną zmienną dla format stringa
                c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                        bytearray(format_str.encode("utf8")))
                
                # Generuj unikalną nazwę
                format_count = next(self._global_counter)
                
                global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                                name=f".str.scanf.bool.{format_count}")
                global_format.linkage = 'internal'
                global_format.global_constant = True
                global_format.initializer = c_format_str
                
                # Konwertuj wskaźnik do formatu do i8*
                format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
                
                # Wywołaj scanf do wczytania wartości całkowitej
                result = self.builder.call(self.scanf_func, [format_ptr, tmp_var])
                
                # Sprawdź czy scanf się powiódł (zwrócił 1 jako liczbę pomyślnie odczytanych elementów)
                one = ir.Constant(ir.IntType(32), 1)
                is_success = self.builder.icmp_signed('==', result, one)
                
                # Tworzymy bloki dla warunkowego przypisania wartości
                success_block = self.builder.append_basic_block(name=f"{node.name}_read_success")
                merge_block = self.builder.append_basic_block(name=f"{node.name}_read_merge")
                
                # Warunek skoku
                self.builder.cbranch(is_success, success_block, merge_block)
                
                # Blok dla pomyślnego odczytu
                self.builder.position_at_end(success_block)
                
                # Wczytaj wartość z tymczasowej zmiennej
                tmp_val = self.builder.load(tmp_var)
                
                # Konwertuj wartość całkowitą na wartość logiczną (0->false, reszta->true)
                zero = ir.Constant(ir.IntType(32), 0)
                bool_val = self.builder.icmp_signed('!=', tmp_val, zero)
                
                # Zapisz wartość logiczną do zmiennej
                self.builder.store(bool_val, var_ptr)
                self.builder.branch(merge_block)
                
                # Ustaw pozycję na blok końcowy
                self.builder.position_at_end(merge_block)
                
            else:  # Typ liczbowy całkowity
                format_str = "%d\0"
                
                # Tworzymy globalną zmienną dla format stringa
                c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                        bytearray(format_str.encode("utf8")))
                
                # Generuj unikalną nazwę
                format_count = next(self._global_counter)
                
                global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                                name=f".str.scanf.int.{format_count}")
                global_format.linkage = 'internal'
                global_format.global_constant = True
                global_format.initializer = c_format_str
                
                # Konwertuj wskaźnik do formatu do i8*
                format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
                
                # Wywołaj scanf i sprawdź wartość zwróconą
                result = self.builder.call(self.scanf_func, [format_ptr, var_ptr])
                
        elif isinstance(var_type, ir.FloatType):
            format_str = "%f\0"  # Format dla liczb zmiennoprzecinkowych
            
            # Tworzymy globalną zmienną dla format stringa
            c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                    bytearray(format_str.encode("utf8")))
            
            # Generuj unikalną nazwę
            format_count = next(self._global_counter)
            
            global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                            name=f".str.scanf.float.{format_count}")
            global_format.linkage = 'internal'
            global_format.global_constant = True
            global_format.initializer = c_format_str
            
            # Konwertuj wskaźnik do formatu do i8*
            format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
            
            # Opróżnienie bufora wyjścia
            self.builder.call(self.fflush_func, [self.stdout])

            # Wywołaj scanf
            result = self.builder.call(self.scanf_func, [format_ptr, var_ptr])
            
        else:
            raise ValueError(f"Nieobsługiwany typ dla operacji read: {var_type}")