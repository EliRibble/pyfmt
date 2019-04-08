def sequence(i):
	x = 0
	while x < i:
		yield x
		x += 1

for x in sequence(10):
	print(x)
