def get_formatted_output(somedata):
	return (
		"\n\n"
		"--------------------this is a divider--------------------\n"
		"{somedata}\n"
		"--------------------end divider--------------------"
	).format(somedata=somedata)

for i in range(3):
	print(get_formatted_output(i))
