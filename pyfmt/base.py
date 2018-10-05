import ast

class Context():
    """Represents the context of the operation being serialized.

    This class is used heavily in making decisions about the application
    of whitespace.
    """
    def __init__(self, indent=0, max_line_length=120, quote="'", tab='\t'):
        self.indent = indent
        self.max_line_length = max_line_length
        self.quote = quote
        self.tab = tab

    def sub(self):
        return Context(
            indent=self.indent+1,
            max_line_length=self.max_line_length,
            quote=self.quote,
            tab=self.tab,
        )

def _format_arguments(value, context):
    """Format an argument like 'x, y = z'"""
    parts = []
    for arg in value.args:
        parts.append(_format_value(arg, context))
    for kwarg in value.kwonlyargs:
        parts.append(_format_value(kwarg, context, pad_key=max_kwarg_key_len))
    possible = ", ".join(parts)
    return possible

def _format_assign(value, context):
    targets = _format_targets(value.targets)
    value = _format_value(value.value, context)
    return "{targets} = {value}".format(
        targets=targets,
        value=value,
    )

def _format_attribute(value, context):
    return "{value}.{attr}".format(
        value = _format_value(value.value, context),
        attr = _format_value(value.attr, context),
    )

def _format_binop(value, context):
    return "{left} {op} {right}".format(
        left  = _format_value(value.left, context),
        op    = _format_value(value.op, context),
        right = _format_value(value.right, context),
    )

def _format_body(body, context):
    lines = [_format_value(line, context) for line in body]
    tabbed_lines = [(context.tab * context.indent) + line for line in lines]
    return "\n".join(tabbed_lines)

def _format_call(value, context):
    """Format a function call like 'print(a*b, foo=x)'"""
    result = _format_call_horizontal(value, context)
    if len(result) < context.max_line_length:
        return result
    return _format_call_vertical(value, context)

def _format_call_horizontal(value, context):
    """Format a call like 'print(a*b)' with the arguments in a line."""
    arguments = [
        _format_value(arg, context) for arg in value.args
    ] + [
        _format_value(kwarg, context) for kwarg in value.keywords
    ]
    return "{func}({arguments})".format(
        arguments=", ".join(arguments),
        func=_format_value(value.func, context),
    )

def _format_call_vertical(value, context):
    """Format a call like 'print(a*b, x=z)' with arguments vertically lined up."""
    args = [
        _format_value(arg, context) for arg in value.args
    ]
    max_kwarg_key_len = max(len(k.arg) for k in value.keywords) if value.keywords else 0
    kwargs = [
        _format_keyword(k, context, pad_key=max_kwarg_key_len) for k in value.keywords
    ]
    if args:
        return "{func}({arguments})".format(
            arguments=",\n\t".join(args + kwargs),
            func=_format_value(value.func, context)
        )
    return "{func}(\n\t{kwargs})".format(
        kwargs=",\n\t".join(kwargs),
        func=_format_value(value.func, context))

def _format_comprehension(value, context):
    return "for {target} in {iter}".format(
        target=_format_value(value.target, context),
        iter=_format_value(value.iter, context),
    )

def _format_expression(value, context):
    return _format_value(value.value, context)

def _format_function_def(func, context):
    arguments = _format_value(func.args, context)
    body = _format_body(func.body, context=context.sub())
    return "def {name}({arguments}):\n{body}".format(
        name=func.name,
        arguments=arguments,
        body=body,
    )

def _format_import(imp, context):
    return "import {}".format(
        ', '.join(sorted(n.name for n in imp.names)))

def _format_import_from(imp, context):
    return "from {} import {}".format(
        imp.module,
        ', '.join(sorted(n.name for n in imp.names)))

def _format_list_comprehension(comp, context):
    assert len(comp.generators) == 1
    return "[{elt} {generators}]".format(
        elt = _format_value(comp.elt, context),
        generators = _format_value(comp.generators[0], context),
    )

def _format_keyword(value, context, pad_key=None):
    pad_key = pad_key or len(value.arg)
    pattern = "{{arg: <{}}} = {{value}}".format(pad_key)
    return pattern.format(
        arg = value.arg,
        value = _format_value(value.value, context),
    )

def _format_multiplication(value, context):
    return "*"

def _format_name(value, context):
    return str(value.id)

def _format_number(value, context):
    return str(value.n)

def _format_return(value, context):
    return "return {}".format(_format_value(value.value, context))

def _format_string(value, context):
    return "{quote}{string}{quote}".format(
        quote=context.quote,
        string=value.s)

def _format_targets(targets):
    result = []
    for target in targets:
        if type(target) == ast.Name:
            result.append(target.id)
        elif type(target) == ast.Tuple:
            for elt in target.elts:
                result.append(elt.id)
    return ", ".join(result)

def _format_tuple(value, context):
    return ", ".join([_format_value(elt, context) for elt in value.elts])

def _format_value(value, context):
    formatter = FORMATTERS.get(type(value))
    if formatter is None:
        raise Exception("Need to write a formatter for {}".format(type(value)))
    return formatter(value, context)

FORMATTERS = {
    ast.Add: lambda x, y: "+",
    ast.arg: lambda x, y: x.arg,
    ast.arguments: _format_arguments,
    ast.Assign: _format_assign,
    ast.Attribute: _format_attribute,
    ast.BinOp: _format_binop,
    ast.Call: _format_call,
    ast.comprehension: _format_comprehension,
    ast.Expr: _format_expression,
    ast.FunctionDef: _format_function_def,
    ast.Import: _format_import,
    ast.ImportFrom: _format_import_from,
    ast.ListComp: _format_list_comprehension,
    ast.keyword: _format_keyword,
    ast.Mult: _format_multiplication,
    ast.Name: _format_name,
    ast.Num: _format_number,
    ast.Pow: lambda x, yz: "**",
    ast.Return: _format_return,
    str: lambda x, y: x,
    ast.Str: _format_string,
    ast.Tuple: _format_tuple,
}

def serialize(content, max_line_length=120, quote="\"", tab="\t"):
    data = ast.parse(content)
    context = Context(
        indent=0,
        max_line_length=max_line_length,
        quote=quote,
        tab=tab)
    return "\n".join([
        FORMATTERS[type(part)](part, context) for part in data.body]) + "\n"
