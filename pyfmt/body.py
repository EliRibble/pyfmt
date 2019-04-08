import logging

from pyfmt import constants
from typed_ast import ast3


def format(body, context, do_indent=True):
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
   
def _format_constants(constants, context):
	return sorted([context.format_value(c, context) for c in constants])

def _format_content(section, context) -> list:
	"""Convert a tree of content into a list of lines to be indented and joined."""
	if not section:
		return []

	BLANKLINES = {
		ast3.ClassDef: 1,
		ast3.FunctionDef: 1,
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
		content = context.format_value(node, context)
		content_lines = content.split("\n")
		content_lines[0] = content_lines[0] + inline_comment
		lines += content_lines
		blanks = BLANKLINES.get(type(node), 0)
		lines += ([""] * blanks)
	return lines

def _format_declarations(declarations, context):
	return [context.format_value(d, context) for d in declarations]

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

def _format_imports(imports, context) -> list:
	lines = [context.format_value(i, context) for i in imports]
	return sorted(lines)

def _split_constants(remainder):
	"Given the remainder of a body return the constants and whatever else is left."
	constants = []
	while remainder and isinstance(remainder[0], ast3.Assign):
		node = remainder[0]
		if len(node.targets) > 1:
			break;
		if not isinstance(node.targets[0], ast3.Name):
			break;
		if type(node.value) not in (ast3.NameConstant, ast3.Str, ast3.Num):
			break;
		constants.append(remainder.pop(0))
	logging.debug("Found %d constant lines", len(constants))
	return constants, remainder

def _split_declarations(remainder):
	"Given the remainder of a body return the declarations and whatever else is left."
	declarations = []
	while remainder and isinstance(remainder[0], ast3.Assign):
		node = remainder[0]
		if len(node.targets) > 1:
			break;
		if not isinstance(node.targets[0], ast3.Name):
			break;
		if type(node.value) not in (
			ast3.Call,
			ast3.NameConstant,
			ast3.Num,
			ast3.Str):
			break;
		declarations.append(remainder.pop(0))
	logging.debug("Found %d declaration lines", len(declarations))
	return declarations, remainder

def _split_docstring(remainder):
	"""Given the non-import sections of a body, return the docstring and remainder."""
	if not (remainder and isinstance(remainder[0], ast3.Expr) and isinstance(remainder[0].value, ast3.Str)):
		return [], remainder
	return remainder[0], remainder[1:]

def _split_imports(body):
	"""Given a body reurn the import statemens and remaining statements."""
	imports	= []
	remainder  = []
	stdimports = []
	in_imports = True
	for line in body:
		if in_imports:
			if isinstance(line, ast3.Import):
				for alias in line.names:
					if alias.name in constants.STANDARD_PYTHON_MODULES:
						stdimports.append(ast3.Import(names=[alias]))
					else:
						imports.append(ast3.Import(names=[alias]))
			elif isinstance(line, ast3.ImportFrom):
				new_imports = [ast3.ImportFrom(
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

