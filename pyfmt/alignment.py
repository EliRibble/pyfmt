"""Module for lining things up."""
import typing

LineParts = typing.Tuple[typing.Text, typing.Text]

def on_character(
	lines: typing.Iterable[LineParts],
	separator: typing.Text,
	joiner: typing.Text="\n",
	tail: typing.Optional[typing.Text]=None) -> typing.Text:
	"""Align a set of lines on a common character.

	Given something like [("a", "foo"), ("biff", "gromulon")], "," this should return something like:

	"a"	, "foo"
	"biff" , "gromulon"
	"""
	if not lines:
		return ""
	max_first = max(len(l[0]) for l in lines)
	results = [
		"{{first: <{}}}{{separator}}{{second}}{{tail}}".format(max_first).format(
			first=first,
			second=second,
			separator=separator,
			tail=tail if tail else "",
		) for first, second in lines]
	return joiner.join(results)

