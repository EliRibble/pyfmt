biff = 'biff'
baz = "{all} {the} {small} {things}".format(
    all = 1 * 2,
    the = 'foo' + 'bar',
    small = biff,
    things = 8**2,
)
