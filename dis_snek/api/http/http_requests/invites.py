from typing import Any

from dis_snek.client.const import MISSING, Absent
from ..route import Route


class InviteRequests:
    request: Any

    async def delete_invite(self, invite_code: str, reason: Absent[str] = MISSING) -> dict:
        """
        Delete the invite.

        parameters:
            invite_code: The code of the invite
            reason: The reason for the deletion
        returns:
            The deleted invite object
        """
        return await self.request(Route("DELETE", f"/invites/{invite_code}"))
