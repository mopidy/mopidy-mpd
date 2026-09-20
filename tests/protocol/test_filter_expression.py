import unittest

from mopidy.models import Album, Artist, Track
from mopidy.query import And, Compare, Not, field_values, matches

from mopidy_mpd.protocol import music_db
from mopidy_mpd.protocol.filter_expression import (
    FilterExpressionError,
    parse,
)
from mopidy_mpd.protocol.music_db import parse_query

_MAPPING = music_db._SEARCH_MAPPING


class ParseTest(unittest.TestCase):
    def test_example_query(self):
        text = (
            '((album == "Exciter") AND (albumartist == "Depeche Mode") '
            'AND (date == "2001"))'
        )
        expr = parse(text, _MAPPING)
        assert expr == And(
            (
                Compare("album", "eq", "Exciter"),
                Compare("albumartist", "eq", "Depeche Mode"),
                Compare("date", "eq", "2001"),
            )
        )

    def test_single_comparison(self):
        expr = parse('(artist == "ABBA")', _MAPPING)
        assert expr == Compare("artist", "eq", "ABBA")

    def test_tag_names_are_case_insensitive(self):
        expr = parse('(ARTIST == "ABBA")', _MAPPING)
        assert expr == Compare("artist", "eq", "ABBA")

    def test_all_operators(self):
        expected = {
            "==": "eq",
            "!=": "ne",
            "contains": "contains",
            "starts_with": "starts_with",
        }
        for mpd_op, core_op in expected.items():
            expr = parse(f'(artist {mpd_op} "ABBA")', _MAPPING)
            assert expr == Compare("artist", core_op, "ABBA")

    def test_any_contains(self):
        expr = parse('(any contains "zz")', _MAPPING)
        assert expr == Compare("any", "contains", "zz")

    def test_negation(self):
        expr = parse('(!(artist == "ABBA"))', _MAPPING)
        assert expr == Not(Compare("artist", "eq", "ABBA"))

    def test_double_wrapped_single_clause_is_unwrapped(self):
        expr = parse('((artist == "ABBA"))', _MAPPING)
        assert expr == Compare("artist", "eq", "ABBA")

    def test_nested_and_chains(self):
        expr = parse(
            '(((artist == "A") AND (album == "B")) AND (date == "C"))',
            _MAPPING,
        )
        assert expr == And(
            (
                And((Compare("artist", "eq", "A"), Compare("album", "eq", "B"))),
                Compare("date", "eq", "C"),
            )
        )

    def test_escaped_quote_in_value(self):
        expr = parse(r'(artist == "Foo \"Bar\" Baz")', _MAPPING)
        assert expr == Compare("artist", "eq", 'Foo "Bar" Baz')

    def test_single_quoted_string(self):
        expr = parse("(artist == 'ABBA')", _MAPPING)
        assert expr == Compare("artist", "eq", "ABBA")

    def test_double_quotes_inside_single_quoted_string_need_no_escaping(self):
        expr = parse("""(artist == 'Foo "Bar" Baz')""", _MAPPING)
        assert expr == Compare("artist", "eq", 'Foo "Bar" Baz')

    def test_single_quotes_inside_double_quoted_string_need_no_escaping(self):
        expr = parse('''(artist == "Foo 'Bar' Baz")''', _MAPPING)
        assert expr == Compare("artist", "eq", "Foo 'Bar' Baz")

    def test_escaped_single_quote_in_single_quoted_value(self):
        expr = parse(r"(artist == 'Foo \'Bar\' Baz')", _MAPPING)
        assert expr == Compare("artist", "eq", "Foo 'Bar' Baz")

    def test_mixed_quote_styles_in_and_chain(self):
        expr = parse(
            """((album == 'Exciter') AND (artist == "Depeche Mode"))""",
            _MAPPING,
        )
        assert expr == And(
            (
                Compare("album", "eq", "Exciter"),
                Compare("artist", "eq", "Depeche Mode"),
            )
        )

    def test_unterminated_single_quoted_string_raises(self):
        with self.assertRaises(FilterExpressionError):
            parse("(artist == 'ABBA)", _MAPPING)

    def test_unknown_tag_raises(self):
        with self.assertRaises(FilterExpressionError):
            parse('(notatag == "x")', _MAPPING)

    def test_unbalanced_parens_raises(self):
        with self.assertRaises(FilterExpressionError):
            parse('(artist == "ABBA"', _MAPPING)

    def test_unterminated_string_raises(self):
        with self.assertRaises(FilterExpressionError):
            parse('(artist == "ABBA)', _MAPPING)

    def test_trailing_garbage_raises(self):
        with self.assertRaises(FilterExpressionError):
            parse('(artist == "ABBA") garbage', _MAPPING)

    def test_and_operands_must_each_be_parenthesized(self):
        with self.assertRaises(FilterExpressionError):
            parse('(artist == "A" AND album == "B")', _MAPPING)

    def test_unknown_operator_raises(self):
        with self.assertRaises(FilterExpressionError):
            parse('(artist ~= "ABBA")', _MAPPING)


class ParseQueryTest(unittest.TestCase):
    def test_legacy_syntax_is_compiled_to_an_expression(self):
        expr = parse_query(["artist", "ABBA"], _MAPPING)
        assert expr == Compare("artist", "contains", "ABBA")

    def test_legacy_exact_syntax_is_compiled_to_an_equals_expression(self):
        expr = parse_query(["artist", "ABBA"], _MAPPING, exact=True)
        assert expr == Compare("artist", "eq", "ABBA")

    def test_expression_syntax_is_parsed(self):
        expr = parse_query(['(artist == "ABBA")'], _MAPPING)
        assert expr == Compare("artist", "eq", "ABBA")
        track = Track(uri="dummy:a", artists=frozenset([Artist(name="ABBA")]))
        other = Track(uri="dummy:b", artists=frozenset([Artist(name="Other")]))
        assert matches(expr, track)
        assert not matches(expr, other)

    def test_mpc_legacy_tag_before_expression_is_ignored(self):
        expr = parse_query(['track', '(album contains "a")'], _MAPPING)

        assert expr == Compare("album", "contains", "a")


class MatchesThroughCoreTest(unittest.TestCase):
    def _track(self, **kwargs):
        kwargs.setdefault("uri", "dummy:track")
        return Track(**kwargs)

    def test_parsed_equals_is_case_sensitive(self):
        track = self._track(name="Exciter")
        expr = parse('(title == "Exciter")', _MAPPING)
        assert matches(expr, track)
        expr = parse('(title == "exciter")', _MAPPING)
        assert not matches(expr, track)

    def test_example_query_end_to_end(self):
        track = Track(
            uri="dummy:a",
            name="Reach Out (Papa Reach)",
            album=Album(
                name="Exciter",
                artists=frozenset([Artist(name="Depeche Mode")]),
                date="2001",
            ),
            date="2001",
        )
        expr = parse(
            '((album == "Exciter") AND (albumartist == "Depeche Mode") '
            'AND (date == "2001"))',
            _MAPPING,
        )
        assert matches(expr, track)

        other = Track(
            uri="dummy:b",
            name="Other",
            album=Album(name="Other Album", artists=frozenset()),
            date="1999",
        )
        assert not matches(expr, other)

    def test_field_values_any_is_union_of_all_fields(self):
        track = self._track(name="Exciter", genre="Rock")
        values = field_values(track, "any")
        assert "Exciter" in values
        assert "Rock" in values
