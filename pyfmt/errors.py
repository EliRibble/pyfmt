class NotPossible(Exception):
	"""Indicates a particular request cannot be done.

	For example, a request to format something in a
	single line when it would make the line too long.
	"""

