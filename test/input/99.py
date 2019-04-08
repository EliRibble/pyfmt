def some_really_long_function_name(i):
	return i ** i

print([(
		some_really_long_function_name(i),
		some_really_long_function_name(i+1),
		some_really_long_function_name(i+3),
	) for i in range(10)])
