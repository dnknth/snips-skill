
# parsetab.py
# This file is automatically generated. Do not edit.
# pylint: disable=W,C,R
_tabversion = '3.10'

_lr_method = 'LALR'

_lr_signature = 'leftORleftANDrightNOTleftGREATERLESSGREATER_EQUALLESS_EQUALEQUALNOT_EQUALREGEX_MATCHAND EQUAL GREATER GREATER_EQUAL LESS LESS_EQUAL LPAREN NOT NOT_EQUAL NUMBER OR REGEX_MATCH RPAREN STRING TOPICexpr : termexpr : expr AND exprexpr : expr OR exprexpr : NOT exprexpr : LPAREN expr RPARENterm : TOPIC LESS NUMBERterm : TOPIC LESS_EQUAL NUMBERterm : TOPIC GREATER_EQUAL NUMBERterm : TOPIC GREATER NUMBERterm : TOPIC EQUAL literalterm : TOPIC NOT_EQUAL literalterm : TOPIC REGEX_MATCH STRINGliteral : NUMBER\n| STRING'
    
_lr_action_items = {'NOT':([0,3,4,6,7,],[3,3,3,3,3,]),'LPAREN':([0,3,4,6,7,],[4,4,4,4,4,]),'TOPIC':([0,3,4,6,7,],[5,5,5,5,5,]),'$end':([1,2,8,17,18,19,20,21,22,23,24,25,26,27,28,],[0,-1,-4,-2,-3,-5,-6,-7,-8,-9,-10,-13,-14,-11,-12,]),'AND':([1,2,8,9,17,18,19,20,21,22,23,24,25,26,27,28,],[6,-1,-4,6,-2,6,-5,-6,-7,-8,-9,-10,-13,-14,-11,-12,]),'OR':([1,2,8,9,17,18,19,20,21,22,23,24,25,26,27,28,],[7,-1,-4,7,-2,-3,-5,-6,-7,-8,-9,-10,-13,-14,-11,-12,]),'RPAREN':([2,8,9,17,18,19,20,21,22,23,24,25,26,27,28,],[-1,-4,19,-2,-3,-5,-6,-7,-8,-9,-10,-13,-14,-11,-12,]),'LESS':([5,],[10,]),'LESS_EQUAL':([5,],[11,]),'GREATER_EQUAL':([5,],[12,]),'GREATER':([5,],[13,]),'EQUAL':([5,],[14,]),'NOT_EQUAL':([5,],[15,]),'REGEX_MATCH':([5,],[16,]),'NUMBER':([10,11,12,13,14,15,],[20,21,22,23,25,25,]),'STRING':([14,15,16,],[26,26,28,]),}

_lr_action = {}
for _k, _v in _lr_action_items.items():
   for _x,_y in zip(_v[0],_v[1]):
      if not _x in _lr_action:  _lr_action[_x] = {}
      _lr_action[_x][_k] = _y
del _lr_action_items

_lr_goto_items = {'expr':([0,3,4,6,7,],[1,8,9,17,18,]),'term':([0,3,4,6,7,],[2,2,2,2,2,]),'literal':([14,15,],[24,27,]),}

_lr_goto = {}
for _k, _v in _lr_goto_items.items():
   for _x, _y in zip(_v[0], _v[1]):
       if not _x in _lr_goto: _lr_goto[_x] = {}
       _lr_goto[_x][_k] = _y
del _lr_goto_items
_lr_productions = [
  ("S' -> expr","S'",1,None,None,None),
  ('expr -> term','expr',1,'p_expr_term','expr.py',99),
  ('expr -> expr AND expr','expr',3,'p_expr_and','expr.py',103),
  ('expr -> expr OR expr','expr',3,'p_expr_or','expr.py',108),
  ('expr -> NOT expr','expr',2,'p_expr_not','expr.py',113),
  ('expr -> LPAREN expr RPAREN','expr',3,'p_expr_parenthesis','expr.py',118),
  ('term -> TOPIC LESS NUMBER','term',3,'p_term_topic_less_number','expr.py',122),
  ('term -> TOPIC LESS_EQUAL NUMBER','term',3,'p_term_topic_less_equal_number','expr.py',127),
  ('term -> TOPIC GREATER_EQUAL NUMBER','term',3,'p_term_topic_greater_equal_number','expr.py',132),
  ('term -> TOPIC GREATER NUMBER','term',3,'p_term_topic_greater_number','expr.py',137),
  ('term -> TOPIC EQUAL literal','term',3,'p_term_topic_equal_literal','expr.py',142),
  ('term -> TOPIC NOT_EQUAL literal','term',3,'p_term_topic_not_equal_literal','expr.py',148),
  ('term -> TOPIC REGEX_MATCH STRING','term',3,'p_term_topic_regex_match_string','expr.py',154),
  ('literal -> NUMBER','literal',1,'p_literal','expr.py',160),
  ('literal -> STRING','literal',1,'p_literal','expr.py',161),
]
