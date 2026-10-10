import re

_LINE = r"^(?P<pre>[ \t]*(?:-[ \t]+)?(?:image|value):[ \t]*)(?P<val>\"[^\"]*\"|\S+)(?P<post>[ \t]+#[ \t]*fareops:{key}[ \t]*)$"


def set_marker(text: str, key: str, value: str, quote: bool = False) -> tuple[str, int]:
    """Replace the value on every line tagged '# fareops:<key>'. Returns (new_text, matches)."""
    pattern = re.compile(_LINE.format(key=re.escape(key)), re.MULTILINE)
    new_val = f'"{value}"' if quote else value
    new_text, n = pattern.subn(lambda m: f"{m['pre']}{new_val}{m['post']}", text)
    return new_text, n


def get_marker(text: str, key: str) -> str | None:
    m = re.search(_LINE.format(key=re.escape(key)), text, re.MULTILINE)
    return m["val"].strip('"') if m else None
