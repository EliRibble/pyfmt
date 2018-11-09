# Why?

## Tabs?

Because there really shouldn't be a debate on this. Indentation is significant in Python. You can either represent indentation level n with n tabs or with n\*(space preferences)\*spaces. Then users can configure their text editor to display indentatino level n in whatever way makes sense to them.

What do you lose by doing this? The ability to draw ASCII art in your code with spaces.

Wait, what?

Yeah, you lose the ability to make your arg lists line up with your indentation in weird ways with newlines.

Since pyfmt prohibits drawing ASCII art in anything but comments, you don't lose anything.

Tabs it is.

## Double quotes?

Because Google requires double quotes for docstrings and I prefer to have quotes fully consistent

# Hacking

Create a virtualenv. `pip install -e .` at the root of the repository. `nose2` to run tests.
