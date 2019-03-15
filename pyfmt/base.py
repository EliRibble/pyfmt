import ast
import functools
import logging
import io
import token
import tokenize

from pyfmt import constants, strings, types

def _format_arguments(value, context):
    """Format an argument like 'x, y = z'"""
    parts = []
    no_defaults = len(value.args) - len(value.defaults)
    for i, arg in enumerate(value.args):
        if i >= no_defaults:
            default = value.defaults[i]
            parts.append("{arg}={default}".format(
                arg = arg.arg,
                default = default.value,
            ))
        else:
            parts.append(arg.arg)
    if value.vararg:
        parts.append("*" + value.vararg.arg)
    assert len(value.kwonlyargs) == len(value.kw_defaults)
    for i, kwarg in enumerate(value.kwonlyargs):
        parts.append("{kwarg}={default}".format(
            kwarg=kwarg.arg,
            default=value.kw_defaults[i].value))
    if value.kwarg:
        parts.append("**" + value.kwarg.arg)
    possible = ", ".join(parts)
    return possible

def _format_assert(value, context):
    if value.msg:
        assert_ = "assert {test}, ".format(
            test=_format_value(value.test, context),
        )
        msg = _format_value(value.msg, context.reserve(len(assert_)))
        return "{assert_}{msg}".format(
            assert_=assert_,
            msg=msg,
        )
    return "assert {}".format(_format_value(value.test, context))

def _format_assign(value, context):
    targets = _format_targets(value.targets)
    value = _format_value(value.value, context.reserve(len(targets) + 3))
    return "{targets} = {value}".format(
        targets=targets,
        value=value,
    )

def _format_attribute(value, context):
    return "{value}.{attr}".format(
        value = _format_value(value.value, context),
        attr = _format_value(value.attr, context),
    )

def _format_aug_assign(value, context):
    return "{left} += {right}".format(
        left = _format_value(value.target, context),
        right = _format_value(value.value, context),
    )

def _format_binop(value, context):
    return "{left} {op} {right}".format(
        left  = _format_value(value.left, context),
        op    = _format_value(value.op, context),
        right = _format_value(value.right, context),
    )

def _format_boolop(value, context):
    parts = [_format_value(v, context) for v in value.values]
    op_part = _format_value(value.op, context)
    return " {} ".format(op_part).join(parts)

def _format_body(body, context, do_indent=True):
    """Format a body like a function or module body.

    This breaks the body into large sections for the sake
    of sorting certain orderable statements within those
    sections, like imports.
    """
    doc, remainder = _split_docstring(body)
    stdimports, imports, remainder = _split_imports(remainder)
    constants, remainder = _split_constants(remainder)
    declarations, remainder = _split_declarations(remainder)

    constants = _format_constants(constants, context)
    declarations = _format_declarations(declarations, context)
    docstring = _format_docstring(doc, context)
    stdimports = _format_imports(stdimports, context)
    imports = _format_imports(imports, context)
    content = _format_content(remainder, context)
    for section in (constants, declarations, stdimports, imports):
        if section:
            section.append("")

    # There may be comments in the body that were not extracted
    # in _format_content because it was empty. Find any of those
    # comments and add them to the body now
    comments = []
    for node in body[::-1]:
        if hasattr(node, "lineno"):
            # We need to capture any comments that are at the end of this block of
            # code. In order to do that we take whatever the highest line number
            # is and we get the comments for an imaginary line of code that is
            # beyond wherever the comment would be (+2).
            comments = context.get_standalone_comments(node.lineno+2, node.col_offset, allow_dedent=False)
            break
            
    body = [l for section in (docstring, stdimports, imports, constants, declarations, content) for l in section]
    body += [comment.content for comment in comments]
    return context.do_indent(body) if do_indent else "\n".join(body)
   

