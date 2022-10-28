import re

from naff.models.discord import BaseChannel, BaseUser, Role

__all__ = ("mentions",)


def mentions(text: str, query: str | re.Pattern[str] | BaseUser | BaseChannel | Role) -> bool:
    """Checks whether a query is present in a text."""
    # don't use match/case witch type(query) since subclasses aren't checked
    if isinstance(query, str):
        return query in text
    elif isinstance(query, re.Pattern):
        return query.match(text) is not None
    elif isinstance(query, BaseUser):
        return (query.mention in text) or (query.username in text)
    elif isinstance(query, (BaseChannel, Role)):
        return (query.mention in text) or (query.name in text)
    else:
        return False
