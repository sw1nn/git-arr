"""
Miscellaneous utilities.

These are mostly used in templates, for presentation purposes.
"""

try:
    import pygments  # type: ignore
    from pygments import highlight  # type: ignore
    from pygments import lexers  # type: ignore
    from pygments.formatters import HtmlFormatter  # type: ignore

    _html_formatter = HtmlFormatter(
        encoding="utf-8",
        cssclass="source_code",
        linenos="table",
        anchorlinenos=True,
        lineanchors="line",
    )
except ImportError:
    pygments = None

try:
    import markdown  # type: ignore
    import markdown.treeprocessors  # type: ignore
except ImportError:
    markdown = None

import base64
import difflib
import functools
import html
import mimetypes
import re
import string
import inspect
import sys
import time
import os
import os.path

import git


def shorten(s: str, width=60):
    if len(s) < 60:
        return s
    return s[:57] + "..."


@functools.lru_cache
def can_colorize(s: str):
    """True if we can colorize the string, False otherwise."""
    if pygments is None:
        return False

    # Pygments can take a huge amount of time with long files, or with very
    # long lines; these are heuristics to try to avoid those situations.
    if len(s) > (512 * 1024):
        return False

    # If any of the first 5 lines is over 300 characters long, don't colorize.
    start = 0
    for i in range(5):
        pos = s.find("\n", start)
        if pos == -1:
            break

        if pos - start > 300:
            return False
        start = pos + 1

    return True


def can_markdown(repo: git.Repo, fname: str):
    """True if we can process file through markdown, False otherwise."""
    if markdown is None:
        return False

    if not repo.info.embed_markdown:
        return False

    return fname.endswith(".md")


def can_embed_image(repo, fname):
    """True if we can embed image file in HTML, False otherwise."""
    if not repo.info.embed_images:
        return False

    return ("." in fname) and (
        fname.split(".")[-1].lower() in ["jpg", "jpeg", "png", "gif"]
    )


@functools.lru_cache
def colorize_diff(s: str) -> str:
    lexer = lexers.DiffLexer(encoding="utf-8")
    formatter = HtmlFormatter(encoding="utf-8", cssclass="source_code")

    return highlight(s, lexer, formatter)


def _compute_line_diff(old_line: str, new_line: str):
    """
    Compute character-level diff between two lines.
    Returns (old_parts, new_parts) where each is a list of (text, is_changed).
    """
    matcher = difflib.SequenceMatcher(None, old_line, new_line)
    old_parts = []
    new_parts = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            old_parts.append((old_line[i1:i2], False))
            new_parts.append((new_line[j1:j2], False))
        elif tag == 'replace':
            old_parts.append((old_line[i1:i2], True))
            new_parts.append((new_line[j1:j2], True))
        elif tag == 'delete':
            old_parts.append((old_line[i1:i2], True))
        elif tag == 'insert':
            new_parts.append((new_line[j1:j2], True))

    return old_parts, new_parts


def _render_line_parts(parts, line_type):
    """
    Render line parts with appropriate highlighting.
    line_type: 'removed' or 'added'
    """
    result = []
    for text, is_changed in parts:
        if not text:
            continue
        escaped = html.escape(text)
        if is_changed:
            result.append(f'<span class="diff-{line_type}-highlight">{escaped}</span>')
        else:
            result.append(escaped)
    return ''.join(result)


@functools.lru_cache
def colorize_diff_enhanced(s: str) -> str:
    """
    Enhanced diff rendering with character-level change highlighting.
    Similar to delta's output style.
    """
    lines = s.split('\n')
    output = []
    output.append('<div class="enhanced-diff">')

    i = 0
    while i < len(lines):
        line = lines[i]

        # Diff header lines (diff --git, index, +++, ---)
        if line.startswith('diff --git') or line.startswith('index ') or \
           line.startswith('---') or line.startswith('+++'):
            output.append(f'<div class="diff-header">{html.escape(line)}</div>')
            i += 1
            continue

        # Hunk headers (@@ ... @@)
        if line.startswith('@@'):
            # Extract hunk header and any trailing context
            match = re.match(r'^(@@[^@]*@@)(.*)', line)
            if match:
                hunk_info, context = match.groups()
                output.append(f'<div class="diff-hunk-header">')
                output.append(f'<span class="diff-hunk-info">{html.escape(hunk_info)}</span>')
                if context:
                    output.append(f'<span class="diff-hunk-context">{html.escape(context)}</span>')
                output.append('</div>')
            else:
                output.append(f'<div class="diff-hunk-header">{html.escape(line)}</div>')
            i += 1
            continue

        # Check for modified line pairs (- followed by +)
        if line.startswith('-') and not line.startswith('---') and \
           i + 1 < len(lines) and lines[i + 1].startswith('+') and \
           not lines[i + 1].startswith('+++'):

            old_line = line[1:]  # Remove leading '-'
            new_line = lines[i + 1][1:]  # Remove leading '+'

            # Compute character-level diff
            old_parts, new_parts = _compute_line_diff(old_line, new_line)

            # Render both lines with inline highlighting
            output.append('<div class="diff-line diff-line-removed">')
            output.append('<span class="diff-marker">-</span>')
            output.append(_render_line_parts(old_parts, 'removed'))
            output.append('</div>')

            output.append('<div class="diff-line diff-line-added">')
            output.append('<span class="diff-marker">+</span>')
            output.append(_render_line_parts(new_parts, 'added'))
            output.append('</div>')

            i += 2
            continue

        # Regular removed line
        if line.startswith('-') and not line.startswith('---'):
            output.append('<div class="diff-line diff-line-removed">')
            output.append('<span class="diff-marker">-</span>')
            output.append(html.escape(line[1:]))
            output.append('</div>')
            i += 1
            continue

        # Regular added line
        if line.startswith('+') and not line.startswith('+++'):
            output.append('<div class="diff-line diff-line-added">')
            output.append('<span class="diff-marker">+</span>')
            output.append(html.escape(line[1:]))
            output.append('</div>')
            i += 1
            continue

        # Context line (unchanged)
        if line.startswith(' '):
            output.append('<div class="diff-line diff-line-context">')
            output.append('<span class="diff-marker"> </span>')
            output.append(html.escape(line[1:]))
            output.append('</div>')
            i += 1
            continue

        # Other lines (shouldn't normally happen in well-formed diffs)
        if line:
            output.append(f'<div class="diff-line">{html.escape(line)}</div>')
        i += 1

    output.append('</div>')
    return '\n'.join(output)


