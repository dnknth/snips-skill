from collections import namedtuple
import ply.lex as lex
import ply.yacc as yacc
import re


class Parser:
    'Parse very simple expressions into callable boolean conditions'
    
    class Expr(namedtuple('Expr', 'keys expr')):
        '''
            Container for a callable boolean predicate
            along with the topic names being evaluated
        '''
        last_state = None
        
        def __call__(self, *args, **kw):
            'Syntactic sugar'
            self.last_state = self.expr(*args, **kw)
            return self.last_state
            
        def __hash__(self):
            return hash(self.expr)


    tokens = (
        'TOPIC',
        'LESS',
        'LESS_EQUAL',
        'EQUAL',
        'REGEX_MATCH',
        'GREATER_EQUAL',
        'GREATER',
        'NOT_EQUAL',
        'NUMBER',
        'NOT',
        'AND',
        'OR',
        'LPAREN',
        'RPAREN',
        'STRING',
    )

    t_TOPIC         = r'[\w_-]+(/[\w_-]+)+'
    t_GREATER       = r'>'
    t_LESS          = r'<'
    t_EQUAL         = r'=='
    t_REGEX_MATCH   = r'~='
    t_GREATER_EQUAL = r'>='
    t_LESS_EQUAL    = r'<='
    t_NOT_EQUAL     = r'!='
    t_NOT           = r'not'
    t_AND           = r'and'
    t_OR            = r'or'
    t_LPAREN        = r'\('
    t_RPAREN        = r'\)'

    # Ignored characters
    t_ignore        = ' \t\r\n'

    def t_NUMBER(self, t):
        r'(\+|-)?\d+(\.\d+)?'
        t.value = float(t.value)    
        return t

    def t_STRING(self, t):
        r"'[^']*'"
        t.value = t.value[1:-1]
        return t
        
    # Track line numbers
    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    def t_error(self, t):
        assert False, "Illegal character '%s'" % t.value[0]

    #-#-# Grammar rules below #-#-#

    precedence = (
        ('left',  'OR'),
        ('left',  'AND'),
        ('right', 'NOT'),
        ('left',  'GREATER', 'LESS', 'GREATER_EQUAL', 'LESS_EQUAL',
                  'EQUAL', 'NOT_EQUAL', 'REGEX_MATCH'),
    )
    
    def p_expr_term(self, p):
        'expr : term'
        p[0] = p[1]

    def p_expr_and(self, p):
        'expr : expr AND expr'
        lhs, rhs = p[1], p[3]
        p[0] = self.Expr(lhs.keys | rhs.keys, lambda s: lhs(s) and rhs(s))

    def p_expr_or(self, p):
        'expr : expr OR expr'
        lhs, rhs = p[1], p[3]
        p[0] = self.Expr(lhs.keys | rhs.keys, lambda s: lhs(s) or rhs(s))

    def p_expr_not(self, p):
        'expr : NOT expr'
        cond = p[2]
        p[0] = self.Expr(cond.keys, lambda s: not cond(s))

    def p_expr_parenthesis(self, p):
        'expr : LPAREN expr RPAREN'
        p[0] = p[2]

    def p_term_topic_less_number(self, p):
        'term : TOPIC LESS NUMBER'
        lhs, rhs = p[1], p[3]
        p[0] = self.Expr(set([lhs]), lambda s: float(s[lhs]) < rhs)
        
    def p_term_topic_less_equal_number(self, p):
        'term : TOPIC LESS_EQUAL NUMBER'
        lhs, rhs = p[1], p[3]
        p[0] = self.Expr(set([lhs]), lambda s: float(s[lhs]) <= rhs)
        
    def p_term_topic_greater_equal_number(self, p):
        'term : TOPIC GREATER_EQUAL NUMBER'
        lhs, rhs = p[1], p[3]
        p[0] = self.Expr(set([lhs]), lambda s: float(s[lhs]) >= rhs)
        
    def p_term_topic_greater_number(self, p):
        'term : TOPIC GREATER NUMBER'
        lhs, rhs = p[1], p[3]
        p[0] = self.Expr(set([lhs]), lambda s: float(s[lhs]) > rhs)
        
    def p_term_topic_equal_literal(self, p):
        'term : TOPIC EQUAL literal'
        lhs, rhs = p[1], p[3]
        cast = type(rhs)
        p[0] = self.Expr(set([lhs]), lambda s: cast(s[lhs]) == rhs)
        
    def p_term_topic_not_equal_literal(self, p):
        'term : TOPIC NOT_EQUAL literal'
        lhs, rhs = p[1], p[3]
        cast = type(rhs)
        p[0] = self.Expr(set([lhs]), lambda s: cast(s[lhs]) != rhs)
        
    def p_term_topic_regex_match_string(self, p):
        'term : TOPIC REGEX_MATCH STRING'
        lhs, rhs = p[1], p[3]
        pattern = re.compile(rhs)
        p[0] = self.Expr(set([lhs]), lambda s: pattern.search(str(s[lhs])) is not None)
        
    def p_literal(self, p):
        '''literal : NUMBER
                   | STRING'''
        p[0] = p[1]

    def p_error(self, p):
        assert False, 'Syntax error at: %s' % (p or 'EOF')

    def __init__(self, **kwargs):
        self.lexer = lex.lex(module=self)
        self.parser = yacc.yacc(module=self, **kwargs)
        
    def parse(self, text, **kwargs):
        return self.parser.parse(text, lexer=self.lexer, **kwargs)
