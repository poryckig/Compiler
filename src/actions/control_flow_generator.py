import llvmlite.ir as ir
from src.syntax_tree.ast_nodes import BreakStatement

def visit_IfStatement(self, node):
    """Generuje kod LLVM dla instrukcji warunkowej if."""
    # Generowanie kodu dla warunku
    condition = self.visit(node.condition)
    
    # Jeśli warunek jest wskaźnikiem, załaduj wartość
    if isinstance(condition.type, ir.PointerType):
        condition = self.builder.load(condition)
    
    # Konwersja do typu bool (i1) jeśli potrzeba
    if isinstance(condition.type, ir.FloatType) or isinstance(condition.type, ir.DoubleType):
        condition = self.builder.fcmp_ordered('!=', condition, ir.Constant(condition.type, 0.0))
    elif not isinstance(condition.type, ir.IntType) or condition.type.width != 1:
        condition = self.builder.icmp_signed('!=', condition, ir.Constant(condition.type, 0))
    
    # Tworzenie bloków dla then, else i kontynuacji
    then_block = self.builder.append_basic_block(name="if.then")
    
    # Blok else potrzebny tylko jeśli jest instrukcja else
    if node.else_block:
        else_block = self.builder.append_basic_block(name="if.else")
    else:
        else_block = None
    
    # Blok, do którego przejdziemy po wykonaniu if/else
    merge_block = self.builder.append_basic_block(name="if.end")
    
    # Skok warunkowy
    if else_block:
        self.builder.cbranch(condition, then_block, else_block)
    else:
        self.builder.cbranch(condition, then_block, merge_block)
    
    # Generowanie kodu dla bloku then
    self.builder.position_at_end(then_block)
    self.visit(node.then_block)
    
    # Jeśli blok then nie kończy się instrukcją return, dodaj skok do merge_block
    if not self.builder.block.is_terminated:
        self.builder.branch(merge_block)
    
    # Generowanie kodu dla bloku else, jeśli istnieje
    if node.else_block:
        self.builder.position_at_end(else_block)
        self.visit(node.else_block)
        
        # Jeśli blok else nie kończy się instrukcją return, dodaj skok do merge_block
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)
    
    # Przejście do bloku końcowego
    self.builder.position_at_end(merge_block)
    
    return None

def visit_SwitchStatement(self, node):
    """Generuje kod LLVM dla instrukcji switch."""
    # Generowanie kodu dla wyrażenia switch
    switch_expr = self.visit(node.expression)
    
    # Jeśli wyrażenie jest wskaźnikiem, załaduj wartość
    if isinstance(switch_expr.type, ir.PointerType):
        switch_expr = self.builder.load(switch_expr)
    
    # Upewnij się, że wyrażenie jest typu całkowitego
    if not isinstance(switch_expr.type, ir.IntType):
        raise ValueError("Wyrażenie w instrukcji switch musi być typu całkowitego")
    
    # Tworzenie bloku dla kodu po instrukcji switch (kontynuacja)
    end_block = self.builder.append_basic_block(name="switch.end")
    
    # Zapisz blok końcowy, aby break mógł do niego skakać
    old_break_block = getattr(self, "_break_block", None)
    self._break_block = end_block
    
    # Tworzenie bloku dla przypadku default
    if node.default_case:
        default_block = self.builder.append_basic_block(name="switch.default")
    else:
        default_block = end_block
    
    # Tworzenie instrukcji switch
    switch = self.builder.switch(switch_expr, default_block)
    
    # Słownik do śledzenia bloków dla każdego przypadku
    case_blocks = {}
    
    # Tworzenie bloków dla każdego przypadku
    for case in node.cases:
        case_value = self.visit(case.value)
        if isinstance(case_value.type, ir.PointerType):
            case_value = self.builder.load(case_value)
        
        # Upewnij się, że wartość case jest stała
        if not isinstance(case_value, ir.Constant):
            raise ValueError("Wartość w instrukcji case musi być stała")
        
        case_block = self.builder.append_basic_block(name="switch.case")
        case_blocks[case] = case_block
        switch.add_case(case_value, case_block)
    
    # Generowanie kodu dla każdego przypadku
    for i, case in enumerate(node.cases):
        case_block = case_blocks[case]
        self.builder.position_at_end(case_block)
        
        # Flaga do śledzenia instrukcji break
        found_break = False
        
        # Generowanie kodu dla instrukcji w tym przypadku
        for stmt in case.statements:
            if isinstance(stmt, BreakStatement):
                found_break = True
                self.builder.branch(end_block)
                break
            else:
                self.visit(stmt)
        
        # Jeśli blok nie jest zakończony (nie ma break ani return)
        if not self.builder.block.is_terminated:
            # Jeśli to ostatni case, przejdź do default lub końca
            if i == len(node.cases) - 1:
                if node.default_case:
                    self.builder.branch(default_block)
                else:
                    self.builder.branch(end_block)
            else:
                # Przejdź do następnego case (zachowanie case fallthrough)
                next_case = node.cases[i + 1]
                self.builder.branch(case_blocks[next_case])
    
    # Generowanie kodu dla przypadku default
    if node.default_case:
        self.builder.position_at_end(default_block)
        
        # Generowanie kodu dla instrukcji w przypadku default
        for stmt in node.default_case.statements:
            if isinstance(stmt, BreakStatement):
                self.builder.branch(end_block)
                break
            else:
                self.visit(stmt)
        
        # Jeśli blok default nie kończy się instrukcją break lub return
        if not self.builder.block.is_terminated:
            self.builder.branch(end_block)
    
    # Przejście do bloku końcowego
    self.builder.position_at_end(end_block)
    
    # Przywróć poprzedni blok break
    self._break_block = old_break_block
    
    return None

