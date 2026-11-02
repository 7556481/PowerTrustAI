"""Versioned exact supported FTS expression subset; no query rewriting."""
import re

def ast(expression):
 """Supported actual one-field FTS subset; fail explicitly on extensions."""
 pattern=re.compile(r'\s*("(?:[^"\n]|"")*"|AND\b|OR\b|NOT\b|terms:|[()])')
 tokens=[];pos=0
 while pos<len(expression):
  if not expression[pos:].strip():break
  m=pattern.match(expression,pos)
  if not m:raise ValueError('Unsupported FTS syntax at '+str(pos))
  tokens.append(m[1]);pos=m.end()
 i=0
 def primary():
  nonlocal i
  if i>=len(tokens):raise ValueError('Missing operand')
  t=tokens[i];i+=1
  if t=='terms:':return primary()
  if t=='(':
   x=or_expr()
   if i>=len(tokens) or tokens[i]!=')':raise ValueError('Unbalanced parentheses')
   i+=1;return x
  if not t.startswith('"'):raise ValueError('Expected quoted term/phrase')
  words=t[1:-1].replace('""','"').split()
  if not words or any(not re.fullmatch(r'[a-z0-9\u3400-\u4dbf\u4e00-\u9fff]+',w) for w in words):raise ValueError('Not pretokenized vocabulary')
  return ['phrase',words]
 def not_expr():
  nonlocal i
  x=primary()
  while i<len(tokens) and tokens[i]=='NOT':i+=1;x=['not',x,primary()]
  return x
 def and_expr():
  nonlocal i
  x=not_expr()
  while i<len(tokens) and tokens[i]=='AND':i+=1;x=['and',x,not_expr()]
  return x
 def or_expr():
  nonlocal i
  x=and_expr()
  while i<len(tokens) and tokens[i]=='OR':i+=1;x=['or',x,and_expr()]
  return x
 if not tokens:return None
 tree=or_expr()
 if i!=len(tokens):raise ValueError('Unconsumed FTS syntax')
 return tree

def query(index,tree):
 import tantivy as t
 if tree is None:return t.Query.empty_query()
 op=tree[0]
 if op=='phrase':return t.Query.term_query(index.schema,'terms',tree[1][0]) if len(tree[1])==1 else t.Query.phrase_query(index.schema,'terms',tree[1])
 a,b=query(index,tree[1]),query(index,tree[2])
 return t.Query.boolean_query([(t.Occur.Must if op!='or' else t.Occur.Should,a),(t.Occur.MustNot if op=='not' else t.Occur.Must if op=='and' else t.Occur.Should,b)])
