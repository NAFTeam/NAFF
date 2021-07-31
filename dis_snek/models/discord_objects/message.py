from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from dis_snek.models.discord_objects.user import User, Member
from dis_snek.models.enums import MessageFlags, MessageTypes, MessageActivityTypes
from dis_snek.models.snowflake import Snowflake_Type, Snowflake


@dataclass
class MessageActivity:
    type: MessageActivityTypes
    party_id: str = None


@dataclass
class MessageReference:  # todo refactor into actual class, add pointers to actual message, channel, guild objects
    message_id: Optional[int] = None
    channel_id: Optional[int] = None
    guild_id: Optional[int] = None
    fail_if_not_exists: bool = True


class Message(Snowflake):
    def __init__(self, data: dict):
        # ids
        self.id: Snowflake_Type = data["id"]
        self.channel_id: Snowflake_Type = data["channel_id"]
        self.guild_id: Optional[Snowflake_Type] = data.get("guild_id")
        self.webhook_id: Optional[Snowflake_Type] = data.get("webhook_id")
        self.application_id: Optional[Snowflake_Type] = data.get("application_id")
        self.nonce: Optional[str] = data.get("nonce")

        # objects
        self.author: User = User(data.get("author")) if "member" not in data else Member(data["member"], data["author"])
        self.application: Optional[dict] = data.get("application") if self.application_id else None
        self.thread: Optional[dict] = data.get("thread")
        self.interaction: Optional[dict] = data.get("interaction")

        # content
        self.content: str = data["content"]
        self.mentions: List = data["mentions"]
        self.mention_roles: List[Snowflake_Type] = data["mention_roles"]
        self.mention_channels: Optional[List[Snowflake_Type]] = data.get("mention_channels")
        self.mention_everyone = data["mention_everyone"]
        self.attachments: Optional[List[dict]] = data.get("attachments", [])
        self.embeds: Optional[List[dict]] = data.get("embeds", [])
        self.sticker_items: Optional[List[dict]] = data.get("sticker_items")
        self.components: Optional[List[dict]] = data.get("components")
        self.pinned: bool = data.get("pinned", False)
        self.flags: int = MessageFlags(data.get("flags", 0))
        self.tts: bool = data["tts"]
        self.type: int = MessageTypes(data["type"])

        # related content
        self.reactions: Optional[List[dict]] = data.get("reactions", [])
        self.message_reference: Optional[MessageReference] = None
        self.referenced_message: Optional[Message] = None
        self.activity: Optional[MessageActivity] = None

        if m_ref := data.get("message_reference"):
            self.message_reference = MessageReference(**m_ref)

        if ref_m := data.get("referenced_message"):
            self.referenced_message = Message(ref_m)

        if act := data.get("activity"):
            self.activity = MessageActivity(**act)

        # time
        self.sent_at: datetime = datetime.fromisoformat(data["timestamp"])
        self.edited_at: Optional[datetime] = (
            datetime.fromisoformat(data["edited_timestamp"]) if "edited_timestamp" in data else None
        )
