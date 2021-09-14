HTTP
====

This page outlines how snek interacts with Discord's http API.

.. note:: For normal use, you should be using methods found in ``client.py``, as those are processed into objects, meanwhile all methods here will return json data.

HTTP Client
___________

.. automodule:: dis_snek.http_client
   :members:
   :exclude-members: DiscordClientWebSocketResponse

Supported Endpoints
___________________

This is a list of endpoints that are supported by dis-snek.
These methods are organised in sub-files of ``dis-snek/http_requests`` according to where they best fit.

.. note:: The majority of the time you should never need to interact with these. They're only documented for people contributing to dis-snek.

.. automodule:: dis_snek.http_requests
   :members: BotRequests, ChannelRequests, EmojiRequests, GuildRequests, InteractionRequests, MemberRequests, MessageRequests, ReactionRequests, StickerRequests, ThreadRequests, UserRequests, WebhookRequests
   :undoc-members:
