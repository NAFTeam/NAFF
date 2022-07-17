from naff import Context, Snowflake_Type, User, Client, BaseChannel, Message
from tests.consts import SAMPLE_USER_DATA, SAMPLE_CHANNEL_DATA, SAMPLE_MESSAGE_DATA

__all__ = ("generate_dummy_context",)


def generate_dummy_context(
    user_id: Snowflake_Type | None = None,
    channel_id: Snowflake_Type | None = None,
    guild_id: Snowflake_Type | None = None,
    message_id: Snowflake_Type | None = None,
    dm: bool = False,
    client: Client | None = None,
) -> Context:
    """Generates a dummy context for testing."""
    client = Client() if client is None else client
    author = SAMPLE_USER_DATA()
    channel = SAMPLE_CHANNEL_DATA()
    message = SAMPLE_MESSAGE_DATA()

    if user_id is not None:
        author["id"] = user_id

    if message_id is not None:
        message["id"] = message_id

    if channel_id is not None:
        channel["id"] = channel_id
        message["channel_id"] = channel_id

    if guild_id is not None:
        channel["guild_id"] = guild_id

    if dm:
        channel["guild_id"] = None
        guild_id = None

    return Context(
        author=User.from_dict(author, client),
        channel=BaseChannel.from_dict(channel, client),
        guild_id=guild_id,
        message=Message.from_dict(message, client),
        client=client,
    )
