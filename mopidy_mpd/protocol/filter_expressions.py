from mopidy_mpd import exceptions

class peekable:
    """ an iterator that can be peeked one element into the future """
    def __init__(self, it):
        self._it = iter(it)
        self._poked = []
    def __iter__(self):
        return self
    def __next__(self):
        if self._poked:
            return self._poked.pop()
        return next(self._it)
    def __bool__(self):
        try:
            self.peek()
            return True
        except StopIteration:
            return False
    def peek(self):
        if not self._poked:
            self._poked = [next(self._it)]
        return self._poked[0]

def takewhile(it, f):
    def gen(it):
        while it and f(it.peek()):
            yield next(it)
    return ''.join(gen(it))

def is_tagname(c):
    return (  # A-Z, a-z or '-' or '_'
        ord('A') <= ord(c) <= ord('Z') or
        ord('a') <= ord(c) <= ord('z') or
        c in '-_'
    )

def is_operator(c):
    return (  # A-Z, a-z or '!' or '=' or '~'
        ord('A') <= ord(c) <= ord('Z') or
        ord('a') <= ord(c) <= ord('z') or
        c in '!=~'
    )

def takeWord(it, alphabet=is_tagname):
    value = takewhile(it, alphabet)
    takewhile(it, str.isspace)
    return value

def takeChar(it):
    c = next(it)
    takewhile(it, str.isspace)
    return c

def takeQuoted(it):
    def gen(it, quote):
        while it and it.peek() != quote:
            c = next(it)
            if c == '\\':
                c = next(it)
            yield c

    quote = next(it)
    Assert(quote in '\'"', "Quoted string expected")
    value = ''.join(gen(it, quote))
    Assert(next(it) == quote, "Closing quote not found")
    takewhile(it, str.isspace)
    return value


def Assert(p, message):
    if not p:
        raise exceptions.MpdArgError(message)

class parenthesis:
    def __init__(self, it):
        self.it = it
    def __enter__(self):
        c = takeChar(self.it)
        Assert(c == '(', "'(' expected")
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            c = takeChar(self.it)
            Assert(c == ')', "')' expected")

operators_inverted = {
    '==': '!=',
    '!=': '==',
    '=~': '!~',
    '!~': '=~',
    'contains': '!contains',
    '!contains': 'contains',
}

def parse_subexpression(it):
    with parenthesis(it):
        if it.peek() == '!':  # (!EXPRESSION)
            takeChar(it)  # consume '!'
            subexpression = parse_subexpression(it)
            Assert(
                # Mopidy doesn't support either-this-or-that style queries.
                len(subexpression) == 1,
                "inverting (AND) not supported"
            )
            filter_type, operator, value = subexpression[0]
            inverted_operator = operators_inverted[operator]
            return [(filter_type, inverted_operator, value)]

        elif it.peek() == '(':  # (EXPRESSION1 AND EXPRESSION2 ...)
            subexpressions = [parse_subexpression(it)]
            while it.peek() != ')':
                Assert(takeWord(it).upper() == "AND", "'AND' expected")
                subexpression = parse_subexpression(it)
                subexpressions.extend(subexpression)
            return subexpressions

        else: # (TAG OP 'VALUE') or (SPECIAL 'VALUE')
            filter_type = takeWord(it)
            if filter_type == "":
                raise exceptions.MpdArgError('Word expected')
            elif filter_type in ("base", "modified-since"):
                # (base 'VALUE'), (modified-since 'VALUE')
                value = takeQuoted(it)
                return [(filter_type, '==', value)]
            else:  # TAG, 'any', 'file', 'filename', 'AudioFormat'
                operator = takeWord(it, is_operator).lower()
                Assert(
                    operator in operators_inverted.keys(),
                    'invalid operator'
                )
                value = takeQuoted(it)
                return [(filter_type, operator, value)]

def parse_filter_expression(expression):
    it = peekable(expression)
    try:
        expression = parse_subexpression(it)
    except StopIteration:
        raise Assert(False, 'incomplete filter expression')
    Assert(not it, 'Unparsed garbage after expression')
    return expression
