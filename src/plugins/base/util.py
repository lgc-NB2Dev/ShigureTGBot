def escape_md(txt: str):
    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for c in chars:
        txt.replace(c, f'\\{c}')
    return txt
