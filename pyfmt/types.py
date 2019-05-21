import collections
import contextlib
import logging
import typing

Comment = collections.namedtuple("Comment", ("srow", "scolumn", "content", "dedent"))

class Context():
    """Represents the context of the operation being serialized.

    This class is used heavily in making decisions about the application
    of whitespace.
    """
    def __init__(self, format_value, comments=None, indent=0, inline=False, max_line_length=120, quote="'", reserved_space=0, suppress_tuple_parens=False, tab='\t'):
        self.comments = comments or []
        self._comments_read_index = 0
        self.format_value = format_value
        self.indent = indent
        self.inline = inline
        self.max_line_length = max_line_length
        self.quote = quote
        self.reserved_space = reserved_space
        self.suppress_tuple_parens = suppress_tuple_parens
        self.tab = tab

    def add_indent(self, lines: typing.Iterable[typing.Text]) -> typing.Iterable[typing.Text]:
        """Indent a list of lines by a single indent.

        Args:
            lines: a list of lines to indent and join
        Returns: The joined lines with indentation
        """
        return [
            self.tab + line if line else ""
            for line in lines]

    def get_inline_comment(self, lineno):
        """Get comment in the provided line."""
        empty_comment = Comment(None, None, "", False)
        if lineno < self._comments_read_index:
            return empty_comment
        result = self.comments[lineno]
        if result and result.dedent:
            return empty_comment
        self._comments_read_index += 1
        return result or empty_comment

    def get_standalone_comments(self, lineno, col_offset, allow_dedent=True) -> list:
        """Get comments in lines before providedlines.
        
        This will mutate self._comments_read_index to mark the comment as used.
        This prevents comments from being written multiple times.
        """
        results = []
        start = self._comments_read_index
        while self._comments_read_index < len(self.comments) and self._comments_read_index < lineno:
            comment = self.comments[self._comments_read_index]
            if comment:
                if comment.dedent and not allow_dedent:
                    logging.debug("Refusing to provide comment for line %d because the comment we have is a dedent comment", lineno)
                    break
                results.append(comment)
            self._comments_read_index += 1
        if start != self._comments_read_index:
            logging.debug("Advanced comments read index to %d", self._comments_read_index)
        return results

    def override(self, **kwargs):
        """Create a new context with the provided overrides.

        For example, if you have a context A and want to produce a context
        B that is identical to A but has a different quote delimitre you would
        use A.override(quote="foo")
        """
        VALID_PARAMS = ("indent", "inline", "max_line_length", "quote", "reserved_space", "suppress_tuple_parens", "tab")
        assert all(k in VALID_PARAMS for k in kwargs.keys())
        params = {k: kwargs.get(k, getattr(self, k)) for k in VALID_PARAMS}
        return Context(format_value=self.format_value, **params)

    @property
    def remaining_line_length(self) -> int:
        return self.max_line_length - self.reserved_space

    def reserve(self, length: int) -> None:
        """Reserve the given amount of characters on the current line.

        This is essential to the proper functioning of calculations
        to honor the line length limits. This function indicates that
        some number of characters have already been used on the current
        line so that functions that calculate the formatting approach
        for the rest of the line know their constraints.
        """
        return self.override(
            reserved_space=((self.indent * len(self.tab)) + length),
        )
    def reserve_text(self, text: typing.Text) -> None:
        """Reserve some amount of text on the current line.

        Many formatting functions generate complex text on part of
        a line. Sometimes those functions may contain newlines which
        makes it difficult to use the text verbatim in reserve(). This
        function has the smarts to look for newlines to reserve the
        proper amount on the last line.
        """
        try:
            last_newline = text.rindex("\n")
        except ValueError:
            return self.reserve(len(text))
        last_line = text[last_newline+1:]
        return self.reserve(len(last_line))

    @contextlib.contextmanager
    def sub(self):
        self.indent += 1
        yield self
        self.indent -= 1

