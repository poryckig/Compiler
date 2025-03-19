import llvmlite.ir as ir
import llvmlite.binding as llvm

def visit_PrintStatement(self, node):
    """Generuje kod LLVM dla instrukcji print."""
    # Oblicz wartość do wydrukowania
    value = self.visit(node.expression)
    
    if isinstance(value.type, ir.FloatType):
        # Dla liczb zmiennoprzecinkowych użyjmy nowego, uproszczonego podejścia
        
        # Format string z terminatorem null
        format_str = "%.1f\n\0"
        format_bytes = format_str.encode("ascii")
        
        # Stwórz globalną stałą dla formatu
        format_type = ir.ArrayType(ir.IntType(8), len(format_bytes))
        format_const = ir.Constant(format_type, bytearray(format_bytes))
        
        # Dla każdego wywołania generuj unikalną nazwę
        global_id = f"fmt.float.{next(self._global_counter)}"
        fmt_global = ir.GlobalVariable(self.module, format_type, name=global_id)
        fmt_global.linkage = 'private'
        fmt_global.global_constant = True
        fmt_global.initializer = format_const
        
        # Konwersja float -> double
        double_val = self.builder.fpext(value, ir.DoubleType())
        
        # Konwersja wskaźnika
        fmt_ptr = self.builder.bitcast(fmt_global, ir.PointerType(ir.IntType(8)))
        
        # Wywołanie printf
        self.builder.call(self.printf_func, [fmt_ptr, double_val])
        
        # Wywołanie funkcji fflush aby upewnić się, że bufor jest opróżniony
        if not hasattr(self, 'fflush_func'):
            fflush_type = ir.FunctionType(self.int_type, [ir.PointerType(ir.IntType(8))])
            self.fflush_func = ir.Function(self.module, fflush_type, name="fflush")
        
        # fflush(NULL) opróżnia wszystkie bufory
        null_ptr = ir.Constant(ir.PointerType(ir.IntType(8)), None)
        self.builder.call(self.fflush_func, [null_ptr])
    else:
        # Dla liczb całkowitych
        format_str = "%d\n\0"
        format_bytes = format_str.encode("ascii")
        
        # Stwórz globalną stałą dla formatu
        format_type = ir.ArrayType(ir.IntType(8), len(format_bytes))
        format_const = ir.Constant(format_type, bytearray(format_bytes))
        
        # Dla każdego wywołania generuj unikalną nazwę
        global_id = f"fmt.int.{next(self._global_counter)}"
        fmt_global = ir.GlobalVariable(self.module, format_type, name=global_id)
        fmt_global.linkage = 'private'
        fmt_global.global_constant = True
        fmt_global.initializer = format_const
        
        # Konwersja wskaźnika
        fmt_ptr = self.builder.bitcast(fmt_global, ir.PointerType(ir.IntType(8)))
        
        # Wywołanie printf
        self.builder.call(self.printf_func, [fmt_ptr, value])
        
        # Wywołanie funkcji fflush aby upewnić się, że bufor jest opróżniony
        if not hasattr(self, 'fflush_func'):
            fflush_type = ir.FunctionType(self.int_type, [ir.PointerType(ir.IntType(8))])
            self.fflush_func = ir.Function(self.module, fflush_type, name="fflush")
        
        # fflush(NULL) opróżnia wszystkie bufory
        null_ptr = ir.Constant(ir.PointerType(ir.IntType(8)), None)
        self.builder.call(self.fflush_func, [null_ptr])
    
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
        # Tutaj istniejący kod dla obsługi tablic, który już masz
        pass
    else:
        # Tutaj istniejący kod dla obsługi zwykłych zmiennych, który już masz
        pass