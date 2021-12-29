from typing import Any
from urllib.parse import urlencode

from dis_snek.const import MISSING, Absent
from dis_snek.models.route import Route
from dis_snek.models.snowflake import Snowflake_Type
from dis_snek.utils.serializer import dict_filter_missing


class ScheduledEventsRequests:
    request: Any

    async def list_schedules_events(self, guild_id: "Snowflake_Type", with_user_count: bool = False) -> list[dict]:
        """
        Get the scheduled events for a guild.

        parameters:
            guild_id: The guild to get scheduled events from
            with_user_count: Whether to include the user count in the response
        returns:
            List of Scheduled Events or None
        """
        return await self.request(
            Route("GET", f"/guilds/{guild_id}/scheduled-events?with_user_count={with_user_count}")
        )

    async def get_scheduled_event(
        self, guild_id: "Snowflake_Type", scheduled_event_id: "Snowflake_Type", with_user_count: bool = False
    ) -> dict:
        """
        Get a scheduled event for a guild.

        parameters:
            guild_id: The guild to get scheduled event from
            with_user_count: Whether to include the user count in the response
        returns:
            Scheduled Event or None
        """
        return await self.request(
            Route("GET", f"/guilds/{guild_id}/scheduled-events/{scheduled_event_id}?with_user_count={with_user_count}")
        )

    async def create_scheduled_event(
        self,
        guild_id: "Snowflake_Type",
        payload: dict,
        reason: Absent[str] = MISSING,
    ) -> dict:
        """
        Create a scheduled event for a guild.

        parameters:
            guild_id: The guild to create scheduled event from
            payload: The scheduled event payload
            reason: The reason to be displayed in audit logs
        returns:
            Scheduled Event or None
        """
        return await self.request(Route("POST", f"/guilds/{guild_id}/scheduled-events"), data=payload, reason=reason)

    async def modify_scheduled_event(
        self,
        guild_id: "Snowflake_Type",
        scheduled_event_id: "Snowflake_Type",
        payload: dict,
        reason: Absent[str] = MISSING,
    ) -> dict:
        """
        Modify a scheduled event for a guild.

        parameters:
            guild_id: The guild to modify scheduled event from
            scheduled_event_id: The scheduled event to modify
            payload: The payload to modify the scheduled event with
            reason: The reason to be displayed in audit logs
        returns:
            Scheduled Event or None
        """
        return await self.request(
            Route("PATCH", f"/guilds/{guild_id}/scheduled-events/{scheduled_event_id}"), data=payload, reason=reason
        )

    async def delete_scheduled_event(
        self,
        guild_id: "Snowflake_Type",
        scheduled_event_id: "Snowflake_Type",
        reason: Absent[str] = MISSING,
    ) -> dict:
        """
        Delete a scheduled event for a guild.

        parameters:
            guild_id: The guild to delete scheduled event from
            scheduled_event_id: The scheduled event to delete
            reason: The reason to be displayed in audit logs
        returns:
            Scheduled Event or None
        """
        return await self.request(
            Route("DELETE", f"/guilds/{guild_id}/scheduled-events/{scheduled_event_id}"), reason=reason
        )

    async def get_scheduled_event_users(
        self,
        guild_id: "Snowflake_Type",
        scheduled_event_id: "Snowflake_Type",
        limit: int = 100,
        with_member: bool = False,
        before: "Snowflake_Type" = MISSING,
        after: "Snowflake_Type" = MISSING,
    ) -> list[dict]:
        """
        Get the users for a scheduled event.

        parameters:
            guild_id: The guild to get scheduled event users from
            scheduled_event_id: The scheduled event to get users from
            limit: how many users to receive from the event
            with_member: include guild member data if it exists
            before: consider only users before given user id
            after: consider only users after given user id
        returns:
            List of Scheduled Event Users or None
        """
        query_params = urlencode(
            dict_filter_missing(dict(limit=limit, with_member=with_member, before=before, after=after))
        )
        return await self.request(
            Route(
                "GET",
                f"/guilds/{guild_id}/scheduled-events/{scheduled_event_id}/users?{query_params}",
            )
        )
