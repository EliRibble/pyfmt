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

def test_alignment_joiner():
	input_ = [
		("a", "bar"),
		("bif", "baz"),
	]
	results = pyfmt.alignment.on_character(input_, ": ", joiner="\n\t")
	assert results == (
		"a  : bar\n\t"
		"bif: baz"
	)

def test_alignment_tail():
	input_ = [
		("a", "bar"),
		("bif", "baz"),
	]
	results = pyfmt.alignment.on_character(input_, ": ", tail=",")
	assert results == (
		"a  : bar,\n"
		"bif: baz,"
	)
