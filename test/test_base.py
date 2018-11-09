import os

import pyfmt.base

INPUT_DIRECTORY = os.path.join(
    os.path.dirname(__file__),
    "input",
)

OUTPUT_DIRECTORY = os.path.join(
    os.path.dirname(__file__),
    "output",
)

def test_generate_format_tests():
    for filename in os.listdir(INPUT_DIRECTORY):
        yield test_format, filename

def test_format(filename):
    inputfile = os.path.join(INPUT_DIRECTORY, filename)
    outputfile = os.path.join(OUTPUT_DIRECTORY, filename)
    assert os.path.exists(inputfile), "test isn't sane, got a filename that isn't there"
    assert os.path.exists(outputfile), "missing output file for {}. It should be at {}".format(inputfile, outputfile)
    with open(inputfile, 'r') as f:
        content = f.read()
    output = pyfmt.base.serialize(content, max_line_length=80, quote="\"", tab="\t")
    with open(outputfile, 'r') as f:
        expected = f.read()
    assert output == expected, "\n--------- output:\n{}--------- expected: \n{}".format(output, expected)
