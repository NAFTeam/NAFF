from typing import TYPE_CHECKING, Any, List

from dis_snek.models.route import Route
from dis_snek.utils.serializer import dict_filter_none

if TYPE_CHECKING:
    from dis_snek.models.snowflake import Snowflake_Type


class WebhookRequests:
    request: Any

    async def create_webhook(self, channel_id: "Snowflake_Type", name: str, avatar: Any = None) -> dict:
        """
        Create a new webhook.

        parameters:
            channel_id: The id of the channel to add this webhook to
            name: name of the webhook (1-80 characters)
            avatar: The image for the default webhook avatar
        """
        return await self.request(
            Route("POST", f"/channels/{channel_id}/webhooks"), data={"name": name, "avatar": avatar}
        )

    async def get_channel_webhooks(self, channel_id: "Snowflake_Type") -> List[dict]:
        """
        Return a list of channel webhook objects.

        parameters:
            channel_id: The id of the channel to query
        returns:
            List of webhook objects
        """
        return await self.request(Route("GET", f"/channels/{channel_id}/webhooks"))

    async def get_guild_webhooks(self, guild_id: "Snowflake_Type") -> List[dict]:
        """
        Return a list of guild webhook objects.

        parameters:
            guild_id: The id of the guild to query
        returns:
            List of webhook objects
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/webhooks"))

    async def get_webhook(self, webhook_id: "Snowflake_Type", webhook_token: str = None) -> dict:
        """
        Return the new webhook object for the given id.

        parameters:
            webhook_id: The ID of the webhook to get
            webhook_token: The token for the webhook
        returns:
            Webhook object
        """
        endpoint = f"/webhooks/{webhook_id}{f'/{webhook_token}' if webhook_token else ''}"

        return await self.request(Route("GET", endpoint))

    async def modify_webhook(
        self,
        webhook_id: "Snowflake_Type",
        name: str,
        avatar: Any,
        channel_id: "Snowflake_Type",
        webhook_token: str = None,
    ) -> dict:
        """
        Modify a webhook.

        parameters:
            name: the default name of the webhook
            avatar: image for the default webhook avatar
            channel_id: the new channel id this webhook should be moved to
            webhook_id: The ID of the webhook to modify
            webhook_token: The token for the webhook

        """
        endpoint = f"/webhooks/{webhook_id}{f'/{webhook_token}' if webhook_token else ''}"

        return await self.request(
            Route("PATCH", endpoint), data={"name": name, "avatar": avatar, "channel_id": channel_id}
        )

    async def delete_webhook(self, webhook_id: "Snowflake_Type", webhook_token: str = None) -> dict:
        """
        Delete a webhook

        parameters:
            webhook_id: The ID of the webhook to delete
            webhook_token: The token for the webhook
        returns:
            Webhook object
        """
        endpoint = f"/webhooks/{webhook_id}{f'/{webhook_token}' if webhook_token else ''}"

        return await self.request(Route("DELETE", endpoint))

    async def execute_webhook(
        self,
        webhook_id: "Snowflake_Type",
        webhook_token: str,
        payload: dict,
        wait=False,
        thread_id: "Snowflake_Type" = None,
    ) -> dict:
        """
        Execute a webhook. Basically send a message as the webhook.

        parameters:
            webhook_id: The ID of the webhook to delete
            webhook_token: The token for the webhook
            payload: The JSON payload for the message
            wait: Waits for server confirmation of message send before response
            thread_id: Send a message to the specified thread
            suffix: An optional suffix to add to the end of the endpoint address
        returns:
            The sent `message`, if `wait` is True else None
        """
        return await self.request(
            Route("POST", f"/webhooks/{webhook_id}/{webhook_token}"),
            params=dict_filter_none({"wait": "true" if wait else "false", "thread_id": thread_id}),
            data=payload,
        )

    async def get_webhook_message(
        self, webhook_id: "Snowflake_Type", webhook_token: str, message_id: "Snowflake_Type"
    ) -> dict:
        """
        Returns a previously-sent webhook message from the same token. Returns a message object on success.

        parameters:
            webhook_id: The ID of the webhook to delete
            webhook_token: The token for the webhook
            message_id: The ID of a message sent by this webhook
        returns:
            A message object on success
        """
        return await self.request(Route("GET", f"/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}"))

    async def edit_webhook_message(
        self, webhook_id: "Snowflake_Type", webhook_token: str, message_id: "Snowflake_Type", payload: dict
    ) -> dict:
        """
        Edits a previously-sent webhook message from the same token.

        parameters:
            webhook_id: The ID of the webhook to delete
            webhook_token: The token for the webhook
            message_id: The ID of a message sent by this webhook
            payload: The JSON payload for the message
        returns:
            The updated message on success
        """
        return await self.request(
            Route("PATCH", f"/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}"), data=payload
        )

    async def delete_webhook_message(
        self, webhook_id: "Snowflake_Type", webhook_token: str, message_id: "Snowflake_Type"
    ) -> None:
        """
        Delete a message that was created by the same token.

        parameters:
            webhook_id: The ID of the webhook to delete
            webhook_token: The token for the webhook
            message_id: The ID of a message sent by this webhook
        """
        return await self.request(Route("DELETE", f"/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}"))
