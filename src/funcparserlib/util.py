#
# Funcparserlib -- A parser library based on parser combinators
# by Andrey Vlasovskikh et al
#

class SyntaxError(Exception):
    'The base class for funcparserlib errors.'
    def __init__(self, msg, pos, index=None):
        Exception.__init__(self, msg, pos, index)

    @property
    def pos(self):
        'SyntaxError -> ((int, int), (int, int)) or None'
        return self.args[1]

    def __str__(self):
        pos = self.args[1]
        s = '%s: ' % pos_to_str(pos) if pos is not None else ''
        return '%s%s' % (s, self.args[0])

# ----------------

def pretty_tree(x, kids, show):
    '''(a, (a -> list(a)), (a -> str)) -> str

    Returns a pseudographic tree representation of x similar to the tree command
    in Unix.
    '''
    (MID, END, CONT, LAST, ROOT) = ('|-- ', '`-- ', '|   ', '    ', '')
    def rec(x, indent, sym):
        line = indent + sym + show(x)
        xs = kids(x)
        if len(xs) == 0:
            return line
        else:
            if sym == MID:
                next_indent = indent + (CONT)
            elif sym == ROOT:
                next_indent = indent + (ROOT)
            else:
                next_indent = indent + (LAST)
            syms = [MID] * (len(xs) - 1) + [END]
            lines = [rec(x, next_indent, sym) for x, sym in zip(xs, syms)]
            return '\n'.join([line] + lines)
    return rec(x, '', ROOT)

# ----------------

def pos_to_str(pos):
    '((int, int), (int, int)) -> str'
    start, end = pos
    sl, sp = start
    el, ep = end
    return '%d,%d-%d,%d' % (sl, sp, el, ep)
