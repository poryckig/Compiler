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
    : expression ('*' | '/') expression                  # MulDivExpr
    | expression ('+' | '-') expression                  # AddSubExpr
    | '(' expression ')'                                 # ParenExpr
    | ID                                                 # VarExpr
    | ID '[' expression ']'                              # ArrayAccessExpr
    | ID '[' expression ']' '[' expression ']'           # MatrixAccessExpr
    | INT                                                # IntLiteral
    | FLOAT                                              # FloatLiteral
    ;

ID: [a-zA-Z][a-zA-Z0-9_]*;
INT: [0-9]+;
FLOAT: [0-9]+ '.' [0-9]+;
WS: [ \t\r\n]+ -> skip;
COMMENT: '//' ~[\r\n]* -> skip;