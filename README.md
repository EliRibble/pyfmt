# Why?

## Horrible SCM diffs?

The Google Style guide has many recommendations that are designed to reduce the blast radius of changes. This includes things like always including dangling commas and using egyptian parens/braces, not aligning whitespace, etc.

This is pragmatic. All common source code management and code review relies heavily on diffs. Those diffs rely heavily on comparing lines of code.

That's because semantic diff is crazy hard.

I think semantic diff is the right way. I think that conceptually we do a bunch of stuff with source code to avoid solving hard problems like semantic diff. I want to see what happens if we stop doing that.

So I ignore any effects this formatter may have if you use a diff tool that is whitespace or newline oriented and assume you have a magical AST-diff from the future.

I know, neat, right?

## Tabs?

Because there really shouldn't be a debate on this. Indentation is significant in Python. You can either represent indentation level n with n tabs or with n\*(space preferences)\*spaces. Then users can configure their text editor to display indentatino level n in whatever way makes sense to them.

What do you lose by doing this? The ability to draw ASCII art in your code with spaces.

Wait, what?

Yeah, you lose the ability to make your arg lists line up with your indentation in weird ways with newlines.

Since pyfmt prohibits drawing ASCII art in anything but comments, you don't lose anything.

Tabs it is.

## Double quotes?

Because Google requires double quotes for docstrings and I prefer to have quotes fully consistent

## Non-Egyptian parens?

Why do we format things vertically as

```
frobinate(
  bar = None,
  baz = None)
```

instead of

```
frobinate(
  bar = None,
  baz = None,
)
```

When the second has better interaction with source control systems by not showing a diff when we add a new parameter?

Because the first option conserves vertical whitespace.

## No parens in for loop target

We do

```
for a, b in foo:
	...
```

instead of

```
for (a, b) in foo:
	...
```

I'm going to claim it's because it removes characters without hurting readability, but honestly it's just because it's what I am used to and I had to make a judgement call.

## Promote else: if: to elif:

When given code like:

```
if foo:
	pass
else:
	if bar:
		pass
```

The formatter will output

```
if foo:
	pass
elif bar:
	pass
```

This seems like a bug. It's not. The two are logically
equivalent and one is shorter than the other, so we
prefer it.

# Hacking

Create a virtualenv. `pip install -e .` at the root of the repository. `nose2` to run tests.

You can run a specific test with high debugging with:

```
cd test
nose2 -F -D test_base.test_generate_format_tests:55 --log-level DEBUG
```
