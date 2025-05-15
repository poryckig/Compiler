grammar lang;

program
    : (structDefinition | classDefinition | functionDeclaration | statement)+ EOF
    ;

structDefinition
    : 'struct' ID '{' structMember+ '}' ';'
    ;

structMember
    : type ID ';'
    ;

classDefinition
    : 'class' ID '{' classMember+ '}' ';'
    ;

classMember
    : type ID ';'                                      # ClassField
    | ID '(' parameterList? ')' blockStatement         # ClassConstructor
    | type ID '(' parameterList? ')' blockStatement    # ClassMethod
    ;

functionDeclaration
    : type ID '(' parameterList? ')' blockStatement
    ;

parameterList
    : parameter (',' parameter)*
    ;

parameter
    : type ID
    ;

statement
    : variableDeclaration ';'
    | assignment ';'
    | printStatement ';'
    | readStatement ';'
    | ifStatement
    | whileStatement
    | forStatement
    | switchStatement
    | returnStatement ';'
    | functionCall ';'
    | methodCall ';'
    | blockStatement
    | breakStatement ';'
    | ';'
    ;

methodCall
    : ID '.' ID '(' argumentList? ')'
    ;

functionCall
    : ID '(' argumentList? ')'
    ;

argumentList
    : expression (',' expression)*
    ;

returnStatement
    : 'return' expression?
    ;

variableDeclaration
    : type ID ('=' expression)?                          # SimpleVarDecl
    | ID ID ('=' structInitializer)?                     # StructVarDecl
    | ID ID ('=' ID '(' argumentList? ')')?              # ClassVarDecl
    | type ID '[' INT ']' ('=' arrayInitializer)?        # ArrayDecl
    | type ID '[' INT ']' '[' INT ']' 
        ('=' matrixInitializer)?                         # MatrixDecl
    ;

structInitializer
    : '{' expression (',' expression)* '}'
    ;

arrayInitializer
    : '{' expression (',' expression)* '}'
    ;

matrixInitializer
    : '{' arrayInitializer (',' arrayInitializer)* '}'
    ;

type
    : 'int'
    | 'float'       // Domyślny typ zmiennoprzecinkowy (float32)
    | 'float32'     // 32-bitowy typ zmiennoprzecinkowy (single precision)
    | 'float64'     // 64-bitowy typ zmiennoprzecinkowy (double precision)
    | 'string'
    | 'bool'
    | 'void'        // Dodany typ void dla funkcji
    | ID
    ;

assignment
    : ID '=' expression                                  # SimpleAssign
    | ID '.' ID '=' expression                           # StructMemberAssign
    | 'this' '.' ID '=' expression                       # ThisMemberAssign
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
    : orExpression                                       # BasicExpr
    | ID '=' expression                                  # AssignExpr
    ;

orExpression
    : xorExpression (('||' | 'or') xorExpression)*
    ;

xorExpression
    : andExpression (('^' | 'xor') andExpression)*
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
    : primaryExpression (('*' | '/' | '%') primaryExpression)*
    ;

primaryExpression
    : '(' expression ')'                                 # ParenExpr
    | functionCall                                       # FuncCallExpr
    | ID '.' ID                                          # StructMemberAccess
    | ID '.' ID '(' argumentList? ')'                    # ObjectMethodCall
    | 'this' '.' ID                                      # ThisMemberAccess
    | ID                                                 # VarExpr
    | ID '[' expression ']'                              # ArrayAccessExpr
    | ID '[' expression ']' '[' expression ']'           # MatrixAccessExpr
    | INT                                                # IntLiteral
    | FLOAT                                              # FloatLiteral
    | STRING                                             # StringLiteral
    | BOOL                                               # BoolLiteral
    ;

ifStatement
    : 'if' '(' expression ')' blockStatement
      ('else' (ifStatement | blockStatement))?
    ;

switchStatement
    : 'switch' '(' expression ')' '{' switchCase* defaultCase? '}'
    ;

switchCase
    : 'case' expression ':' statement*
    ;

defaultCase
    : 'default' ':' statement*
    ;

breakStatement
    : 'break'
    ;

whileStatement
    : 'while' '(' expression ')' blockStatement
    ;

forStatement
    : 'for' '(' forInit? ';' expression? ';' forUpdate? ')' blockStatement
    ;

forInit
    : variableDeclaration
    | assignment
    ;

forUpdate
    : expression
    ;

blockStatement
    : '{' statement* '}'
    ;

ID: [a-zA-Z][a-zA-Z0-9_]*;
INT: [0-9]+;
FLOAT: [0-9]+ '.' [0-9]+;
STRING: '"' (~["\\\r\n] | '\\' ["\\/bfnrt])* '"';
BOOL: 'true' | 'false';
WS: [ \t\r\n]+ -> skip;
COMMENT: '//' ~[\r\n]* -> skip;