import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from antlr4 import FileStream, CommonTokenStream
from src.parser.generated.langLexer import langLexer
from src.parser.generated.langParser import langParser
from src.syntax_tree.ast_builder import ASTBuilder
from src.codegen.llvm_generator import LLVMGenerator
from src.utils.error_handler import CompilerErrorListener

DEBUG = False

def print_ast(node, indent=0):
    """Pomocnicza funkcja do wyświetlania AST w formie drzewa"""
    if node is None:
        return
        
    # Formatuj nazwę klasy i ewentualne atrybuty
    node_type = type(node).__name__
    attributes = []
    
    if hasattr(node, 'name'):
        attributes.append(f"name='{node.name}'")
    if hasattr(node, 'var_type'):
        attributes.append(f"type='{node.var_type}'")
    if hasattr(node, 'value') and not hasattr(node, 'left'):  # Dla prostych wartości
        if isinstance(node.value, (int, float)):
            attributes.append(f"value={node.value}")
        elif isinstance(node.value, str):
            attributes.append(f"value='{node.value}'")
    if hasattr(node, 'operator'):
        attributes.append(f"op='{node.operator}'")
    
    attrs_str = ", ".join(attributes)
    if attrs_str:
        print(" " * indent + f"{node_type}({attrs_str})")
    else:
        print(" " * indent + node_type)
    
    # Rekurencyjnie wyświetl dzieci
    if hasattr(node, 'statements'):
        for stmt in node.statements:
            print_ast(stmt, indent + 2)
    if hasattr(node, 'initial_value') and node.initial_value is not None:
        print(" " * (indent + 2) + "initial_value:")
        print_ast(node.initial_value, indent + 4)
    if hasattr(node, 'expression'):
        print(" " * (indent + 2) + "expression:")
        print_ast(node.expression, indent + 4)
    if hasattr(node, 'left'):
        print(" " * (indent + 2) + "left:")
        print_ast(node.left, indent + 4)
    if hasattr(node, 'right'):
        print(" " * (indent + 2) + "right:")
        print_ast(node.right, indent + 4)

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <input_file>")
        return
    
    input_file = sys.argv[1]
    print(f"Przetwarzanie pliku: {input_file}")
    
    try:
        # Tworzenie i rejestracja ErrorListener
        error_listener = CompilerErrorListener()
        
        # 1. Analiza leksykalna
        input_stream = FileStream(input_file, encoding='utf-8')
        lexer = langLexer(input_stream)
        lexer.removeErrorListeners()  # Usuń domyślny listener
        lexer.addErrorListener(error_listener)
        tokens = CommonTokenStream(lexer)
        
        # 2. Analiza składniowa
        parser = langParser(tokens)
        parser.removeErrorListeners()  # Usuń domyślny listener
        parser.addErrorListener(error_listener)
        tree = parser.program()
        
        # Sprawdź czy były błędy
        if error_listener.has_errors():
            print("Kompilacja przerwana z powodu błędów.")
            return
        
        # 3. Budowa AST
        if DEBUG: print("Budowanie AST...")
        ast_builder = ASTBuilder()
        ast = ast_builder.visit(tree)
        
        # 4. Wyświetlenie AST (do debugowania)
        if ast:
            if DEBUG:
                print("AST utworzone pomyślnie:")
                print_ast(ast)
        else:
            print("AST nie zostało utworzone poprawnie.")
            return
        
        # 5. Generowanie kodu LLVM IR
        if DEBUG: print("Generowanie kodu LLVM IR...")
        generator = LLVMGenerator()
        llvm_ir = generator.generate(ast)
        
        # 6. Zapis wygenerowanego kodu
        output_file = input_file.replace('.lang', '.ll')
        with open(output_file, 'w') as f:
            f.write(llvm_ir)
        
        print(f"Kompilacja zakończona. Wyjście zapisane do {output_file}")
        
    except Exception as e:
        print(f"Błąd: {str(e)}")
        import traceback
        traceback.print_exc()
        
if __name__ == '__main__':
    main()