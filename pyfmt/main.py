import argparse

import pyfmt.base

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='The file to process')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        content = f.read()
    print(pyfmt.base.serialize(content, tab='\t'))
