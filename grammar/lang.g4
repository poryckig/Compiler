grammar lang;

program: statement+ EOF;

statement
    : variableDeclaration ';'
    | assignment ';'
    | printStatement ';'
    | readStatement ';'
    ;

variableDeclaration
    : type ID ('=' expression)?
    ;

type
    : 'int'
    | 'float'
    ;

assignment
    : ID '=' expression
    ;

printStatement
    : 'print' expression
    ;

readStatement
    : 'read' ID
    ;

expression
    : expression ('*' | '/') expression
    | expression ('+' | '-') expression
    | '(' expression ')'
    | ID
    | INT
    | FLOAT
    ;

ID: [a-zA-Z][a-zA-Z0-9]*;
INT: [0-9]+;
FLOAT: [0-9]+ '.' [0-9]+;
WS: [ \t\r\n]+ -> skip;
COMMENT: '//' ~[\r\n]* -> skip;