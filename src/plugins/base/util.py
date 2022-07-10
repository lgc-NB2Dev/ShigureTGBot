def escape_md(txt: str):
    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for c in chars:
        txt = txt.replace(c, f'\\{c}')
    return txt
