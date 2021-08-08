from typing import List, Dict, Any, Optional, Union

from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake_Type


class ThreadRequests:
    request: Any

    async def join_thread(self, thread_id: Snowflake_Type) -> None:
        """
        Join a thread.

        :param thread_id: The thread to join.
        """
        return await self.request(Route("PUT", f"/channels/{thread_id}/thread-members/@me"))

    async def leave_thread(self, thread_id: Snowflake_Type) -> None:
        """
        Leave a thread.

        :param thread_id: The thread to leave.
        """
        return await self.request(Route("DELETE", f"/channels/{thread_id}/thread-members/@me"))

    async def add_thread_member(self, thread_id: Snowflake_Type, user_id: Snowflake_Type) -> None:
        """
        Add another user to a thread.

        :param thread_id: The ID of the thread
        :param user_id: The ID of the user to add
        """
        return await self.request(Route("PUT", f"/channels/{thread_id}/thread-members/@{user_id}"))

    async def remove_thread_member(self, thread_id: Snowflake_Type, user_id: Snowflake_Type) -> None:
        """
        Remove another user from a thread.

        :param thread_id: The ID of the thread
        :param user_id: The ID of the user to remove
        """
        return await self.request(Route("DELETE", f"/channels/{thread_id}/thread-members/@{user_id}"))

    async def list_thread_members(self, thread_id: Snowflake_Type) -> List[dict]:
        """
        Get a list of members in the thread.

        :param thread_id: the id of the thread
        :return: a list of member objects
        """
        return await self.request(Route("GET", f"/channels/{thread_id}/thread-members"))

    async def list_public_archived_threads(
        self, channel_id: Snowflake_Type, limit: int = None, before: Optional[Snowflake_Type] = None
    ) -> List[dict]:
        """
        Get a list of archived public threads in a channel.

        :param channel_id: The channel to get threads from
        :param limit: Optional limit of threads to
        :param before: Get threads before this snowflake
        :return: a list of threads
        """
        payload = {}
        if limit:
            payload["limit"] = limit
        if before:
            payload["before"] = before
        return await self.request(Route("GET", f"/channels/{channel_id}/threads/archived/public"), json=payload)

    async def list_private_archived_threads(
        self, channel_id: Snowflake_Type, limit: int = None, before: Optional[Snowflake_Type] = None
    ) -> List[dict]:
        """
        Get a list of archived private threads in a channel.

        :param channel_id: The channel to get threads from
        :param limit: Optional limit of threads to
        :param before: Get threads before this snowflake
        :return: a list of threads
        """
        payload = {}
        if limit:
            payload["limit"] = limit
        if before:
            payload["before"] = before
        return await self.request(Route("GET", f"/channels/{channel_id}/threads/archived/private"), json=payload)

    async def list_joined_private_archived_threads(
        self, channel_id: Snowflake_Type, limit: int = None, before: Optional[Snowflake_Type] = None
    ) -> List[dict]:
        """
        Get a list of archived private threads in a channel that you have joined.

        :param channel_id: The channel to get threads from
        :param limit: Optional limit of threads to
        :param before: Get threads before this snowflake
        :return: a list of threads
        """
        payload = {}
        if limit:
            payload["limit"] = limit
        if before:
            payload["before"] = before
        return await self.request(
            Route("GET", f"/channels/{channel_id}/users/@me/threads/archived/private"), json=payload
        )

    async def list_active_threads(self, guild_id: Snowflake_Type) -> List[dict]:
        """
        List active threads within a guild.

        :param guild_id: the guild id to get threads from
        :return: A list of active threads
        """
        return await self.request(Route("GET", f"/guilds/{guild_id}/threads/active"))

    async def create_thread(
        self,
        channel_id: Snowflake_Type,
        name: str,
        auto_archive_duration: int = 60,
        thread_type: int = 11,
        message_id: Optional[Snowflake_Type] = None,
    ) -> dict:
        """
        Create a thread in the given channel.
        Can either create a thread with or without a message

        :param channel_id: The ID of the channel to create this thread in
        :param name: The name of the thread
        :param auto_archive_duration: duration in minutes to automatically archive the thread after recent activity,
            can be set to: 60, 1440, 4320, 10080
        :param thread_type: The type of thread, defaults to public. ignored if creating thread from a message
        :param message_id: An optional message to create a thread from.
        :return: The created thread
        """
        payload = dict(name=name, auto_archive_duration=auto_archive_duration)
        if message_id:
            return await self.request(
                Route("POST", f"/channels/{channel_id}/messages/{message_id}/threads"), json=payload
            )
        else:
            payload["type"] = thread_type
            return await self.request(Route("POST", f"/channels/{channel_id}/threads"), json=payload)
