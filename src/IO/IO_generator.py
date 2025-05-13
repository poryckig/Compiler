import llvmlite.ir as ir
import llvmlite.binding as llvm

def visit_PrintStatement(self, node):
    """Generuje kod LLVM dla instrukcji print."""
    # Dodaj informację debugowania
    print(f"DEBUG: Przetwarzam instrukcję print: {id(node)}")
    
    # Oblicz wartość do wydrukowania
    value = self.visit(node.expression)
    
    # Sprawdź, czy wartość ma typ void (co może się zdarzyć po wywołaniu funkcji void)
    if isinstance(value.type, ir.VoidType):
        # Dla void drukujemy tylko komunikat "void"
        format_str = "void\n\0"
        format_bytes = format_str.encode("ascii")
        format_type = ir.ArrayType(ir.IntType(8), len(format_bytes))
        format_const = ir.Constant(format_type, bytearray(format_bytes))
        
        format_global = ir.GlobalVariable(self.module, format_type, name=f"fmt.void.{next(self._global_counter)}")
        format_global.linkage = 'private'
        format_global.global_constant = True
        format_global.initializer = format_const
        
        format_ptr = self.builder.bitcast(format_global, ir.PointerType(ir.IntType(8)))
        
        # Wywołaj printf bez dodatkowych argumentów
        self.builder.call(self.printf_func, [format_ptr])
        return None
    
    print(f"DEBUG: Drukowanie wartości typu: {value.type}")
    
    # Upewnij się, że ładujemy wartość ze zmiennej, jeśli to wskaźnik
    if isinstance(value.type, ir.PointerType) and not (value.type.pointee == ir.IntType(8)):
        print(f"DEBUG: Ładowanie wartości ze wskaźnika typu: {value.type.pointee}")
        value = self.builder.load(value)
        print(f"DEBUG: Po załadowaniu typ wartości: {value.type}")
    
    if isinstance(value.type, ir.PointerType) and value.type.pointee == ir.IntType(8):
        # Dla stringów
        format_str = "%s\n\0"
    elif isinstance(value.type, ir.FloatType):
        # Dla liczb zmiennoprzecinkowych single-precision (float32)
        format_str = "%.6f\n\0"  # 6 miejsc po przecinku dla float32
        # Ważne: LLVM printf oczekuje double dla formatów zmiennoprzecinkowych
        # Konwertuj float32 na double przed wywołaniem printf
        value = self.builder.fpext(value, self.double_type)
    elif isinstance(value.type, ir.DoubleType):
        # Dla liczb zmiennoprzecinkowych double-precision (float64)
        format_str = "%.12f\n\0"  # 12 miejsc po przecinku dla float64
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

def handle_float_read(self, element_ptr, var_type):
    """Obsługuje odczyt wartości zmiennoprzecinkowej."""
    # Określ format na podstawie typu
    if isinstance(var_type, ir.FloatType):
        # Dla float32 używamy %f
        format_str = "%f\0"
    elif isinstance(var_type, ir.DoubleType):
        # Dla float64 używamy %lf
        format_str = "%lf\0"
    else:
        raise ValueError(f"Nieobsługiwany typ zmiennoprzecinkowy: {var_type}")
    
    print(f"Odczyt liczby zmiennoprzecinkowej formatem: {format_str}")
        
    # Tworzymy globalną zmienną dla format stringa
    c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                            bytearray(format_str.encode("utf8")))
    
    global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                    name=f".str.scanf.{next(self._global_counter)}")
    global_format.linkage = 'internal'
    global_format.global_constant = True
    global_format.initializer = c_format_str
    
    # Konwertuj wskaźnik do formatu do i8*
    format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
    
    # Wywołaj scanf
    self.builder.call(self.scanf_func, [format_ptr, element_ptr])
    
