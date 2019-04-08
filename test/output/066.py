try:
	raise ValueError()
except ValueError as v:
	print("value error", str(v))
except Exception as e:
	print("hello", str(e))
else:
	print("hit the else.")
finally:
	print("And finally we're done.")
