from typing import TYPE_CHECKING, Any, List

from dis_snek.const import MISSING
from dis_snek.models.route import Route

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


class MessageRequests:
    request: Any

    async def create_message(self, payload: dict, channel_id: "Snowflake_Type") -> dict:
        """Send a message to the specified channel."""
        return await self.request(Route("POST", f"/channels/{channel_id}/messages"), data=payload)

    async def delete_message(
        self, channel_id: "Snowflake_Type", message_id: "Snowflake_Type", reason: str = MISSING
    ) -> Any:
        """Deletes a message from the specified channel. Incomplete."""
        await self.request(Route("DELETE", f"/channels/{channel_id}/messages/{message_id}"), reason=reason)

    async def bulk_delete_messages(
        self, channel_id: "Snowflake_Type", message_ids: List["Snowflake_Type"], reason: str = MISSING
    ) -> None:
        """
        Delete multiple messages in a single request.

        parameters:
            channel_id: The id of the channel these messages are in
            message_ids: A list of message ids to delete
            reason: The reason for this action
        """
        return await self.request(
            Route("POST", f"/channels/{channel_id}/messages/bulk-delete"), data={"messages": message_ids}, reason=reason
        )

    async def get_message(self, channel_id: "Snowflake_Type", message_id: "Snowflake_Type") -> dict:
        """
        Get a specific message in the channel. Returns a message object on success.


        parameters:
            channel_id: the channel this message belongs to
            message_id: the id of the message
        returns:
            message or None
        """
        return await self.request(Route("GET", f"/channels/{channel_id}/messages/{message_id}"))

    async def pin_message(self, channel_id: "Snowflake_Type", message_id: "Snowflake_Type") -> None:
        """Pin a message to a channel

        parameters:
            channel_id: Channel to pin message to
            message_id: Message to pin
        """
        return await self.request(Route("PUT", f"/channels/{channel_id}/pins/{message_id}"))

    async def unpin_message(self, channel_id: "Snowflake_Type", message_id: "Snowflake_Type") -> None:
        """Unpin a message to a channel

        parameters:
            channel_id: Channel to unpin message to
            message_id: Message to unpin
        """
        return await self.request(Route("DELETE", f"/channels/{channel_id}/pins/{message_id}"))

    async def edit_message(
        self,
        payload: dict,
        channel_id: "Snowflake_Type",
        message_id: "Snowflake_Type",
    ) -> dict:
        """Edit an existing message

        parameters:
            payload:
            channel_id: Channel of message to edit.
            message_id: Message to edit.

        returns:
            Message object of edited message
        """
        return await self.request(Route("PATCH", f"/channels/{channel_id}/messages/{message_id}"), data=payload)

    async def crosspost_message(self, channel_id: "Snowflake_Type", message_id: "Snowflake_Type") -> dict:
        """
        Crosspost a message in a News Channel to following channels.

        parameters:
            channel_id: Channel the message is in
            message_id: The id of the message to crosspost
        returns:
            message object
        """
        return await self.request(Route("POST", f"/channels/{channel_id}/messages/{message_id}/crosspost"))