def _format_call(value, context):
    """Format a function call like 'print(a*b, foo=x)'"""
    result = _format_call_horizontal(value, context)
    last_newline = result.rfind("\n")
    last_line = result[last_newline:] if last_newline > 0 else result
    if len(last_line) < context.remaining_line_length:
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
        _format_keyword(k, context, pad_key=max_kwarg_key_len) for k in sorted(value.keywords, key=lambda keyword: keyword.arg)
    ]
    if args:
        return "{func}({arguments})".format(
            arguments=",\n\t".join(args + kwargs),
            func=_format_value(value.func, context)
        )
    return "{func}(\n\t{kwargs})".format(
        kwargs=",\n\t".join(kwargs),
        func=_format_value(value.func, context))

def _format_class(value, context):
    with context.sub() as sub:
        body = _format_body(value.body, context)
    return "class {name}({bases}):\n{body}".format(
        bases=", ".join([b.id for b in value.bases]),
        body=body,
        name=value.name,
    )

def _format_compare(value, context):
    comparisons = [
        "{} {}".format(
            _format_value(op, context),
            _format_value(comparator, context),
        ) for op, comparator in zip(
            value.ops,
            value.comparators,
        )
    ]
    return "{left} {comparisons}".format(
        left=_format_value(value.left, context),
        comparisons=" ".join(comparisons),
    )

def _format_comprehension(value, context):
    return "for {target} in {iter}".format(
        target=_format_value(value.target, context),
        iter=_format_value(value.iter, context),
    )

def _format_constants(constants, context):
    return sorted([_format_value(c, context) for c in constants])

def _format_content(section, context) -> list:
    """Convert a tree of content into a list of lines to be indented and joined."""
    if not section:
        return []

    BLANKLINES = {
        ast.ClassDef: 1,
        ast.FunctionDef: 1,
    }
    lines = []
    for node in section:
        if hasattr(node, 'lineno'):
            pre_comments = context.get_standalone_comments(node.lineno, node.col_offset)
            logging.debug("Found %d pre-comments for %s content at %d", len(pre_comments), type(node), node.lineno)
            lines += [comment.content for comment in pre_comments]
            inline_comment = context.get_inline_comment(node.lineno).content
            inline_comment = " " + inline_comment if inline_comment else ""
        else:
            inline_comment = ""
        content = _format_value(node, context)
        content_lines = content.split("\n")
        content_lines[0] = content_lines[0] + inline_comment
        lines += content_lines
        blanks = BLANKLINES.get(type(node), 0)
        lines += ([""] * blanks)
    return lines

def _format_declarations(declarations, context):
    return [_format_value(d, context) for d in declarations]

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

def _format_docstring(value, context) -> list:
    """Given a single expression known to be a docstring apply special formatting.

    Returns:
        A list of lines
    """
    # A docstring will be a single really long string expression, often with
    # embedded tabs for formatting. We need to rip those out to apply our own
    # formatting.
    if not value:
        return []
    subvalue = value.value
    if "\n" in subvalue.s:
        content = (context.quote * 3) + subvalue.s + (context.quote * 3)
        lines = content.split("\n")
    else:
        lines = [context.quote + subvalue.s + context.quote]
    clean_lines = [line.strip() if line else "" for line in lines]
    return clean_lines

def _format_eq(value, context):
    return "=="

def _format_except_handler(value, context):
    body = _format_body(value.body, context)
    return "except {type_}{name}:\n{body}".format(
        body  = body,
        name  = (" as " + value.name) if value.name else "",
        type_ = _format_value(value.type, context.reserve(len("except ")))
    )

def _format_expression(value, context):
    return _format_value(value.value, context)

def _format_for(value, context):
    else_ = ""
    if value.orelse:
        elsebody = _format_body(value.orelse, context)
        else_ = "\nelse:\n{}".format(elsebody)
    return "for {target} in {iter_}:\n{body}{else_}".format(
        body=_format_body(value.body, context),
        else_=else_,
        iter_=_format_value(value.iter, context),
        target=_format_value(value.target, context),
    )

def _format_function_def(func, context):
    arguments = _format_value(func.args, context)
    with context.sub() as sub:
        body = _format_body(func.body, context=context)
    return "def {name}({arguments}):\n{body}".format(
        arguments=arguments,
        body=body,
        name=func.name,
    )

