import functools
import logging
import io
import token
import tokenize

from typed_ast import ast3
from pyfmt import alignment, body, constants, decorators, functions, strings, types

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
		attr = value.attr,
	)

def _format_aug_assign(value, context):
	return "{left} {op}= {right}".format(
		left  = _format_value(value.target, context),
		op	= _format_value(value.op, context),
		right = _format_value(value.value, context),
	)

def _format_binop(value, context):
	return "{left} {op} {right}".format(
		left  = _format_value(value.left, context),
		op	= _format_value(value.op, context),
		right = _format_value(value.right, context),
	)

def _format_boolop(value, context):
	parts = [_format_value(v, context) for v in value.values]
	op_part = _format_value(value.op, context)
	return " {} ".format(op_part).join(parts)


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
		decorators_ = decorators.format(value.decorator_list, context)
		body_ = body.format(value.body, context)
	return "{decorators}class {name}({bases}):\n{body}".format(
		bases=", ".join([b.id for b in value.bases]),
		body=body_,
		decorators=decorators_,
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
	return "{{\n\t{}\n}}".format(alignment.on_character(pairs, ": ", joiner="\n\t", tail=","))

def _format_dict_short(pairs, context):
	"Format a dictionary as if it were quite short"
	parts = ["{}: {}".format(k, v) for k, v in pairs]
	return "{{{}}}".format(", ".join(parts))

def _format_eq(value, context):
	return "=="

def _format_except_handler(value, context):
	body_ = body.format(value.body, context)
	type_ = _format_value(value.type, context.reserve(len("except ")))
	return "except {type_}{name}:\n{body}".format(
		body  = body_,
		name  = (" as " + value.name) if value.name else "",
		type_ = type_,
	)

def _format_expression(value, context):
	return _format_value(value.value, context)

def _format_for(value, context):
	else_ = ""
	if value.orelse:
		elsebody = body.format(value.orelse, context)
		else_ = "\nelse:\n{}".format(elsebody)
	return "for {target} in {iter_}:\n{body}{else_}".format(
		body=body.format(value.body, context),
		else_=else_,
		iter_=_format_value(value.iter, context),
		target=_format_value(value.target, context.override(suppress_tuple_parens=True)),
	)

def _format_orelse(orelse, context):
	if not orelse:
		return ""
	# value.orelse will either be a list of ast3.If
	# (if: ... elif: ...) or it will be a list of
	# the content of the "else" clause.
	if isinstance(orelse[0], ast3.If):
		lines = [_format_if(e, context, "elif") for e in orelse]
		results = "\n".join(lines)
		results = "\n" + results
		return results
	
	with context.sub() as sub:
		body_ = body.format(orelse, context)
	return "\nelse:\n{}".format(body_)

def _format_if(value, context, prefix="if"):
	test = _format_value(value.test, context)
	with context.sub() as sub:
		body_ = body.format(value.body, context)
	orelses = _format_orelse(value.orelse, context)
	return "{prefix} {test}:\n{body}{orelses}".format(
		body=body_,
		orelses=orelses,
		prefix=prefix,
		test=test,
	)

def _format_if_exp(value, context):
	return "{result} if {test} else {orelse}".format(
		orelse = context.format_value(value.orelse, context),
		result = context.format_value(value.body, context),
		test   = context.format_value(value.test, context),
	)

def _format_import(imp, context):
	return "import {}".format(
		', '.join(sorted(n.name for n in imp.names)))

def _format_import_from(imp, context):
	return "from {} import {}".format(
		imp.module,
		', '.join(sorted(n.name for n in imp.names)))

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

def _format_slice(value, context):
	lower = _format_value(value.lower, context) if value.lower else ""
	upper = _format_value(value.upper, context) if value.upper else ""
	step = ":" + _format_value(value.step, context) if value.step else ""
	return "{lower}:{upper}{step}".format(
		lower = lower,
		step = step,
		upper = upper,
	)

def _format_starred(value, context):
	return "*" + value.value.id

def _format_targets(targets):
	result = []
	for target in targets:
		if type(target) == ast3.Name:
			result.append(target.id)
		elif type(target) == ast3.Tuple:
			for elt in target.elts:
				result.append(elt.id)
		elif type(target) == ast3.Attribute:
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
		elsebody = body.format(value.orelse, context)
		else_ = "\nelse:\n{}".format(elsebody)
	finally_ = ""
	if value.finalbody:
		finalbody = body.format(value.finalbody, context)
		finally_ = "\nfinally:\n{}".format(finalbody)
	handlers = [_format_except_handler(handler, context) for handler in value.handlers]
	return "try:\n{body}\n{handlers}{else_}{finally_}".format(
		body=body.format(value.body, context),
		else_=else_,
		finally_=finally_,
		handlers="\n".join(handlers),
	)

def _format_tuple(value, context):
	content = [_format_value(elt, context) for elt in value.elts]
	content = ", ".join(content)
	if context.suppress_tuple_parens:
		return content
	return "({})".format(content)

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

def _format_while(value, context):
	return "while {condition}:\n{body}{orelse}".format(
		body=body.format(value.body, context),
		condition=_format_value(value.test, context),
		orelse=_format_orelse(value.orelse, context),
	)

def _format_with(value, context):
	return "with {context}:\n{body}".format(
		body=body.format(value.body, context),
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

FORMATTERS = {
	ast3.Add: lambda x, y: "+",
	ast3.And: lambda x, y: "and",
	ast3.arguments: functions.format_arguments,
	ast3.Assert: _format_assert,
	ast3.Assign: _format_assign,
	ast3.AsyncFunctionDef: functions.format_async_function_def,
	ast3.Attribute: _format_attribute,
	ast3.AugAssign: _format_aug_assign,
	ast3.BinOp: _format_binop,
	ast3.BitAnd: lambda x, y: "&",
	ast3.BitOr: lambda x, y: "|",
	ast3.Break: lambda x, y: "break",
	ast3.BoolOp: _format_boolop,
	ast3.Call: _format_call,
	ast3.ClassDef: _format_class,
	ast3.Compare: _format_compare,
	ast3.comprehension: _format_comprehension,
	ast3.Dict: _format_dict,
	ast3.Div: lambda x, y: "/",
	ast3.Eq: _format_eq,
	ast3.Expr: _format_expression,
	ast3.For: _format_for,
	ast3.FunctionDef: functions.format_function_def,
	ast3.GtE: lambda x, y: ">=",
	ast3.If: _format_if,
	ast3.IfExp: _format_if_exp,
	ast3.Import: _format_import,
	ast3.ImportFrom: _format_import_from,
	ast3.Index: _format_index,
	ast3.List: _format_list,
	ast3.ListComp: _format_list_comprehension,
	ast3.Lt: lambda x, y: "<",
	ast3.LtE: lambda x, y: "<=",
	ast3.keyword: _format_keyword,
	ast3.Mod: lambda x, y: "%",
	ast3.Mult: _format_multiplication,
	ast3.Name: _format_name,
	ast3.NameConstant: _format_name_constant,
	ast3.Not: lambda x, y: "not ",
	ast3.NotEq: lambda x, y: "!=",
	ast3.Num: _format_number,
	ast3.Or: lambda x, y: "or",
	ast3.Pass: lambda x, y: "pass",
	ast3.Pow: lambda x, y: "**",
	ast3.Raise: _format_raise,
	ast3.Return: _format_return,
	ast3.Slice: _format_slice,
	ast3.Starred: _format_starred,
	ast3.Str: strings.format_string,
	ast3.Sub: lambda x, y: "-",
	ast3.Subscript: _format_subscript,
	ast3.Try: _format_try,
	ast3.Tuple: _format_tuple,
	ast3.UnaryOp: _format_unary_op,
	ast3.USub: lambda x, y: "-",
	ast3.While: _format_while,
	ast3.With: _format_with,
	ast3.withitem: _format_withitem,
	ast3.Yield: _format_yield,
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
	data = ast3.parse(content)
	comments = _extract_comments(content)
	context = types.Context(
		comments=comments,
		format_value=_format_value,
		indent=0,
		max_line_length=max_line_length,
		quote=quote,
		tab=tab)
	result = body.format(data.body, context, do_indent=False).strip() + "\n"
	return result
