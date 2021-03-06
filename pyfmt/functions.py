import collections
import typing

from pyfmt import alignment, body, decorators, errors
from typed_ast import ast3

Arguments = collections.namedtuple("Arguments", ("arguments", "karguments", "kwargs", "vargs"))

class Argument:
	def __init__(self,
		annotation: typing.Optional['ast3.Annotation'],
		default: typing.Optional['ast3.Token'],
		name: ast3.Name,
	):
		self.annotation = annotation
		self.default = default
		self.name = name

def format_arguments(value, context):
	"""Format an argument like 'x, y = z'"""
	args = _collate_arguments(value, context)
	try:
		return _format_arguments_horizontally(value, context, args)
	except errors.NotPossible:
		pass
	return _format_arguments_vertically(value, context, args)

def format_async_function_def(func, context):
	return _format_function_def("async def", func, context)

def format_function_def(func, context):
	return _format_function_def("def", func, context)

def format_lambda(lambda_, context):
	prefix = len("lambda ")
	args = context.format_value(lambda_.args, context.reserve(prefix))
	body_ = context.format_value(lambda_.body, context=context.reserve(prefix + len(args)))
	possible = "lambda {args}: {body}".format(
		args = args,
		body = body_,
	)
	lines = possible.split("\n")
	if all([len(l) <= context.remaining_line_length for l in lines]):
		return possible
	body_parts = body_.split("\n")
	body_parts = context.add_indent(body_parts)
	return "lambda {args}:\n{body}".format(
		args = args,
		body = "\n".join(body_parts),
	)

def _align_kwargs(kwargs: typing.Iterable[Arguments]) -> typing.Iterable[typing.Text]:
	"""Given an iterable of kwargs line them up and return them."""
	parts = [(kwarg.name, kwarg.default) for kwarg in kwargs]
	parts = sorted(parts, key=lambda x: x[0])
	return alignment.on_character(parts, " = ")

def _collate_arguments(value, context) -> typing.Iterable[Arguments]:
	"""Given the arguments turn them into an easier structure.

	The idea here is that its obnoxious to deal with the way
	Python's ast module breaks up function arguments with
	defaults. So do that break up once and put it into a
	different structure that's easier to work with.
	"""
	results = []
		
	no_defaults = len(value.args) - len(value.defaults)
	for i, arg in enumerate(value.args):
		default = value.defaults[i-no_defaults] if i >= no_defaults else None
		results.append(Argument(
			annotation = context.format_value(arg.annotation, context) if arg.annotation else None,
			default	   = context.format_value(default, context) if default else None,
			name	   = arg.arg,
		))
	assert len(value.kwonlyargs) == len(value.kw_defaults)
	for i, kwarg in enumerate(value.kwonlyargs):
		default = value.kw_defaults[i]
		results.append(Argument(
			annotation = context.format_value(kwarg.annotation) if kwarg.annotation else None,
			default	   = context.format_value(default, context),
			name	   = kwarg.arg,
		))
	return results

def _format_arg(arg, context):
	return "{arg}{annotation}{default}".format(
		annotation = (": " + arg.annotation) if arg.annotation else "",
		arg = arg.name,
		default = ("=" + arg.default) if arg.default else "",
	)

def _format_arguments_horizontally(value, context, args):
	args = _collate_arguments(value, context)
	parts = [_format_arg(arg, context) for arg in args[:len(value.args)]]
	if value.vararg:
		parts.append("*" + value.vararg.arg)
	parts += [_format_arg(kwarg, context) for kwarg in args[len(value.args):]]
	if value.kwarg:
		parts.append("**" + value.kwarg.arg)
	result = ", ".join(parts)
	if len(result) <= context.remaining_line_length:
		return result
	raise errors.NotPossible("Line '%s' is too long.")

def _format_arguments_vertically(value, context, args):
	parts = [_format_arg(arg, context) for arg in args[:len(value.args)]]
	if value.vararg:
		parts.append("*" + value.vararg.arg)
	parts += _align_kwargs(args[len(value.args):])
	if value.kwarg:
		parts.append("**" + value.kwarg.arg)
	return "\n\t" + (",\n\t".join(parts))

def _format_function_def(prefix, func, context):
	decorators_ = decorators.format(func.decorator_list, context)
	def_ = "{} {}".format(prefix, func.name)
	arguments = context.format_value(func.args, context.reserve(len(def_)))
	with context.sub() as sub:
		body_ = body.format(func.body, context=context)
	return "{decorators}{def_}({arguments}){returns}:\n{body}".format(
		arguments=arguments,
		body=body_,
		decorators=decorators_,
		def_=def_,
		returns=" -> " + context.format_value(func.returns, context) if func.returns else "",
	)

