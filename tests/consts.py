"""
A bunch of fake API responses for testing.

Because the library has a habit of mangling the data (_process_dict), these are functions that will always return clean responses.
"""

import discord_typings

__all__ = ("SAMPLE_DM_DATA", "SAMPLE_GUILD_DATA", "SAMPLE_USER_DATA")


def SAMPLE_USER_DATA() -> discord_typings.UserData:
    return {
        "id": "123456789012345678",
        "username": "test_user",
        "discriminator": "1234",
        "avatar": "",
    }


def SAMPLE_DM_DATA() -> discord_typings.DMChannelData:
    return {
        "id": "123456789012345679",
        "type": 1,
        "last_message_id": None,
        "recipients": [SAMPLE_USER_DATA()],
    }


def SAMPLE_GUILD_DATA() -> discord_typings.GuildData:
    return {
        "id": "123456789012345670",
        "name": "test_guild",
        "icon": "",
        "splash": "",
        "discovery_splash": "",
        "owner_id": "123456789012345678",
        "afk_channel_id": None,
        "afk_timeout": 0,
        "verification_level": 0,
        "default_message_notifications": 0,
        "explicit_content_filter": 0,
        "roles": [],
        "emojis": [],
        "features": [],
        "mfa_level": 0,
        "application_id": None,
        "system_channel_id": None,
        "system_channel_flags": 0,
        "rules_channel_id": None,
        "vanity_url_code": None,
        "description": None,
        "banner": None,
        "premium_tier": 0,
        "preferred_locale": "en-US",
        "public_updates_channel_id": None,
        "nsfw_level": 0,
        "stickers": [],
        "premium_progress_bar_enabled": False,
    }
