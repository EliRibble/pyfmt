def decorator(f, g):
	return print

class A:
	@decorator("foo", max)
	@decorator("bar", min)
	def my_function():
		print("hello")
