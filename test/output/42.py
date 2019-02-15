def generator():
	for i in range(10):
		yield i

def main():
	for thing in generator():
		print(thing)

if __name__ == "__main__":
	main()
