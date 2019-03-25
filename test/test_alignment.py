import pyfmt.alignment

def test_alignment_simple():
	input_ = [
		("a", "bar"),
		("bif", "baz"),
	]
	results = pyfmt.alignment.on_character(input_, " = ")
	assert results == (
		"a   = bar\n"
		"bif = baz"
	)
