import functools
import inspect
import re
from typing import Callable, Iterable, List, Optional, Any

__all__ = ["escape_mentions", "find", "find_all", "get", "get_all", "wrap_partial", "get_parameters"]

mention_reg = re.compile(r"@(everyone|here|[!&]?[0-9]{17,20})")


def escape_mentions(content: str) -> str:
    """
    Escape mentions that could ping someone in a string.

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


def find_all(predicate: Callable, sequence: Iterable) -> List[Any]:
    """
    Find all elements in a sequence that match the predicate.

    ??? Hint "Example Usage:"
        ```python
        members = find_all(lambda m: m.name == "UserName", guild.members)
        ```
    Args:
        predicate: A callable that returns a boolean value
        sequence: A sequence to be searched

    Returns:
        A list of matches

    """
    return [el for el in sequence if predicate(el)]


def get(sequence: Iterable, **kwargs: Any) -> Optional[Any]:
    """
    Find the first element in a sequence that matches all attrs.

    ??? Hint "Example Usage:"
        ```python
        channel = get(guild.channels, nsfw=False, category="General")
        ```

    Args:
        sequence: A sequence to be searched
        kwargs: Keyword arguments to search the sequence for

    Returns:
        A match if found, otherwise None
    """
    if not kwargs:
        return sequence[0]

    for el in sequence:
        if any(not hasattr(el, attr) for attr in kwargs.keys()):
            continue
        if all(getattr(el, attr) == value for attr, value in kwargs.items()):
            return el
    return None


def get_all(sequence: Iterable, **kwargs: Any) -> List[Any]:
    """
    Find all elements in a sequence that match all attrs.

    ??? Hint "Example Usage:"
        ```python
        channels = get_all(guild.channels, nsfw=False, category="General")
        ```

    Args:
        sequence: A sequence to be searched
        kwargs: Keyword arguments to search the sequence for

    Returns:
        A list of matches
    """
    if not kwargs:
        return sequence

    matches = []
    for el in sequence:
        if any(not hasattr(el, attr) for attr in kwargs.keys()):
            continue
        if all(getattr(el, attr) == value for attr, value in kwargs.items()):
            matches.append(el)
    return matches


def wrap_partial(obj, cls) -> Callable:
    """
    🎁 Wraps a commands callback objects into partials.

    !!! note
        This is used internally, you shouldn't need to use this function

    Args:
        obj: The command object to process
        cls: The class to use in partials

    Returns:
        The original command object with its callback methods wrapped

    """
    if isinstance(obj.callback, functools.partial):
        return obj
    if "_no_wrap" not in getattr(obj.callback, "__name__", ""):
        obj.callback = functools.partial(obj.callback, cls)

    if getattr(obj, "error_callback", None):
        obj.error_callback = functools.partial(obj.error_callback, cls)
    if getattr(obj, "pre_run_callback", None):
        obj.pre_run_callback = functools.partial(obj.pre_run_callback, cls)
    if getattr(obj, "post_run_callback", None):
        obj.post_run_callback = functools.partial(obj.post_run_callback, cls)
    if getattr(obj, "autocomplete_callbacks", None):
        obj.autocomplete_callbacks = {k: functools.partial(v, cls) for k, v in obj.autocomplete_callbacks.items()}
    if getattr(obj, "subcommands", None):
        obj.subcommands = {k: wrap_partial(v, cls) for k, v in obj.subcommands.items()}

    return obj


def get_parameters(callback: Callable) -> dict[str, inspect.Parameter]:
    return {p.name: p for p in inspect.signature(callback).parameters.values()}
