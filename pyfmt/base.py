import ast

from pyfmt import constants

class Context():
    """Represents the context of the operation being serialized.

    This class is used heavily in making decisions about the application
    of whitespace.
    """
    def __init__(self, indent=0, inline=False, max_line_length=120, quote="'", tab='\t'):
        self.indent = indent
        self.inline = inline
        self.max_line_length = max_line_length
        self.quote = quote
        self.tab = tab

    def override(self, **kwargs):
        """Create a new context with the provided overrides.

        For example, if you have a context A and want to produce a context
        B that is identical to A but has a different quote delimitre you would
        use A.override(quote="foo")
        """
        VALID_PARAMS = ("indent", "inline", "max_line_length", "quote", "tab")
        assert all(k in VALID_PARAMS for k in kwargs.keys())
        params = {k: kwargs.get(k, getattr(self, k)) for k in VALID_PARAMS}
        return Context(**params)

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
    """Format a body like a function or module body.

    This breaks the body into large sections for the sake
    of sorting certain orderable statements within those
    sections, like imports.
    """
    doc, remainder = _split_docstring(body)
    stdimports, imports, remainder = _split_imports(remainder)
    constants, remainder = _split_constants(remainder)
    constants = _format_constants(constants, context)
    docstring = _format_docstring(doc, context)
    stdimports = _format_imports(stdimports, context)
    imports = _format_imports(imports, context)

    content = _joiner(remainder, context)

    stdimports = stdimports + "\n\n" if stdimports else ""
    imports = imports + "\n\n" if imports else ""
    docstring = docstring + "\n" if docstring else ""
    constants = constants + "\n\n" if constants else ""
    return (docstring + stdimports + imports + constants + content).rstrip()

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
        _format_value(kwarg, context.override(inline=True)) for kwarg in value.keywords
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

def _format_compare(value, context):
    return "{left} {op} {right}".format(
        left=_format_value(value.left, context),
        op=_format_value(value.ops[0], context),
        right=_format_value(value.comparators[0], context),
    )

def _format_comprehension(value, context):
    return "for {target} in {iter}".format(
        target=_format_value(value.target, context),
        iter=_format_value(value.iter, context),
    )

def _format_constants(constants, context):
    lines = [(context.indent * context.tab) + _format_value(c, context) for c in constants]
    return "\n".join(sorted(lines))

def _format_dict(value, context):
    "Format a dictionary, choosing the best approach of several"
    data = {
        _format_value(k, context):
        _format_value(v, context) for k, v in zip(value.keys, value.values)}
    ordering = sorted(data.keys())
    pairs = [
        (k, data[k]) for k in ordering]
    short = _format_dict_short(pairs, context)
    if len(short) <= context.max_line_length:
        return short
    medium = _format_dict_medium(pairs, context)
    return medium

def _format_dict_medium(pairs, context):
    "Format a dictionary as if were medium length, one key/value pair per line"
    parts = ["{}: {},".format(k, v) for k, v in pairs]
    return "{{\n\t{}\n}}".format("\n\t".join(parts))

def _format_dict_short(pairs, context):
    "Format a dictionary as if it were quite short"
    parts = ["{}: {}".format(k, v) for k, v in pairs]
    return "{{{}}}".format(", ".join(parts))

def _format_docstring(value, context):
    """Given a single expression known to be a docstring apply special formatting.

    Returns:
        A list of lines
    """
    # A docstring will be a single really long string expression, often with
    # embedded tabs for formatting. We need to rip those out to apply our own
    # formatting.
    if not value:
        return []
    content = _format_expression(value, context)
    if "\n" in content:
        context = context.override(quote="\"\"\"")
        content = _format_expression(value, context)
    lines = content.split('\n')
    docstring = [
        (context.indent * context.tab) + line.strip() if line else "" for line in lines]
    return "\n".join(docstring)

def _format_eq(value, context):
    return "=="

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

def _format_if(value, context):
    test = _format_value(value.test, context)
    body = _format_body(value.body, context.sub())
    return "if {}:\n{}".format(test, body)

def _format_import(imp, context):
    return "import {}".format(
        ', '.join(sorted(n.name for n in imp.names)))

