def format(decorators, context):
	lines = ["@" + context.format_value(d, context) for d in decorators]
	result = "\n".join(lines)
	return result + "\n" if result else ""
