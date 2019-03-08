import collections
import contextlib
import logging

Comment = collections.namedtuple("Comment", ("srow", "scolumn", "content", "dedent"))

class Context():
    """Represents the context of the operation being serialized.

    This class is used heavily in making decisions about the application
    of whitespace.
    """
    def __init__(self, comments=None, indent=0, inline=False, max_line_length=120, quote="'", reserved_space=0, tab='\t'):
        self.comments = comments or []
        self._comments_read_index = 0
        self.indent = indent
        self.inline = inline
        self.max_line_length = max_line_length
        self.quote = quote
        self.reserved_space = reserved_space
        self.tab = tab

    def do_indent(self, lines) -> str:
        """Indent a list of lines

        Args:
            lines: a list of lines to indent and join
        Returns: The joined lines with indentation
        """
        indented_lines = [
            self.tab + line if line else ""
            for line in lines]
        return "\n".join(indented_lines)

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
        VALID_PARAMS = ("indent", "inline", "max_line_length", "quote", "reserved_space", "tab")
        assert all(k in VALID_PARAMS for k in kwargs.keys())
        params = {k: kwargs.get(k, getattr(self, k)) for k in VALID_PARAMS}
        return Context(**params)

    @property
    def remaining_line_length(self) -> int:
        return self.max_line_length - self.reserved_space

    def reserve(self, length: int) -> None:
        return self.override(
            reserved_space=((self.indent * len(self.tab)) + length),
        )

    @contextlib.contextmanager
    def sub(self):
        self.indent += 1
        yield self
        self.indent -= 1