def visit_BreakStatement(self, node):
    """Generuje kod LLVM dla instrukcji break."""
    # Sprawdź, czy mamy zapisany blok końcowy
    if hasattr(self, "_break_block") and self._break_block:
        self.builder.branch(self._break_block)
    else:
        raise ValueError("Instrukcja break może być używana tylko w pętli lub instrukcji switch")
    
    return None

def visit_WhileStatement(self, node):
    """Generuje kod LLVM dla pętli while."""
    # Tworzenie bloków dla warunku, ciała pętli i kontynuacji
    cond_block = self.builder.append_basic_block(name="while.cond")
    body_block = self.builder.append_basic_block(name="while.body")
    end_block = self.builder.append_basic_block(name="while.end")
    
    # Skok do bloku warunku
    self.builder.branch(cond_block)
    
    # Generowanie kodu dla warunku
    self.builder.position_at_end(cond_block)
    condition = self.visit(node.condition)
    
    # Jeśli warunek jest wskaźnikiem, załaduj wartość
    if isinstance(condition.type, ir.PointerType):
        condition = self.builder.load(condition)
    
    # Konwersja do typu bool (i1) jeśli potrzeba
    if isinstance(condition.type, ir.FloatType) or isinstance(condition.type, ir.DoubleType):
        condition = self.builder.fcmp_ordered('!=', condition, ir.Constant(condition.type, 0.0))
    elif not isinstance(condition.type, ir.IntType) or condition.type.width != 1:
        condition = self.builder.icmp_signed('!=', condition, ir.Constant(condition.type, 0))
    
    # Skok warunkowy
    self.builder.cbranch(condition, body_block, end_block)
    
    # Generowanie kodu dla ciała pętli
    self.builder.position_at_end(body_block)
    self.visit(node.body)
    
    # Powrót do warunku
    if not self.builder.block.is_terminated:
        self.builder.branch(cond_block)
    
    # Przejście do bloku końcowego
    self.builder.position_at_end(end_block)
    
    return None

def visit_ForStatement(self, node):
    """Generuje kod LLVM dla pętli for."""
    # Generowanie kodu dla inicjalizacji
    if node.init:
        self.visit(node.init)
    
    # Tworzenie bloków dla warunku, aktualizacji, ciała pętli i kontynuacji
    cond_block = self.builder.append_basic_block(name="for.cond")
    body_block = self.builder.append_basic_block(name="for.body")
    update_block = self.builder.append_basic_block(name="for.update")
    end_block = self.builder.append_basic_block(name="for.end")
    
    # Skok do bloku warunku
    self.builder.branch(cond_block)
    
    # Generowanie kodu dla warunku
    self.builder.position_at_end(cond_block)
    if node.condition:
        condition = self.visit(node.condition)
        
        # Jeśli warunek jest wskaźnikiem, załaduj wartość
        if isinstance(condition.type, ir.PointerType):
            condition = self.builder.load(condition)
        
        # Konwersja do typu bool (i1) jeśli potrzeba
        if isinstance(condition.type, ir.FloatType) or isinstance(condition.type, ir.DoubleType):
            condition = self.builder.fcmp_ordered('!=', condition, ir.Constant(condition.type, 0.0))
        elif not isinstance(condition.type, ir.IntType) or condition.type.width != 1:
            condition = self.builder.icmp_signed('!=', condition, ir.Constant(condition.type, 0))
        
        # Skok warunkowy
        self.builder.cbranch(condition, body_block, end_block)
    else:
        # Jeśli nie ma warunku, zawsze wykonuj ciało pętli
        self.builder.branch(body_block)
    
    # Generowanie kodu dla ciała pętli
    self.builder.position_at_end(body_block)
    self.visit(node.body)
    
    # Skok do bloku aktualizacji
    if not self.builder.block.is_terminated:
        self.builder.branch(update_block)
    
    # Generowanie kodu dla aktualizacji
    self.builder.position_at_end(update_block)
    if node.update:
        self.visit(node.update)
    
    # Powrót do warunku
    self.builder.branch(cond_block)
    
    # Przejście do bloku końcowego
    self.builder.position_at_end(end_block)
    
    return None

def visit_Block(self, node):
    """Generuje kod LLVM dla bloku instrukcji."""
    # Odwiedź wszystkie instrukcje w bloku
    for stmt in node.statements:
        self.visit(stmt)
    return None