def visit_ReadStatement(self, node):
    """Generuje kod LLVM dla instrukcji read."""
    # Sprawdź, czy zmienna jest zadeklarowana
    if node.name not in self.symbol_table:
        raise ValueError(f"Niezadeklarowana zmienna: {node.name}")
    
    # Pobierz obiekt ze słownika symboli
    var_obj = self.symbol_table[node.name]
    
    # Sprawdź, czy mamy do czynienia z macierzą
    if node.row_index is not None and node.col_index is not None:
        # Sprawdź, czy to rzeczywiście macierz
        if not isinstance(var_obj, tuple) or len(var_obj) != 4:
            raise ValueError(f"Zmienna {node.name} nie jest macierzą")
            
        matrix_ptr, element_type, rows, cols = var_obj
            
        # Oblicz indeksy
        row_index = self.visit(node.row_index)
        col_index = self.visit(node.col_index)
            
        # Sprawdź zakresy indeksów
        rows_const = ir.Constant(self.int_type, rows)
        cols_const = ir.Constant(self.int_type, cols)
            
        # Sprawdzenie zakresu wiersza
        row_out_of_bounds = self.builder.icmp_signed('>=', row_index, rows_const)
        
        with self.builder.if_then(row_out_of_bounds):
            # Komunikat o błędzie dla indeksu wiersza poza zakresem
            error_msg = f"Row index out of bounds in matrix '{node.name}'\n\0"
            error_bytes = error_msg.encode("utf8")
            error_type = ir.ArrayType(ir.IntType(8), len(error_bytes))
            error_const = ir.Constant(error_type, bytearray(error_bytes))
            
            error_global = ir.GlobalVariable(self.module, error_type, name=f".str.error.{next(self._global_counter)}")
            error_global.linkage = 'private'
            error_global.global_constant = True
            error_global.initializer = error_const
            
            error_ptr = self.builder.bitcast(error_global, ir.PointerType(ir.IntType(8)))
            self.builder.call(self.printf_func, [error_ptr])
        
        # Sprawdzenie zakresu kolumny
        col_out_of_bounds = self.builder.icmp_signed('>=', col_index, cols_const)
        
        with self.builder.if_then(col_out_of_bounds):
            # Komunikat o błędzie dla indeksu kolumny poza zakresem
            error_msg = f"Column index out of bounds in matrix '{node.name}'\n\0"
            error_bytes = error_msg.encode("utf8")
            error_type = ir.ArrayType(ir.IntType(8), len(error_bytes))
            error_const = ir.Constant(error_type, bytearray(error_bytes))
            
            error_global = ir.GlobalVariable(self.module, error_type, name=f".str.error.{next(self._global_counter)}")
            error_global.linkage = 'private'
            error_global.global_constant = True
            error_global.initializer = error_const
            
            error_ptr = self.builder.bitcast(error_global, ir.PointerType(ir.IntType(8)))
            self.builder.call(self.printf_func, [error_ptr])
        
        # Oblicz adres elementu macierzy
        zero = ir.Constant(self.int_type, 0)
        row_ptr = self.builder.gep(matrix_ptr, [zero, row_index], name=f"{node.name}_row")
        element_ptr = self.builder.gep(row_ptr, [zero, col_index], name=f"{node.name}_elem")
        
        # Odczytaj wartość według typu elementu
        if isinstance(element_type, ir.IntType):
            if element_type.width == 1:  # Typ bool (i1)
                # Dla boolean odczytujemy jako int i konwertujemy na bool
                format_str = "%d\0"
                
                # Tworzymy tymczasową zmienną do odczytu int
                temp_var = self.builder.alloca(self.int_type, name=f"{node.name}_temp")
                
                # Tworzymy globalną zmienną dla format stringa
                c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                        bytearray(format_str.encode("utf8")))
                
                global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                                name=f".str.scanf.{next(self._global_counter)}")
                global_format.linkage = 'internal'
                global_format.global_constant = True
                global_format.initializer = c_format_str
                
                # Konwertuj wskaźnik do formatu do i8*
                format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
                
                # Wywołaj scanf
                self.builder.call(self.scanf_func, [format_ptr, temp_var])
                
                # Załaduj odczytaną wartość
                int_value = self.builder.load(temp_var)
                
                # Konwertuj int na bool (niezerowe wartości jako true)
                bool_value = self.builder.icmp_unsigned('!=', int_value, ir.Constant(self.int_type, 0))
                
                # Zapisz wartość bool do elementu macierzy
                self.builder.store(bool_value, element_ptr)
                
            else:  # Zwykły typ całkowity
                format_str = "%d\0"
                
                # Tworzymy globalną zmienną dla format stringa
                c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                        bytearray(format_str.encode("utf8")))
                
                global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                                name=f".str.scanf.{next(self._global_counter)}")
                global_format.linkage = 'internal'
                global_format.global_constant = True
                global_format.initializer = c_format_str
                
                # Konwertuj wskaźnik do formatu do i8*
                format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
                
                # Wywołaj scanf
                self.builder.call(self.scanf_func, [format_ptr, element_ptr])
                
        elif isinstance(element_type, ir.FloatType) or isinstance(element_type, ir.DoubleType):
            # Obsługa odczytu dla typów zmiennoprzecinkowych
            self.handle_float_read(element_ptr, element_type)
            
        else:
            raise ValueError(f"Nieobsługiwany typ dla operacji read: {element_type}")
        
        return None
    
    # Sprawdź, czy mamy do czynienia z tablicą
    elif node.index is not None:
        # Sprawdź, czy to rzeczywiście tablica
        if not isinstance(var_obj, tuple) or len(var_obj) != 3:
            raise ValueError(f"Zmienna {node.name} nie jest tablicą")
            
        array_ptr, element_type, size = var_obj
            
        # Oblicz indeks
        index = self.visit(node.index)
        
        # Sprawdź zakres indeksu
        size_const = ir.Constant(self.int_type, size)
        out_of_bounds = self.builder.icmp_signed('>=', index, size_const)
        
        with self.builder.if_then(out_of_bounds):
            # Komunikat o błędzie dla indeksu poza zakresem
            error_msg = f"Index out of bounds in array '{node.name}'\n\0"
            error_bytes = error_msg.encode("utf8")
            error_type = ir.ArrayType(ir.IntType(8), len(error_bytes))
            error_const = ir.Constant(error_type, bytearray(error_bytes))
            
            error_global = ir.GlobalVariable(self.module, error_type, name=f".str.error.{next(self._global_counter)}")
            error_global.linkage = 'private'
            error_global.global_constant = True
            error_global.initializer = error_const
            
            error_ptr = self.builder.bitcast(error_global, ir.PointerType(ir.IntType(8)))
            self.builder.call(self.printf_func, [error_ptr])
        
        # Oblicz adres elementu tablicy
        zero = ir.Constant(self.int_type, 0)
        element_ptr = self.builder.gep(array_ptr, [zero, index], name=f"{node.name}_elem")
        
        # Odczytaj wartość według typu elementu
        if isinstance(element_type, ir.IntType):
            if element_type.width == 1:  # Typ bool (i1)
                # Dla boolean odczytujemy jako int i konwertujemy na bool
                format_str = "%d\0"
                
                # Tworzymy tymczasową zmienną do odczytu int
                temp_var = self.builder.alloca(self.int_type, name=f"{node.name}_temp")
                
                # Tworzymy globalną zmienną dla format stringa
                c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                        bytearray(format_str.encode("utf8")))
                
                global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                                name=f".str.scanf.{next(self._global_counter)}")
                global_format.linkage = 'internal'
                global_format.global_constant = True
                global_format.initializer = c_format_str
                
                # Konwertuj wskaźnik do formatu do i8*
                format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
                
                # Wywołaj scanf
                self.builder.call(self.scanf_func, [format_ptr, temp_var])
                
                # Załaduj odczytaną wartość
                int_value = self.builder.load(temp_var)
                
                # Konwertuj int na bool (niezerowe wartości jako true)
                bool_value = self.builder.icmp_unsigned('!=', int_value, ir.Constant(self.int_type, 0))
                
                # Zapisz wartość bool do elementu tablicy
                self.builder.store(bool_value, element_ptr)
                
            else:  # Zwykły typ całkowity
                format_str = "%d\0"
                
                # Tworzymy globalną zmienną dla format stringa
                c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                        bytearray(format_str.encode("utf8")))
                
                global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                                name=f".str.scanf.{next(self._global_counter)}")
                global_format.linkage = 'internal'
                global_format.global_constant = True
                global_format.initializer = c_format_str
                
                # Konwertuj wskaźnik do formatu do i8*
                format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
                
                # Wywołaj scanf
                self.builder.call(self.scanf_func, [format_ptr, element_ptr])
                
        elif isinstance(element_type, ir.FloatType) or isinstance(element_type, ir.DoubleType):
            # Obsługa odczytu dla typów zmiennoprzecinkowych
            self.handle_float_read(element_ptr, element_type)
            
        else:
            raise ValueError(f"Nieobsługiwany typ dla operacji read: {element_type}")
            
        return None
    
    # Obsługa zwykłej zmiennej
    else:
        # Tutaj var_obj to wskaźnik do zmiennej
        var_ptr = var_obj
        var_type = var_ptr.type.pointee
        
        print(f"Odczyt do zmiennej {node.name} typu {var_type}")
        
        # Określ format scanf na podstawie typu zmiennej
        if isinstance(var_type, ir.IntType):
            if var_type.width == 1:  # Typ bool (i1)
                # Dla boolean odczytujemy jako int i konwertujemy na bool
                format_str = "%d\0"
                
                # Tworzymy tymczasową zmienną do odczytu int
                temp_var = self.builder.alloca(self.int_type, name=f"{node.name}_temp")
                
                # Tworzymy globalną zmienną dla format stringa
                c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                        bytearray(format_str.encode("utf8")))
                
                global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                                name=f".str.scanf.{next(self._global_counter)}")
                global_format.linkage = 'internal'
                global_format.global_constant = True
                global_format.initializer = c_format_str
                
                # Konwertuj wskaźnik do formatu do i8*
                format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
                
                # Wywołaj scanf
                self.builder.call(self.scanf_func, [format_ptr, temp_var])
                
                # Załaduj odczytaną wartość
                int_value = self.builder.load(temp_var)
                
                # Konwertuj int na bool (niezerowe wartości jako true)
                bool_value = self.builder.icmp_unsigned('!=', int_value, ir.Constant(self.int_type, 0))
                
                # Zapisz wartość bool do zmiennej docelowej
                self.builder.store(bool_value, var_ptr)
                
            else:  # Zwykły typ całkowity
                format_str = "%d\0"
                
                # Tworzymy globalną zmienną dla format stringa
                c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                        bytearray(format_str.encode("utf8")))
                
                global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                                name=f".str.scanf.{next(self._global_counter)}")
                global_format.linkage = 'internal'
                global_format.global_constant = True
                global_format.initializer = c_format_str
                
                # Konwertuj wskaźnik do formatu do i8*
                format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
                
                # Wywołaj scanf
                self.builder.call(self.scanf_func, [format_ptr, var_ptr])
                
        elif isinstance(var_type, ir.FloatType) or isinstance(var_type, ir.DoubleType):
            # Obsługa odczytu dla typów zmiennoprzecinkowych
            self.handle_float_read(var_ptr, var_type)
            
        elif isinstance(var_type, ir.PointerType) and var_type.pointee == ir.IntType(8):
            # Dla string używamy tymczasowego bufora o stałym rozmiarze
            buffer_size = 1024
            buffer_type = ir.ArrayType(ir.IntType(8), buffer_size)
            
            # Alokuj bufor na stosie
            buffer_ptr = self.builder.alloca(buffer_type, name=f"{node.name}_buffer")
            
            # Format dla scanf - odczyt stringa (%s)
            format_str = "%s\0"
            c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), 
                                    bytearray(format_str.encode("utf8")))
            
            global_format = ir.GlobalVariable(self.module, c_format_str.type, 
                                            name=f".str.scanf.{next(self._global_counter)}")
            global_format.linkage = 'internal'
            global_format.global_constant = True
            global_format.initializer = c_format_str
            
            # Konwertuj wskaźnik do formatu do i8*
            format_ptr = self.builder.bitcast(global_format, ir.PointerType(ir.IntType(8)))
            
            # Konwertuj wskaźnik do bufora do i8*
            buffer_i8_ptr = self.builder.bitcast(buffer_ptr, ir.PointerType(ir.IntType(8)))
            
            # Wywołaj scanf
            self.builder.call(self.scanf_func, [format_ptr, buffer_i8_ptr])
            
            # Zapisz wskaźnik do bufora w zmiennej
            self.builder.store(buffer_i8_ptr, var_ptr)
            
        else:
            raise ValueError(f"Nieobsługiwany typ dla operacji read: {var_type}")
        
        return None