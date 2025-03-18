grammar lang;

program: statement+ EOF;

statement
    : variableDeclaration ';'
    | assignment ';'
    | printStatement ';'
    | readStatement ';'
    | ';'
    ;

variableDeclaration
    : type ID ('=' expression)?                           # SimpleVarDecl
    | type ID '[' INT ']' ('=' arrayInitializer)?         # ArrayDecl
    ;

arrayInitializer
    : '{' expression (',' expression)* '}'
    ;

type
    : 'int'
    | 'float'
    ;

assignment
    : ID '=' expression                                  # SimpleAssign
    | ID '[' expression ']' '=' expression               # ArrayAssign
    ;

printStatement
    : 'print' expression
    ;

readStatement
    : 'read' ID                                          # SimpleRead
    | 'read' ID '[' expression ']'                       # ArrayRead
    ;

expression
    : expression ('*' | '/') expression                  # MulDivExpr
    | expression ('+' | '-') expression                  # AddSubExpr
    | '(' expression ')'                                 # ParenExpr
    | ID                                                 # VarExpr
    | ID '[' expression ']'                              # ArrayAccessExpr
    | INT                                                # IntLiteral
    | FLOAT                                              # FloatLiteral
    ;

ID: [a-zA-Z][a-zA-Z0-9_]*;
INT: [0-9]+;
FLOAT: [0-9]+ '.' [0-9]+;
WS: [ \t\r\n]+ -> skip;
COMMENT: '//' ~[\r\n]* -> skip;