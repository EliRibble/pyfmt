try:
    raise ValueError()
except (Exception, ValueError) as e:
    print("hello", str(e))