def _format_if(value, context):
    test = _format_value(value.test, context)
    with context.sub() as sub:
        body = _format_body(value.body, context)
    return "if {}:\n{}".format(test, body)

def _format_import(imp, context):
    return "import {}".format(
        ', '.join(sorted(n.name for n in imp.names)))

def _format_import_from(imp, context):
    return "from {} import {}".format(
        imp.module,
        ', '.join(sorted(n.name for n in imp.names)))

def _format_imports(imports, context) -> list:
    lines = [_format_value(i, context) for i in imports]
    return sorted(lines)

def _format_index(value, context):
    return _format_value(value.value, context)

def _format_list(value, context):
    elts = [
        _format_value(e, context) for e in value.elts
    ]
    return "[{}]".format(", ".join(elts))

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

def _format_raise(value, context):
    assert value.cause is None
    return "raise {}".format(_format_value(value.exc, context.reserve(len("raise "))))

def _format_return(value, context):
    return "return {}".format(_format_value(value.value, context.reserve(len("return "))))

def _format_starred(value, context):
    return "*" + value.value.id

def _format_targets(targets):
    result = []
    for target in targets:
        if type(target) == ast.Name:
            result.append(target.id)
        elif type(target) == ast.Tuple:
            for elt in target.elts:
                result.append(elt.id)
        elif type(target) == ast.Attribute:
            result.append("{}.{}".format(target.value.id, target.attr))
        else:
            raise Exception("No idea how to format target: {}".format(target))
    return ", ".join(result)

def _format_subscript(value, context):
    return "{value}[{slice_}]".format(
        value=_format_value(value.value, context),
        slice_=_format_value(value.slice, context),
    )

def _format_try(value, context):
    else_ = ""
    if value.orelse:
        elsebody = _format_body(value.orelse, context)
        else_ = "\nelse:\n{}".format(elsebody)
    finally_ = ""
    if value.finalbody:
        finalbody = _format_body(value.finalbody, context)
        finally_ = "\nfinally:\n{}".format(finalbody)
    handlers = [_format_except_handler(handler, context) for handler in value.handlers]
    return "try:\n{body}\n{handlers}{else_}{finally_}".format(
        body=_format_body(value.body, context),
        else_=else_,
        finally_=finally_,
        handlers="\n".join(handlers),
    )

def _format_tuple(value, context):
    return ", ".join([_format_value(elt, context) for elt in value.elts])

def _format_unary_op(value, context):
    return "{op}{operand}".format(
        op=_format_value(value.op, context),
        operand=_format_value(value.operand, context),
    )

def _format_value(value, context):
    formatter = FORMATTERS.get(type(value))
    if formatter is None:
        raise Exception("Need to write a formatter for {}".format(type(value)))
    return formatter(value, context)

def _format_yield(value, context):
    return "yield {}".format(_format_value(value.value, context))

def _format_with(value, context):
    return "with {context}:\n{body}".format(
        body=_format_body(value.body, context),
        context=_format_value(value.items[0], context),
    )

def _format_withitem(value, context):
    optional = ""
    if value.optional_vars:
        optional = " as " + _format_value(value.optional_vars, context)
    return "{expr}{optional}".format(
        expr=_format_value(value.context_expr, context),
        optional=optional,
    )

def _split_constants(remainder):
    "Given the remainder of a body return the constants and whatever else is left."
    constants = []
    while remainder and isinstance(remainder[0], ast.Assign):
        node = remainder[0]
        if len(node.targets) > 1:
            break;
        if not isinstance(node.targets[0], ast.Name):
            break;
        if type(node.value) not in (ast.NameConstant, ast.Str, ast.Num):
            break;
        constants.append(remainder.pop(0))
    logging.debug("Found %d constant lines", len(constants))
    return constants, remainder

