"""Module for dealing with formatting strings."""
import ast
import typing

from pyfmt import types

class StrategyFailureError(Exception):
    "Indicates the strategy can't be applied."

def format_string(value: ast.Str, context: types.Context) -> typing.Text:
    result = value.s.replace(context.quote, "\\" + context.quote)
    result = _apply_strategies(result, context)
        
    return result 
 
def _apply_strategies(value: typing.Text, context: types.Context):
    for strategy in STRATEGIES:
        try:
            return strategy(value, context)
        except StrategyFailureError:
            continue
    raise ValueError("Can't handle value:\n{}".format(value))

def _format_direct(value: typing.Text, context: types.Context):
    "The string is short and has no newlines in it."
    if len(value) > context.max_line_length:
        raise StrategyFailureError("Value length is {} which is longer than context max line length of {}".format(len(value), context.max_line_length))
    result = value.replace("\t", r"\t").replace("\n", r"\n")
    return "{quote}{result}{quote}".format(
        quote=context.quote,
        result=result,
    )

def _make_string_line(line: typing.Iterable[typing.Text], context:types.Context) -> typing.Text:
    return "{tabs}{quote}{content}{quote}".format(
        content=" ".join(line),
        quote=context.quote,
        tabs=(context.indent + 1) * context.tab,
    )

def _format_spaces(value: typing.Text, context: types.Context):
    "The string is long, try to break it on spaces."
    value = value.replace("\n", r"\n ")
    words = value.split(" ")
    results = []
    line = []
    while words:
        word = words.pop(0)
        possible_line = line + [word]
        test_line = _make_string_line(possible_line, context)
        if len(test_line) < context.max_line_length:
            line = possible_line
        else:
            results.append(_make_string_line(line, context.override(indent=0)))
            words.insert(0, word)
            line = []
    if line:
        results.append(_make_string_line(line, context.override(indent=0)))
    results = [r.replace(r"\n ", r"\n") for r in results]
    content = "\n".join(results)
    return "(\n" + content + "\n)"
    return "{quote}{result}{quote}".format(
        quote=context.quote,
        result=result,
    )

# The strategies we prefer, in order, for breaking up a
# large string.
STRATEGIES = (
    _format_direct,
    _format_spaces,
    #_format_hardbreak,
)
