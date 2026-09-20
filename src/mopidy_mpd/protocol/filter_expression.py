"""Parse MPD's parenthesized filter expressions into Mopidy search trees.

Grammar (documented here since MPD itself has no formal spec for it)::

    top_expr   := "(" content ")"
    content    := comparison | negation | and_chain
    negation   := "!" top_expr
    and_chain  := top_expr ( "AND" top_expr )+
    comparison := TAG OP STRING
    OP         := "==" | "!=" | "contains" | "starts_with"
    TAG        := bare identifier, looked up case-insensitively in the
                  caller's field mapping (e.g. music_db._SEARCH_MAPPING)
    STRING     := double- or single-quoted, backslash-escaped string literal

Every ``AND`` operand must be parenthesized. ``OR``, bare tag-existence checks,
and MPD's special filters are not supported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mopidy.query import And, Compare, CompareOp, Not, SearchExpr

from mopidy_mpd.tokenize import UNESCAPE_RE


class FilterExpressionError(Exception):
    """Raised when a filter expression string cannot be parsed.

    Deliberately not a ``ValueError`` subclass: callers already use bare
    ``ValueError`` to signal an unrelated legacy-syntax quirk (a dangling tag
    with no value), and that must not be conflated with a malformed
    expression.
    """


_MPD_OPS: dict[str, CompareOp] = {
    "==": "eq",
    "!=": "ne",
    "contains": "contains",
    "starts_with": "starts_with",
}


@dataclass(frozen=True)
class _Token:
    kind: str
    text: str
    pos: int


_TOKEN_RE = re.compile(
    r"""
      (?P<lparen>\()
    | (?P<rparen>\))
    | (?P<ne_op>!=)
    | (?P<not>!)
    | (?P<eq_op>==)
    | "(?P<string_dq>(?:[^"\\]|\\.)*)"
    | '(?P<string_sq>(?:[^'\\]|\\.)*)'
    | (?P<ident>[A-Za-z][A-Za-z0-9_]*)
    """,
    re.VERBOSE,
)

_TOKEN_KINDS = {
    "lparen": "LPAREN",
    "rparen": "RPAREN",
    "eq_op": "OP",
    "ne_op": "OP",
    "not": "NOT",
    "string_dq": "STRING",
    "string_sq": "STRING",
}


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    pos = 0
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        match = _TOKEN_RE.match(text, pos)
        if not match:
            if text[pos] in "\"'":
                raise FilterExpressionError(
                    f"unterminated string starting at position {pos}"
                )
            raise FilterExpressionError(
                f"unexpected character at position {pos}: {text[pos : pos + 20]!r}"
            )
        assert (name := match.lastgroup) is not None
        value = match.group(name)
        start = match.start(name)
        if name == "ident":
            lowered = value.lower()
            if lowered == "and":
                kind = "AND"
            elif lowered in _MPD_OPS:
                kind, value = "OP", lowered
            else:
                kind = "TAG"
        else:
            kind = _TOKEN_KINDS[name]
            if kind == "STRING":
                value = UNESCAPE_RE.sub(r"\g<1>", value)
        tokens.append(_Token(kind, value, start))
        pos = match.end()
    return tokens


class _Parser:
    def __init__(self, tokens: list[_Token], field_mapping: dict[str, str]) -> None:
        self._tokens = tokens
        self._pos = 0
        self._field_mapping = field_mapping

    def parse(self) -> SearchExpr:
        expr = self._parse_top_expr()
        token = self._peek()
        if token is not None:
            raise FilterExpressionError(
                f"unexpected trailing input at position {token.pos}: {token.text!r}"
            )
        return expr

    def _peek(self) -> _Token | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _advance(self) -> _Token:
        token = self._peek()
        if token is None:
            raise FilterExpressionError("unexpected end of expression")
        self._pos += 1
        return token

    def _expect(self, kind: str) -> _Token:
        token = self._peek()
        if token is None or token.kind != kind:
            got = f"{token.kind} {token.text!r}" if token else "end of expression"
            raise FilterExpressionError(f"expected {kind}, got {got}")
        return self._advance()

    def _parse_top_expr(self) -> SearchExpr:
        self._expect("LPAREN")
        expr = self._parse_content()
        self._expect("RPAREN")
        return expr

    def _parse_content(self) -> SearchExpr:
        token = self._peek()
        if token is None:
            raise FilterExpressionError("unexpected end of expression")
        if token.kind == "NOT":
            self._advance()
            return Not(self._parse_top_expr())
        if token.kind == "TAG":
            return self._parse_comparison()
        if token.kind == "LPAREN":
            return self._parse_and_chain()
        raise FilterExpressionError(
            f"unexpected token at position {token.pos}: {token.text!r}"
        )

    def _parse_and_chain(self) -> SearchExpr:
        conjuncts = [self._parse_top_expr()]
        while (peeked := self._peek()) is not None and peeked.kind == "AND":
            self._advance()
            conjuncts.append(self._parse_top_expr())
        return And(tuple(conjuncts)) if len(conjuncts) > 1 else conjuncts[0]

    def _parse_comparison(self) -> Compare:
        tag_token = self._expect("TAG")
        field = self._field_mapping.get(tag_token.text.lower())
        if field is None:
            raise FilterExpressionError(f"unknown tag {tag_token.text!r}")
        op = _MPD_OPS[self._expect("OP").text]
        value_token = self._expect("STRING")
        return Compare(field=field, op=op, value=value_token.text)


def parse(text: str, field_mapping: dict[str, str]) -> SearchExpr:
    """Parses a filter expression string into a [mopidy.query.SearchExpr][].

    ``field_mapping`` normalizes tag names the same way the legacy tag/value
    parser does (e.g. ``music_db._SEARCH_MAPPING``), so unknown/aliased tags
    are rejected/resolved identically to the legacy syntax.
    """
    return _Parser(_tokenize(text), field_mapping).parse()
