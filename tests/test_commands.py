import unittest

from mopidy_mpd import exceptions, protocol
from mopidy_mpd.dispatcher import MpdContext


class TestConverts(unittest.TestCase):
    def test_integer(self):
        assert protocol.INT("123") == 123
        assert protocol.INT("-123") == (-123)
        assert protocol.INT("+123") == 123
        self.assertRaises(ValueError, protocol.INT, "3.14")
        self.assertRaises(ValueError, protocol.INT, "")
        self.assertRaises(ValueError, protocol.INT, "abc")
        self.assertRaises(ValueError, protocol.INT, "12 34")

    def test_unsigned_integer(self):
        assert protocol.UINT("123") == 123
        self.assertRaises(ValueError, protocol.UINT, "-123")
        self.assertRaises(ValueError, protocol.UINT, "+123")
        self.assertRaises(ValueError, protocol.UINT, "3.14")
        self.assertRaises(ValueError, protocol.UINT, "")
        self.assertRaises(ValueError, protocol.UINT, "abc")
        self.assertRaises(ValueError, protocol.UINT, "12 34")

    def test_boolean(self):
        assert protocol.BOOL("1") is True
        assert protocol.BOOL("0") is False
        self.assertRaises(ValueError, protocol.BOOL, "3.14")
        self.assertRaises(ValueError, protocol.BOOL, "")
        self.assertRaises(ValueError, protocol.BOOL, "true")
        self.assertRaises(ValueError, protocol.BOOL, "false")
        self.assertRaises(ValueError, protocol.BOOL, "abc")
        self.assertRaises(ValueError, protocol.BOOL, "12 34")

    def test_range(self):
        assert slice(1, 2) == protocol.RANGE("1")
        assert slice(0, 1) == protocol.RANGE("0")
        assert slice(0, None) == protocol.RANGE("0:")
        assert slice(1, 3) == protocol.RANGE("1:3")
        self.assertRaises(ValueError, protocol.RANGE, "3.14")
        self.assertRaises(ValueError, protocol.RANGE, "1:abc")
        self.assertRaises(ValueError, protocol.RANGE, "abc:1")
        self.assertRaises(ValueError, protocol.RANGE, "2:1")
        self.assertRaises(ValueError, protocol.RANGE, "-1:2")
        self.assertRaises(ValueError, protocol.RANGE, "1 : 2")
        self.assertRaises(ValueError, protocol.RANGE, "")
        self.assertRaises(ValueError, protocol.RANGE, "true")
        self.assertRaises(ValueError, protocol.RANGE, "false")
        self.assertRaises(ValueError, protocol.RANGE, "abc")
        self.assertRaises(ValueError, protocol.RANGE, "12 34")


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.commands = protocol.Commands()

    def test_add_as_a_decorator(self):
        @self.commands.add("test")
        def test(context: MpdContext):
            pass

    def test_register_second_command_to_same_name_fails(self):
        def func(context: MpdContext):
            pass

        self.commands.add("foo")(func)
        with self.assertRaises(ValueError):
            self.commands.add("foo")(func)

    def test_function_only_takes_context_succeeds(self):
        sentinel = object()
        self.commands.add("bar")(lambda context: sentinel)
        assert sentinel == self.commands.call(context=None, tokens=["bar"])

    def test_function_has_required_arg_succeeds(self):
        sentinel = object()
        self.commands.add("bar")(lambda context, required: sentinel)
        assert sentinel == self.commands.call(context=None, tokens=["bar", "arg"])

    def test_function_has_optional_args_succeeds(self):
        sentinel = object()
        self.commands.add("bar")(lambda context, optional=None: sentinel)
        assert sentinel == self.commands.call(context=None, tokens=["bar"])
        assert sentinel == self.commands.call(context=None, tokens=["bar", "arg"])

    def test_function_has_required_and_optional_args_succeeds(self):
        sentinel = object()

        def func(context: MpdContext, required, optional=None):
            return sentinel

        self.commands.add("bar")(func)
        assert sentinel == self.commands.call(context=None, tokens=["bar", "arg"])
        assert sentinel == self.commands.call(
            context=None, tokens=["bar", "arg", "arg"]
        )

    def test_function_has_varargs_succeeds(self):
        sentinel, args = object(), []
        self.commands.add("bar")(lambda context, *args: sentinel)
        for _ in range(10):
            assert sentinel == self.commands.call(context=None, tokens=["bar", *args])
            args.append("test")

    def test_function_has_only_varags_succeeds(self):
        sentinel = object()
        self.commands.add("baz")(lambda *args: sentinel)
        assert sentinel == self.commands.call(context=None, tokens=["baz"])

    def test_function_has_no_arguments_fails(self):
        with self.assertRaises(TypeError):
            self.commands.add("test")(lambda: True)

    def test_function_has_required_and_varargs_fails(self):
        with self.assertRaises(TypeError):

            def func(context: MpdContext, required, *args):
                pass

            self.commands.add("test")(func)

    def test_function_has_optional_and_varargs_fails(self):
        with self.assertRaises(TypeError):

            def func(context: MpdContext, optional=None, *args):
                pass

            self.commands.add("test")(func)

    def test_function_hash_keywordargs_fails(self):
        with self.assertRaises(TypeError):
            self.commands.add("test")(lambda context, **kwargs: True)

    def test_call_chooses_correct_handler(self):
        sentinel1, sentinel2, sentinel3 = object(), object(), object()
        self.commands.add("foo")(lambda context: sentinel1)
        self.commands.add("bar")(lambda context: sentinel2)
        self.commands.add("baz")(lambda context: sentinel3)

        assert sentinel1 == self.commands.call(context=None, tokens=["foo"])
        assert sentinel2 == self.commands.call(context=None, tokens=["bar"])
        assert sentinel3 == self.commands.call(context=None, tokens=["baz"])

    def test_call_with_nonexistent_handler(self):
        with self.assertRaises(exceptions.MpdUnknownCommandError):
            self.commands.call(context=None, tokens=["bar"])

    def test_call_passes_context(self):
        sentinel = object()
        self.commands.add("foo")(lambda context: context)
        assert sentinel == self.commands.call(context=sentinel, tokens=["foo"])

    def test_call_without_args_fails(self):
        with self.assertRaises(exceptions.MpdNoCommandError):
            self.commands.call(context=None, tokens=[])

    def test_call_passes_required_argument(self):
        self.commands.add("foo")(lambda context, required: required)
        assert self.commands.call(context=None, tokens=["foo", "test123"]) == "test123"

    def test_call_passes_optional_argument(self):
        sentinel = object()
        self.commands.add("foo")(lambda context, optional=sentinel: optional)
        assert sentinel == self.commands.call(context=None, tokens=["foo"])
        assert self.commands.call(context=None, tokens=["foo", "test"]) == "test"

    def test_call_passes_required_and_optional_argument(self):
        def func(context: MpdContext, required, optional=None):
            return (required, optional)

        self.commands.add("foo")(func)
        assert self.commands.call(context=None, tokens=["foo", "arg"]) == ("arg", None)
        assert self.commands.call(context=None, tokens=["foo", "arg", "kwarg"]) == (
            "arg",
            "kwarg",
        )

    def test_call_passes_varargs(self):
        self.commands.add("foo")(lambda context, *args: args)

    def test_call_incorrect_args(self):
        self.commands.add("foo")(lambda context: context)
        with self.assertRaises(exceptions.MpdArgError):
            self.commands.call(context=None, tokens=["foo", "bar"])

        self.commands.add("bar")(lambda context, required: context)
        with self.assertRaises(exceptions.MpdArgError):
            self.commands.call(context=None, tokens=["bar", "bar", "baz"])

        self.commands.add("baz")(lambda context, optional=None: context)
        with self.assertRaises(exceptions.MpdArgError):
            self.commands.call(context=None, tokens=["baz", "bar", "baz"])

    def test_validator_gets_applied_to_required_arg(self):
        sentinel = object()

        def func(context: MpdContext, required):
            return required

        self.commands.add("test", required=lambda v: sentinel)(func)
        assert sentinel == self.commands.call(context=None, tokens=["test", "foo"])

    def test_validator_gets_applied_to_optional_arg(self):
        sentinel = object()

        def func(context: MpdContext, optional=None):
            return optional

        self.commands.add("foo", optional=lambda v: sentinel)(func)

        assert sentinel == self.commands.call(context=None, tokens=["foo", "123"])

    def test_validator_skips_optional_default(self):
        sentinel = object()

        def func(context: MpdContext, optional=sentinel):
            return optional

        self.commands.add("foo", optional=lambda v: None)(func)

        assert sentinel == self.commands.call(context=None, tokens=["foo"])

    def test_validator_applied_to_non_existent_arg_fails(self):
        self.commands.add("foo")(lambda context, arg: arg)
        with self.assertRaises(TypeError):

            def func(context: MpdContext, wrong_arg):
                return wrong_arg

            self.commands.add("bar", arg=lambda v: v)(func)

    def test_validator_called_context_fails(self):
        return  # TODO: how to handle this
        with self.assertRaises(TypeError):

            def func(context: MpdContext):
                pass

            self.commands.add("bar", context=lambda v: v)(func)

    def test_validator_value_error_is_converted(self):
        def validdate(value):
            raise ValueError

        def func(context: MpdContext, arg):
            pass

        self.commands.add("bar", arg=validdate)(func)

        with self.assertRaises(exceptions.MpdArgError):
            self.commands.call(context=None, tokens=["bar", "test"])

    def test_auth_required_gets_stored(self):
        def func1(context: MpdContext):
            pass

        def func2(context: MpdContext):
            pass

        self.commands.add("foo")(func1)
        self.commands.add("bar", auth_required=False)(func2)

        assert self.commands.handlers["foo"].auth_required
        assert not self.commands.handlers["bar"].auth_required

    def test_list_command_gets_stored(self):
        def func1(context: MpdContext):
            pass

        def func2(context: MpdContext):
            pass

        self.commands.add("foo")(func1)
        self.commands.add("bar", list_command=False)(func2)

        assert self.commands.handlers["foo"].list_command
        assert not self.commands.handlers["bar"].list_command
