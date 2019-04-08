def do_stuff(l):
	print(l(1))
	print(l(2))
	print(l(4))

do_stuff(lambda x: x ** 2)
do_stuff(lambda x: print("This is probably a really bad idea: %d" % x))
do_stuff(lambda groot:
	do_stuff(lambda groot_:
	do_stuff(lambda groot__: do_stuff(lambda groot___: print(groot___)))))
