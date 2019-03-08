def outer(f):
	def nested(g):
		def doublenested(h):
			return (
				"This is going to be a really long string that is super nested inside a "
				"bunch of definitions. Just want to make sure it gets sanely broken up "
				"into parts."
			)