def _split_declarations(remainder):
    "Given the remainder of a body return the declarations and whatever else is left."
    declarations = []
    while remainder and isinstance(remainder[0], ast.Assign):
        node = remainder[0]
        if len(node.targets) > 1:
            break;
        if not isinstance(node.targets[0], ast.Name):
            break;
        if type(node.value) not in (
            ast.Call,
            ast.NameConstant,
            ast.Num,
            ast.Str):
            break;
        declarations.append(remainder.pop(0))
    logging.debug("Found %d declaration lines", len(declarations))
    return declarations, remainder

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
    ast.And: lambda x, y: "and",
    # ast.arg: lambda x, y: x.arg,
    ast.arguments: _format_arguments,
    ast.Assert: _format_assert,
    ast.Assign: _format_assign,
    ast.Attribute: _format_attribute,
    ast.AugAssign: _format_aug_assign,
    ast.BinOp: _format_binop,
    ast.Break: lambda x, y: "break",
    ast.BoolOp: _format_boolop,
    ast.Call: _format_call,
    ast.ClassDef: _format_class,
    ast.Compare: _format_compare,
    ast.comprehension: _format_comprehension,
    ast.Dict: _format_dict,
    ast.Eq: _format_eq,
    ast.Expr: _format_expression,
    ast.For: _format_for,
    ast.FunctionDef: _format_function_def,
    ast.GtE: lambda x, y: ">=",
    ast.If: _format_if,
    ast.Import: _format_import,
    ast.ImportFrom: _format_import_from,
    ast.Index: _format_index,
    ast.List: _format_list,
    ast.ListComp: _format_list_comprehension,
    ast.keyword: _format_keyword,
    ast.Mod: lambda x, y: "%",
    ast.Mult: _format_multiplication,
    ast.Name: _format_name,
    ast.NameConstant: _format_name_constant,
    ast.Not: lambda x, y: "not ",
    ast.NotEq: lambda x, y: "!=",
    ast.Num: _format_number,
    ast.Or: lambda x, y: "or",
    ast.Pass: lambda x, y: "pass",
    ast.Pow: lambda x, y: "**",
    ast.Raise: _format_raise,
    ast.Return: _format_return,
    str: lambda x, y: x,
    ast.Starred: _format_starred,
    ast.Str: strings.format_string,
    ast.Sub: lambda x, y: "-",
    ast.Subscript: _format_subscript,
    ast.Try: _format_try,
    ast.Tuple: _format_tuple,
    ast.UnaryOp: _format_unary_op,
    ast.With: _format_with,
    ast.withitem: _format_withitem,
    ast.Yield: _format_yield,
}

def _extract_comments(content):
    "Given content get all comments and their locations"
    results = [None] * (content.count("\n") + 1)
    buf = io.BytesIO(content.encode("utf-8")) # ReadLine(content)
    for token_type, tok, begin, end, line in tokenize.tokenize(buf.__next__):
        if token_type == token.N_TOKENS:
            logging.debug("Adding comment N_TOKENS from %s to %s: '%s'", begin, end, tok)
            comment = types.Comment(begin[0], begin[1], tok, dedent=False)
            results[comment.srow] = comment
        # This logic handles comments that happen after a 
        # block. For some reason the token type is not
        # present in the token library (so we can't do
        # token.<foo> in the comparison here. We also
        # bump up the row index so that it is not treated
        # as a trailing comment from the previous block
        elif token_type == 58 and '#' in tok:
            value = tok.strip()
            logging.debug("Adding dedent comment NL from %s to %s: '%s'", begin, end, value)
            comment = types.Comment(begin[0], begin[1], value, dedent=True)
            results[comment.srow] = comment
        else:
            logging.debug("Skip %s at %s to %s '%s'", token.tok_name[token_type], begin, end, tok)
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug("Complete extracted comments:")
        for i, comment in enumerate(results):
            logging.debug("%d: %s", i, comment)
    return results

def serialize(content, max_line_length=120, quote="\"", tab="\t"):
    data = ast.parse(content)
    comments = _extract_comments(content)
    context = types.Context(
        comments=comments,
        indent=0,
        max_line_length=max_line_length,
        quote=quote,
        tab=tab)
    result = _format_body(data.body, context, do_indent=False).strip() + "\n"
    return result
