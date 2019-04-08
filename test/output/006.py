biff = "biff"

baz = "{all} {the} {small} {things}".format(
	all    = 1 * 2,
	small  = biff,
	the    = "foo" + "bar",
	things = 8 ** 2)
