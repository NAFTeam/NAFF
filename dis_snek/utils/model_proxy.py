from typing import TYPE_CHECKING, Iterable
from inspect import isasyncgen
from functools import partial

from dis_snek.utils.proxy import CacheProxy, CacheView

if TYPE_CHECKING:
    from dis_snek.client import Snake
    from dis_snek.models.snowflake import Snowflake_Type


def _get_proxy_class(id, method, client):
    # client is for future

    # todo None

    if isinstance(id, Iterable) or isasyncgen(id):
        proxy_cls = CacheView
    else:
        proxy_cls = CacheProxy
    # print("PICKED", proxy_cls, "FOR", id)
    return proxy_cls(id, method)


# todo snowflake id typevar for lists

def proxy_guild(client: "Snake", guild_id: "Snowflake_Type"):
    method = client.cache.get_guild
    return _get_proxy_class(guild_id, method, client)


def proxy_channel(client: "Snake", channel_id: "Snowflake_Type"):
    method = client.cache.get_channel
    return _get_proxy_class(channel_id, method, client)


def proxy_dm_channel(client: "Snake", user_id: "Snowflake_Type"):
    method = client.cache.get_dm_channel
    return _get_proxy_class(user_id, method, client)


def proxy_message(client: "Snake", channel_id: "Snowflake_Type", message_id: "Snowflake_Type"):
    method = partial(client.cache.get_message, channel_id)
    return _get_proxy_class(message_id, method, client)


def proxy_user(client: "Snake", user_id: "Snowflake_Type"):
    method = client.cache.get_user
    return _get_proxy_class(user_id, method, client)


def proxy_member(client: "Snake", guild_id: "Snowflake_Type", user_id: "Snowflake_Type"):
    method = partial(client.cache.get_member, guild_id)
    return _get_proxy_class(user_id, method, client)


def proxy_role(client: "Snake", guild_id: "Snowflake_Type", role_id: "Snowflake_Type"):
    method = partial(client.cache.get_role, guild_id)
    return _get_proxy_class(role_id, method, client)
