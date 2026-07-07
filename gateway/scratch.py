import sqlglot
from sqlglot import exp

def test():
    q = "INSERT INTO users (id, ssn, name) VALUES (1, '123-45', 'Alice')"
    parsed = sqlglot.parse_one(q, read='postgres')
    print(repr(parsed))
    print(parsed.args)
    
    # We want to replace '123-45' with 'encrypted'
    if isinstance(parsed, exp.Insert):
        cols = [c.name.lower() for c in parsed.args.get("this").args.get("expressions", [])]
        print("cols:", cols)
        
        expression = parsed.args.get("expression")
        if isinstance(expression, exp.Values):
            for tuple_expr in expression.expressions:
                # tuple_expr is a Tuple
                for i, val in enumerate(tuple_expr.expressions):
                    if cols[i] == 'ssn' and isinstance(val, exp.Literal) and val.is_string:
                        # Replace string literal
                        val.replace(exp.Literal.string("encrypted"))
    print(parsed.sql("postgres"))
    
    q2 = "UPDATE users SET ssn = '123-45', name = 'Alice' WHERE id = 1"
    parsed2 = sqlglot.parse_one(q2, read='postgres')
    if isinstance(parsed2, exp.Update):
        for eq in parsed2.args.get("expressions", []):
            col_name = eq.left.name.lower()
            val = eq.right
            if col_name == 'ssn' and isinstance(val, exp.Literal) and val.is_string:
                val.replace(exp.Literal.string("encrypted2"))
    print(parsed2.sql("postgres"))
    
test()
