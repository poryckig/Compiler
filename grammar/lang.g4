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
    | 'string'
    | 'bool'
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
    : orExpression
    ;

orExpression
    : andExpression (('||' | 'or') andExpression)*
    ;

andExpression
    : notExpression (('&&' | 'and') notExpression)*
    ;

notExpression
    : ('!' | 'not') notExpression
    | comparisonExpression
    ;

comparisonExpression
    : additiveExpression (comparisonOperator additiveExpression)?
    ;

comparisonOperator
    : '==' | '!=' | '<' | '>' | '<=' | '>='
    ;

additiveExpression
    : multiplicativeExpression (('+' | '-') multiplicativeExpression)*
    ;

multiplicativeExpression
    : primaryExpression (('*' | '/') primaryExpression)*
    ;

primaryExpression
    : '(' expression ')'
    | ID
    | ID '[' expression ']'
    | ID '[' expression ']' '[' expression ']'
    | INT
    | FLOAT
    | STRING
    | BOOL
    ;

ID: [a-zA-Z][a-zA-Z0-9_]*;
INT: [0-9]+;
FLOAT: [0-9]+ '.' [0-9]+;
STRING: '"' (~["\\\r\n] | '\\' ["\\/bfnrt])* '"';
BOOL: 'true' | 'false';
WS: [ \t\r\n]+ -> skip;
COMMENT: '//' ~[\r\n]* -> skip;