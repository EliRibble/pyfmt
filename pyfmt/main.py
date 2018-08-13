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

def _format_arguments(arguments, indent):
    parts = []
    for arg in arguments.args:
        parts.append(_format_value(arg, indent))
    return ', '.join(parts)

def _format_targets(targets):
    result = []
    for target in targets:
        if type(target) == ast.Name:
            result.append(target.id)
        elif type(target) == ast.Tuple:
            for elt in target.elts:
                result.append(elt.id)
    return ', '.join(result)

def _format_list_comprehension(comp, indent):
    assert len(comp.generators) == 1
    return "[{elt} {generators}]".format(
        elt = _format_value(comp.elt, indent),
        generators = _format_value(comp.generators[0], indent),
    )

def _format_value(value, indent):
    if type(value) == ast.arg:
        return value.arg
    elif type(value) == ast.Assign:
        targets = _format_targets(value.targets)
        value = _format_value(value.value, indent)
        return "{targets} = {value}".format(
            targets=targets,
            value=value,
        )
    elif type(value) == ast.BinOp:
        return '{left} {op} {right}'.format(
            left  = _format_value(value.left, indent),
            op    = _format_value(value.op, indent),
            right = _format_value(value.right, indent),
        )
    elif type(value) == ast.Call:
        arguments = _format_arguments(value, indent)
        return '{func}({arguments})'.format(
            arguments=arguments,
            func=value.func.id,
        )
    elif type(value) == ast.comprehension:
        return "for {target} in {iter}".format(
            target=_format_value(value.target, indent),
            iter=_format_value(value.iter, indent),
        )
    elif type(value) == ast.Expr:
        return _format_value(value.value, indent)
    elif type(value) == ast.FunctionDef:
        return _format_function_def(value, indent)
    elif type(value) == ast.ListComp:
        return _format_list_comprehension(value, indent)
    elif type(value) == ast.Mult:
        return '*'
    elif type(value) == ast.Name:
        return str(value.id)
    elif type(value) == ast.Num:
        return str(value.n)
    elif type(value) == ast.Return:
        return 'return {}'.format(_format_value(value.value, indent))
    elif type(value) == ast.Str:
        return '"{}"'.format(value.s)
    elif type(value) == ast.Tuple:
        return ', '.join([_format_value(elt, indent) for elt in value.elts])
    else:
        raise Exception("No idea how to format value {}".format(type(value)))

def _format_body(body, indent):
    lines = [_format_value(line, indent) for line in body]
    tabbed_lines = [(TAB * indent) + line for line in lines]
    return '\n'.join(tabbed_lines)

def _format_function_def(func, indent=0):
    arguments = _format_arguments(func.args, indent)
    body = _format_body(func.body, indent=indent+1)
    return 'def {name}({arguments}):\n{body}'.format(
        name=func.name,
        arguments=arguments,
        body=body,
    )

FORMATTERS = {
    ast.FunctionDef: _format_function_def,
}
def formatted(content):
    result = ""
    for part in content.body:
        result += FORMATTERS[type(part)](part)
    return result
