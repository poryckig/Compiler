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
    : type ID ('=' expression)?                          # SimpleVarDecl
    | type ID '[' INT ']' ('=' arrayInitializer)?        # ArrayDecl
    | type ID '[' INT ']' '[' INT ']' 
        ('=' matrixInitializer)?                         # MatrixDecl
    ;

arrayInitializer
    : '{' expression (',' expression)* '}'
    ;

matrixInitializer
    : '{' arrayInitializer (',' arrayInitializer)* '}'
    ;

type
    : 'int'
    | 'float'
    | 'string'               // Typ string
    ;

assignment
    : ID '=' expression                                  # SimpleAssign
    | ID '[' expression ']' '=' expression               # ArrayAssign
    | ID '[' expression ']' '[' expression ']' 
        '=' expression                                   # MatrixAssign
    ;

printStatement
    : 'print' expression
    ;

readStatement
    : 'read' ID                                          # SimpleRead
    | 'read' ID '[' expression ']'                       # ArrayRead
    | 'read' ID '[' expression ']' '[' expression ']'    # MatrixRead
    ;

expression
    : multiplyingExpression (('+' | '-') multiplyingExpression)*   # AddSubExpr
    ;

multiplyingExpression
    : primaryExpression (('*' | '/') primaryExpression)*           # MulDivExpr
    ;

primaryExpression
    : '(' expression ')'                                 # ParenExpr
    | ID                                                 # VarExpr
    | ID '[' expression ']'                              # ArrayAccessExpr
    | ID '[' expression ']' '[' expression ']'           # MatrixAccessExpr
    | INT                                                # IntLiteral
    | FLOAT                                              # FloatLiteral
    | STRING                                             # StringLiteral
    ;

ID: [a-zA-Z][a-zA-Z0-9_]*;
INT: [0-9]+;
FLOAT: [0-9]+ '.' [0-9]+;
STRING: '"' (~["\\\r\n] | '\\' ["\\/bfnrt])* '"';        // Literał stringowy
WS: [ \t\r\n]+ -> skip;
COMMENT: '//' ~[\r\n]* -> skip;