def _format_import_from(imp, context):
    return "from {} import {}".format(
        imp.module,
        ', '.join(sorted(n.name for n in imp.names)))

def _format_imports(imports, context):
    lines = [_format_value(i, context) for i in imports]
    return "\n".join(sorted(lines))

def _format_list(value, context):
    return "list"

def _format_list_comprehension(comp, context):
    assert len(comp.generators) == 1
    return "[{elt} {generators}]".format(
        elt = _format_value(comp.elt, context),
        generators = _format_value(comp.generators[0], context),
    )

def _format_keyword(value, context, pad_key=None):
    pad_key = pad_key or len(value.arg)
    pattern = "{{arg: <{}}}{{equals}}{{value}}".format(pad_key)
    return pattern.format(
        arg = value.arg,
        equals = "=" if context.inline else " = ",
        value = _format_value(value.value, context),
    )

def _format_multiplication(value, context):
    return "*"

def _format_name(value, context):
    return str(value.id)

def _format_name_constant(value, context):
    return str(value.value)

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

def _joiner(section, context):
    """Join a section into well-formatte lines.

    Take a section, which is a list of AST items to put together in a block which
    is one giant, properly formatted strings.
    """
    if not section:
        return ""
    JOINERS = {
        ast.FunctionDef: "\n\n",
    }
    lines = []
    result = ""
    joiner = ""
    for node in section:
        # only add the joiner if this is not the last iteration
        result += joiner
        joiner = JOINERS.get(type(node), "\n")
        content = _format_value(node, context)
        result = result + (context.tab * context.indent) + content
    return result

def _split_constants(remainder):
    "Given the remainder of a body return the constants and whatever else is left."
    constants = []
    while remainder and isinstance(remainder[0], ast.Assign):
        node = remainder[0]
        if len(node.targets) > 1:
            break;
        if not isinstance(node.targets[0], ast.Name):
            break;
        if type(node.value) not in (ast.NameConstant, ast.Str,):
            break;
        constants.append(remainder[0])
        remainder = remainder[1:]
    return constants, remainder

def _split_docstring(remainder):
    """Given the non-import sections of a body, return the docstring and remainder."""
    if not (remainder and isinstance(remainder[0], ast.Expr) and isinstance(remainder[0].value, ast.Str)):
        return [], remainder
    return remainder[0], remainder[1:]

def _split_imports(body):
    """Given a body reurn the import statemens and remaining statements."""
    imports    = []
    remainder  = []
    stdimports = []
    in_imports = True
    for line in body:
        if in_imports:
            if isinstance(line, ast.Import):
                for alias in line.names:
                    if alias.name in constants.STANDARD_PYTHON_MODULES:
                        stdimports.append(ast.Import(names=[alias]))
                    else:
                        imports.append(ast.Import(names=[alias]))
            elif isinstance(line, ast.ImportFrom):
                new_imports = [ast.ImportFrom(
                    module=line.module,
                    names=[name],
                ) for name in line.names]
                if line.module in constants.STANDARD_PYTHON_MODULES:
                    stdimports += new_imports
                else:
                    imports += new_imports
            else:
                in_imports = False
        if not in_imports:
            remainder.append(line)
    return stdimports, imports, remainder

FORMATTERS = {
    ast.Add: lambda x, y: "+",
    ast.arg: lambda x, y: x.arg,
    ast.arguments: _format_arguments,
    ast.Assign: _format_assign,
    ast.Attribute: _format_attribute,
    ast.BinOp: _format_binop,
    ast.Call: _format_call,
    ast.Compare: _format_compare,
    ast.comprehension: _format_comprehension,
    ast.Dict: _format_dict,
    ast.Eq: _format_eq,
    ast.Expr: _format_expression,
    ast.FunctionDef: _format_function_def,
    ast.If: _format_if,
    ast.Import: _format_import,
    ast.ImportFrom: _format_import_from,
    ast.List: _format_list,
    ast.ListComp: _format_list_comprehension,
    ast.keyword: _format_keyword,
    ast.Mult: _format_multiplication,
    ast.Name: _format_name,
    ast.NameConstant: _format_name_constant,
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
    return _format_body(data.body, context) + "\n"
