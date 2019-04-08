class A():
	pass

class B(A):
	"This just shows I can inherit from A"

class C():
	pass

# a really complex class
class D(C, B):
	pass

print(C)
