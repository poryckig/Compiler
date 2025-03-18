from antlr4.error.ErrorListener import ErrorListener

class CompilerErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        # Dla brakujących średników, nie precyzuj konkretnej linii
        if "missing ';'" in msg:
            error_msg = f"Błąd składniowy: brak średnika przed '{offendingSymbol.text}' w linii {line}"
        else:
            error_msg = f"Błąd składniowy w linii {line}:{column} - {msg}"
        
        self.errors.append(error_msg)
        print(error_msg)

    def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact, ambigAlts, configs):
        error_msg = f"Niejednoznaczność w gramatyce od indeksu {startIndex} do {stopIndex}"
        self.errors.append(error_msg)
        print(error_msg)

    def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex, conflictingAlts, configs):
        # Możemy zignorować te komunikaty lub zapisać je do logów
        pass

    def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex, prediction, configs):
        # Możemy zignorować te komunikaty lub zapisać je do logów
        pass
        
    def has_errors(self):
        return len(self.errors) > 0