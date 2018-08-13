import argparse
import ast

TAB = '\t'

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='The file to process')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        content = ast.parse(f.read())
    print(formatted(content))

def _format_arg(value, indent):
    return value.arg

def _format_arguments(arguments, keywords, indent):
    parts = []
    for arg in arguments:
        parts.append(_format_value(arg, indent))
    for kwarg in keywords:
        parts.append(_format_value(kwarg, indent))
    return ', '.join(parts)

def _format_assign(value, indent):
    targets = _format_targets(value.targets)
    value = _format_value(value.value, indent)
    return "{targets} = {value}".format(
        targets=targets,
        value=value,
    )

def _format_attribute(value, indent):
    return '{value}.{attr}'.format(
        value = _format_value(value.value, indent),
        attr = _format_value(value.attr, indent),
    )

def _format_binop(value, indent):
    return '{left} {op} {right}'.format(
        left  = _format_value(value.left, indent),
        op    = _format_value(value.op, indent),
        right = _format_value(value.right, indent),
    )

def _format_body(body, indent):
    lines = [_format_value(line, indent) for line in body]
    tabbed_lines = [(TAB * indent) + line for line in lines]
    return '\n'.join(tabbed_lines)

def _format_call(value, indent):
    arguments = _format_arguments(value.args, value.keywords, indent)
    return '{func}({arguments})'.format(
        arguments=arguments,
        func=_format_value(value.func, indent),
    )

def _format_comprehension(value, indent):
    return "for {target} in {iter}".format(
        target=_format_value(value.target, indent),
        iter=_format_value(value.iter, indent),
    )

def _format_expression(value, indent):
    return _format_value(value.value, indent)

def _format_function_def(func, indent=0):
    arguments = _format_arguments(func.args, func.keywords, indent)
    body = _format_body(func.body, indent=indent+1)
    return 'def {name}({arguments}):\n{body}'.format(
        name=func.name,
        arguments=arguments,
        body=body,
    )

def _format_list_comprehension(comp, indent):
    assert len(comp.generators) == 1
    return "[{elt} {generators}]".format(
        elt = _format_value(comp.elt, indent),
        generators = _format_value(comp.generators[0], indent),
    )

def _format_keyword(value, indent):
    return "{arg}={value}".format(
        arg = value.arg,
        value = _format_value(value.value, indent),
    )

def _format_multiplication(value, indent):
    return '*'

def _format_name(value, indent):
    return str(value.id)

def _format_number(value, indent):
    return str(value.n)

def _format_return(value, indent):
    return 'return {}'.format(_format_value(value.value, indent))

def _format_string(value, indent):
    return '"{}"'.format(value.s)

def _format_targets(targets):
    result = []
    for target in targets:
        if type(target) == ast.Name:
            result.append(target.id)
        elif type(target) == ast.Tuple:
            for elt in target.elts:
                result.append(elt.id)
    return ', '.join(result)

def _format_tuple(value, indent):
    return ', '.join([_format_value(elt, indent) for elt in value.elts])

def _format_value(value, indent):
    formatter = FORMATTERS.get(type(value))
    if formatter is None:
        raise Exception("Need to write a formatter for {}".format(type(value)))
    return formatter(value, indent)

FORMATTERS = {
    ast.Add: lambda x, y: '+',
    ast.arg: _format_arg,
    ast.Assign: _format_assign,
    ast.Attribute: _format_attribute,
    ast.BinOp: _format_binop,
    ast.Call: _format_call,
    ast.comprehension: _format_comprehension,
    ast.Expr: _format_expression,
    ast.FunctionDef: _format_function_def,
    ast.ListComp: _format_list_comprehension,
    ast.keyword: _format_keyword,
    ast.Mult: _format_multiplication,
    ast.Name: _format_name,
    ast.Num: _format_number,
    ast.Pow: lambda x, y: '**',
    ast.Return: _format_return,
    str: lambda x, y: x,
    ast.Str: _format_string,
    ast.Tuple: _format_tuple,
}

def formatted(content):
    return '\n'.join([
        FORMATTERS[type(part)](part, 0) for part in content.body])
