import logging
import os

import pyfmt.base

INPUT_DIRECTORY = os.path.join(os.path.dirname(__file__), "input")
OUTPUT_DIRECTORY = os.path.join(os.path.dirname(__file__), "output")

def test_generate_format_tests():
	for filename in sorted(os.listdir(INPUT_DIRECTORY)):
		if not filename.startswith("."):
			yield (test_format, filename)

def test_format(filename):
	inputfile = os.path.join(INPUT_DIRECTORY, filename)
	outputfile = os.path.join(OUTPUT_DIRECTORY, filename)

	assert os.path.exists(inputfile), "test isn't sane, got a filename that isn't there"
	assert os.path.exists(outputfile), "missing output file for {}. It should be at {}".format(inputfile, outputfile)
	logging.debug("Reading input from %s", inputfile)
	with open(inputfile, "r") as f:
		content = f.read()

	output = pyfmt.base.serialize(content, max_line_length=80, quote="\"", tab="\t")
	logging.debug("Reading output from %s", outputfile)
	with open(outputfile, "r") as f:
		expected = f.read()

	for line in output.split("\n"):
		assert len(line) <= 80, "{} is {} characters".format(line, len(line))
	assert output == expected, _get_diff(output, expected)

def _get_diff(output, expected):
	char = 0
	line = 0

	for i, c in enumerate(expected):
		if i >= len(output) or c != output[i]:
			break
		if c == "\n":
			line += 1
			char = 0
		char += 1
	return (
		"\n"
		"--------- output repr:\n"
		"{outputrepr}\n"
		"--------- expected repr:\n"
		"{expectedrepr}\n"
		"--------- output:\n"
		"{output}\n"
		"--------- expected:\n"
		"{expected}\n"
		"--------- Failure line {line} char {char}\n"
	).format(
		char         = char,
		expected     = _lined(expected),
		expectedrepr = repr(expected),
		line         = line,
		output       = _lined(output),
		outputrepr   = repr(output))

def _lined(output):
	"Add line numbers to a block of output"
	lines = output.split("\n")

	lines = ["{}: {}".format(i, l) for (i, l) in enumerate(lines)]
	return "\n".join(lines)

