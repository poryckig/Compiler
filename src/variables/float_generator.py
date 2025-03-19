import llvmlite.ir as ir

def visit_FloatLiteral(self, node):
        # Debugowanie
        print(f"Tworzenie literału zmiennoprzecinkowego: {node.value}")
        
        # Konwersja do poprawnej wartości float
        float_value = float(node.value)
        print(f"Wartość po konwersji: {float_value}")
        
        # Zwróć stałą zmiennoprzecinkową
        constant = ir.Constant(self.float_type, float_value)
        print(f"Tworzę stałą zmiennoprzecinkową typu: {constant.type}")
        return constant