def print_stuff(a, b, *args, c=None, d={}, **kwargs):
	print(a, b, *args, c, d, kwargs)

print_stuff(
	"this is a",
	"this is b",
	"this is something in args",
	"also in args",
	c = "a thing for c",
	d = "d gets a different thing",
	e = "e came out of nowhere",
	f = "f is right out")
