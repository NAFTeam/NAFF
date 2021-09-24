import re
from typing import Callable, Iterable, Optional, Any

mention_reg = re.compile(r"@(everyone|here|[!&]?[0-9]{17,20})")


def escape_mentions(content: str) -> str:
    """
    Escape mentions that could ping someone in a string

    note:
        This does not escape channel mentions as they do not ping anybody

    Args:
        content: The string to escape

    Returns:
        Processed string
    """
    return mention_reg.sub("@\u200b\\1", content)


def find(predicate: Callable, sequence: Iterable) -> Optional[Any]:
    """
    Find the first element in a sequence that matches the predicate.

    ??? Hint "Example Usage:"
        ```python
        member = find(lambda m: m.name == "UserName", guild.members)
        ```
    Args:
        predicate: A callable that returns a boolean value
        sequence: A sequence to be searched

    Returns:
        A match if found, otherwise None
    """
    for el in sequence:
        if predicate(el):
            return el
    return None
