"""Punctuation-only diagnostics; never repair invalid JSON or retain its text."""
def diagnostic(text):
    stack=[];inside=False;escaped=False
    for position,ch in enumerate(text):
        if inside:
            if escaped:escaped=False
            elif ch=='\\':escaped=True
            elif ch=='"':inside=False
            continue
        if ch=='"':inside=True
        elif ch in '{[':stack.append(ch)
        elif ch in '}]':
            expected='}' if stack and stack[-1]=='{' else ']' if stack else None
            if ch!=expected:return {'nesting_position':position,'actual_closer':ch,'expected_closer':expected}
            stack.pop()
    return {'unclosed_containers':len(stack),'unclosed_string':inside}
