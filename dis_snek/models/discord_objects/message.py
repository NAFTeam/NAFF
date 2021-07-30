from datetime import datetime
from typing import Optional, List

from dis_snek.models.discord_objects.user import User, Member
from dis_snek.models.snowflake import Snowflake
from dis_snek.models.enums import MessageFlags, MessageTypes, MessageActivityTypes


class Message:
    def __init__(self, data: dict):
        # ids
        self.id: Snowflake = data["id"]
        self.channel_id: Snowflake = data["channel_id"]
        self.guild_id: Optional[Snowflake] = data.get("guild_id")
        self.webhook_id: Optional[Snowflake] = data.get("webhook_id")
        self.application_id: Optional[Snowflake] = data.get("application_id")
        self.nonce: Optional[str] = data.get("nonce")

        # objects
        self.author: User = User(data.get("author")) if "member" not in data else Member(data["member"], data["author"])
        self.application: Optional[dict] = data.get("application") if self.application_id else None
        self.thread: Optional[dict] = data.get("thread")
        self.interaction: Optional[dict] = data.get("interaction")

        # content
        self.content: str = data["content"]
        self.mentions: List = data["mentions"]
        self.mention_roles: List[Snowflake] = data["mention_roles"]
        self.mention_channels: Optional[List[Snowflake]] = data.get("mention_channels")
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
        self.message_reference: Optional[dict] = data.get("message_reference")
        self.referenced_message: Optional[Message] = (
            Message(data["referenced_message"]) if data["referenced_message"] else None
        )
        self.activity: Optional[dict] = data.get("activity")

        # time
        self.sent_at: datetime = datetime.fromisoformat(data["timestamp"])
        self.edited_at: Optional[datetime] = (
            datetime.fromisoformat(data["edited_timestamp"]) if data["edited_timestamp"] else None
        )
