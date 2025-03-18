from antlr4.error.ErrorListener import ErrorListener

class CompilerErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        # Rozróżnienie rodzaju błędu
        if "token recognition error" in msg:
            # To jest błąd leksykalny
            token_char = msg.split("at: '")[1].split("'")[0] if "at: '" in msg else "?"
            error_msg = f"Błąd leksykalny w linii {line}:{column} - nierozpoznany token: '{token_char}'"
        elif "missing ';'" in msg:
            # Brak średnika
            error_msg = f"Błąd składniowy: brak średnika przed '{offendingSymbol.text}' w linii {line}"
        elif "mismatched input" in msg and "expecting" in msg:
            # Niedopasowany token
            expected = msg.split("expecting ")[1]
            error_msg = f"Błąd składniowy w linii {line}:{column} - nieoczekiwany token: '{offendingSymbol.text}', oczekiwano: {expected}"
        else:
            # Inne błędy składniowe
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