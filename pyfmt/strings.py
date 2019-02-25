"""Module for dealing with formatting strings."""
import ast

def format_string(value: ast.Str, context):
    REPLACEMENTS = {
        context.quote: "\\" + context.quote,
        "\n": "\\n",
        "\t": "\\t",
    }
    return "{quote}{string}{quote}".format(
        quote=context.quote,
        string=REPLACEMENTS.get(value.s, value.s),
    )