@functools.lru_cache
def colorize_blob(fname, s: str) -> str:
    try:
        lexer = lexers.guess_lexer_for_filename(fname, s, encoding="utf-8")
    except lexers.ClassNotFound:
        # Only try to guess lexers if the file starts with a shebang,
        # otherwise it's likely a text file and guess_lexer() is prone to
        # make mistakes with those.
        lexer = lexers.TextLexer(encoding="utf-8")
        if s.startswith("#!"):
            try:
                lexer = lexers.guess_lexer(s[:80], encoding="utf-8")
            except lexers.ClassNotFound:
                pass

    return highlight(s, lexer, _html_formatter)


def embed_image_blob(fname: str, image_data: bytes) -> str:
    mimetype = mimetypes.guess_type(fname)[0]
    b64img = base64.b64encode(image_data).decode("ascii")
    return '<img style="max-width:100%;" src="data:{0};base64,{1}" />'.format(
        mimetype, b64img
    )


@functools.lru_cache
def is_binary(b: bytes):
    # Git considers a blob binary if NUL in first ~8KB, so do the same.
    return b"\0" in b[:8192]


@functools.lru_cache
def hexdump(s: bytes):
    graph = string.ascii_letters + string.digits + string.punctuation + " "
    b = s.decode("latin1")
    offset = 0
    while b:
        t = b[:16]
        hexvals = ["%.2x" % ord(c) for c in t]
        text = "".join(c if c in graph else "." for c in t)
        yield offset, " ".join(hexvals[:8]), " ".join(hexvals[8:]), text
        offset += 16
        b = b[16:]


if markdown:

    class RewriteLocalLinks(markdown.treeprocessors.Treeprocessor):
        """Rewrites relative links to files, to match git-arr's links.

        A link of "[example](a/file.md)" will be rewritten such that it links to
        "a/f=file.md.html".

        Note that we're already assuming a degree of sanity in the HTML, so we
        don't re-check that the path is reasonable.
        """

        def run(self, root):
            for child in root:
                if child.tag == "a":
                    self.rewrite_href(child)

                # Continue recursively.
                self.run(child)

        def rewrite_href(self, tag):
            """Rewrite an <a>'s href."""
            target = tag.get("href")
            if not target:
                return
            if "://" in target or target.startswith("/"):
                return

            head, tail = os.path.split(target)
            new_target = os.path.join(head, "f=" + tail + ".html")
            tag.set("href", new_target)

    class RewriteLocalLinksExtension(markdown.Extension):
        def extendMarkdown(self, md):
            md.treeprocessors.register(
                RewriteLocalLinks(), "RewriteLocalLinks", 1000
            )

    _md_extensions = [
        "markdown.extensions.fenced_code",
        "markdown.extensions.tables",
        RewriteLocalLinksExtension(),
    ]

    @functools.lru_cache
    def markdown_blob(s: str) -> str:
        return markdown.markdown(s, extensions=_md_extensions)

else:

    @functools.lru_cache
    def markdown_blob(s: str) -> str:
        raise RuntimeError("markdown_blob() called without markdown support")


def log_timing(*log_args):
    "Decorator to log how long a function call took."
    if not os.environ.get("GIT_ARR_DEBUG"):
        return lambda f: f

    def log_timing_decorator(f):
        argspec = inspect.getfullargspec(f)
        idxs = [argspec.args.index(arg) for arg in log_args]

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = f(*args, **kwargs)
            end = time.time()

            f_args = [args[i] for i in idxs]
            sys.stderr.write(
                "%.4fs  %s %s\n" % (end - start, f.__name__, " ".join(f_args))
            )
            return result

        return wrapper

    return log_timing_decorator
