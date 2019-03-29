def decorator(c):
	return print

@decorator
class A():
	pass
