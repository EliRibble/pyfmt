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
    if len(value) > context.remaining_line_length:
        raise StrategyFailureError("Value length is {} which is longer than context max line length of {}".format(len(value), context.remaining_line_length))
    result = value.replace("\t", r"\t").replace("\n", r"\n")
    return "{quote}{result}{quote}".format(
        quote=context.quote,
        result=result,
    )

def _make_string_line(line: typing.Iterable[typing.Text], context:types.Context) -> typing.Text:
    return "{tabs}{quote}{content}{quote}".format(
        content="".join(line),
        quote=context.quote,
        tabs=(context.indent + 1) * context.tab,
    )

def _format_spaces(value: typing.Text, context: types.Context):
    "The string is long, try to break it on spaces. And newlines."
    # Break up the content on spaces but retain the
    # spaces so we can also break on newlines
    words = value.split(" ")
    for i in range(len(words) - 1):
        words[i] = words[i] + " "
    # For each word see if we can make a line. Once it's
    # too long we step back and add the line to our results.
    results = []
    line = []
    while words:
        word = words.pop(0)
        # If the line has a newline then gather all the newlines
        # together into a single line and break there.
        newlines_start = word.find("\n")
        newlines_end = newlines_start
        if newlines_start > -1:
            while newlines_end < len(word) and word[newlines_end] == "\n" :
                newlines_end += 1
            # Whatever is left that is not a newline needs to
            # be added back to our stack for processing.
            remainder = word[newlines_end:]
            words.insert(0, remainder)
            word = word[:newlines_end]
            word = word.replace("\n", r"\n")
            results.append(_make_string_line(line + [word], context.override(indent=0)))
            line = []
            continue
        possible_line = line + [word]
        test_line = _make_string_line(possible_line, context)
        if len(test_line) < context.max_line_length:
            line = possible_line
            continue
        results.append(_make_string_line(line, context.override(indent=0)))
        line = []
        words.insert(0, word)
    if line:
        results.append(_make_string_line(line, context.override(indent=0)))
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
