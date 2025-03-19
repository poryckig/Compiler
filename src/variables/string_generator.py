import llvmlite.ir as ir

def visit_StringLiteral(self, node):
    """Generuje kod LLVM dla literału stringowego - wersja z lepszym identyfikowaniem."""
    # Usuń cudzysłowy z początku i końca wartości
    string_value = node.value[1:-1]
    
    # Obsługa znaków specjalnych
    string_value = string_value.replace('\\n', '\n')
    string_value = string_value.replace('\\t', '\t')
    string_value = string_value.replace('\\"', '"')
    string_value = string_value.replace('\\\\', '\\')
    
    # Dodaj znak końca stringa
    string_with_null = string_value + '\0'
    
    # Konwertuj string na bajty
    string_bytes = string_with_null.encode('utf-8')
    
    # Długość stringa z bajtem zerowym
    string_length = len(string_bytes)
    
    # Stwórz typ tablicy (string jest tablicą znaków)
    string_type = ir.ArrayType(ir.IntType(8), string_length)
    
    # Stwórz stałą dla zawartości stringa
    string_constant = ir.Constant(string_type, bytearray(string_bytes))
    
    # Utwórz unikalne ID na podstawie treści stringa i licznika
    # Tworzymy hash z treści stringa, aby pomóc w unikatowości
    import hashlib
    string_hash = hashlib.md5(string_bytes).hexdigest()[:8]
    global_id = f"str.{string_hash}.{next(self._global_counter)}"
    
    # Stwórz globalną zmienną dla stringa
    string_global = ir.GlobalVariable(self.module, string_type, name=global_id)
    string_global.linkage = 'private'
    string_global.global_constant = True
    string_global.initializer = string_constant
    
    # Zwróć wskaźnik do pierwszego znaku stringa
    zero = ir.Constant(self.int_type, 0)
    string_ptr = self.builder.gep(string_global, [zero, zero], name=f"{global_id}_ptr")
    
    return string_ptr