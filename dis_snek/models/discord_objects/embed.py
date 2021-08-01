"""
The MIT License (MIT).

Copyright (c) 2021 - present LordOfPolls

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
from typing import Any
from typing import Optional
from typing import List

import attr
from attr.validators import instance_of
from attr.validators import optional

from dis_snek.models.timestamp import Timestamp
from dis_snek.utils.serializer import to_dict
from dis_snek.utils.serializer import no_export_meta


@attr.s(slots=True)
class EmbedField:
    """Represents an embed field."""

    name: str = attr.ib()
    value: str = attr.ib()
    inline: bool = attr.ib(default=False)

    def __len__(self):
        return len(self.name) + len(self.value)


@attr.s(slots=True)
class EmbedAuthor:
    name: Optional[str] = attr.ib(default=None)
    url: Optional[str] = attr.ib(default=None)
    icon_url: Optional[str] = attr.ib(default=None)
    proxy_icon_url: Optional[str] = attr.ib(default=None, metadata=no_export_meta)

    def __len__(self):
        return len(self.name)


@attr.s(slots=True)
class EmbedAttachment:  # thumbnail or image or video
    url: Optional[str] = attr.ib(default=None)
    proxy_url: Optional[str] = attr.ib(default=None, metadata=no_export_meta)
    height: Optional[int] = attr.ib(default=None, metadata=no_export_meta)
    width: Optional[int] = attr.ib(default=None, metadata=no_export_meta)

    @property
    def size(self):
        return self.height, self.width


@attr.s(slots=True)
class EmbedFooter:
    text: str = attr.ib()
    icon_url: Optional[str] = attr.ib(default=None)
    proxy_icon_url: Optional[str] = attr.ib(default=None, metadata=no_export_meta)

    def __len__(self):
        return len(self.text)


@attr.s(slots=True)
class EmbedProvider:
    name: Optional[str] = attr.ib(default=None)
    url: Optional[str] = attr.ib(default=None)


@attr.s(slots=True)
class Embed(object):
    """Represents a discord embed object.

    :param title: the title of the embed
    :param description: the description of the embed
    :param color: the color of the embed
    """

    title: Optional[str] = attr.ib(default=None)
    description: Optional[str] = attr.ib(default=None, repr=False)
    color: Optional[str] = attr.ib(default=None)

    url: Optional[str] = attr.ib(validator=optional(instance_of(str)), default=None, init=False)

    timestamp: Optional[Timestamp] = attr.ib(validator=optional(instance_of(Timestamp)), default=None, init=False)

    fields: List[EmbedField] = attr.ib(factory=list, repr=False)
    author: Optional[EmbedAuthor] = attr.ib(default=None, init=False)
    thumbnail: Optional[EmbedAttachment] = attr.ib(default=None, init=False, repr=False)
    image: Optional[EmbedAttachment] = attr.ib(default=None, init=False, repr=False)
    video: Optional[EmbedAttachment] = attr.ib(default=None, init=False, repr=False, metadata=no_export_meta)
    footer: Optional[EmbedFooter] = attr.ib(default=None, init=False, repr=False)
    provider: Optional[EmbedProvider] = attr.ib(default=None, init=False, repr=False, metadata=no_export_meta)

    @title.validator
    def _name_validation(self, attribute: str, value: Any) -> None:
        """Validate the embed title."""
        if value is not None:
            if isinstance(value, str):
                if len(value) > 256:
                    raise ValueError("Title cannot exceed 256 characters")
                return
            raise TypeError("Title must be of type String")

    @description.validator
    def _description_validation(self, attribute: str, value: Any) -> None:
        """Validate the description."""
        if value is not None:
            if isinstance(value, str):
                if len(value) > 4096:
                    raise ValueError("Description cannot exceed 4096 characters")
                return
            raise TypeError("Description must be of type String")

    @fields.validator
    def _fields_validation(self, attribute: str, value: Any) -> None:
        """Validate the fields."""
        if isinstance(value, list):
            if len(value) > 25:
                raise ValueError("Embeds can only hold 25 fields")

    def to_dict(self) -> dict:
        """
        Convert this object into a dict ready for discord.

        :return: dict
        """
        self._name_validation("title", self.title)
        self._description_validation("description", self.description)
        self._fields_validation("fields", self.fields)

        if len(self) > 6000:
            raise ValueError(
                "Your embed is too large, go to https://discord.com/developers/docs/resources/channel#embed-limits"
            )

        return to_dict(self)

    def __len__(self):
        # yes i know there are far more optimal ways to write this
        # its written like this for readability
        total = 0
        total += len(self.title) if self.title else 0
        total += len(self.description) if self.description else 0
        total += len(self.footer) if self.footer else 0
        total += len(self.author) if self.author else 0

        for field in self.fields:
            total += len(field)
        return total

    def set_author(self,
                   name: str,
                   url: Optional[str] = None,
                   icon_url: Optional[str] = None,
                   ) -> None:
        """
        Set the author field of the embed.

        :param name: The text to go in the title section
        :param url: A url link to the author
        :param icon_url: A url of an image to use as the icon
        """
        self.author = EmbedAuthor(name=name, url=url, icon_url=icon_url)

    def set_thumbnail(self, url: str) -> None:
        """
        Set the thumbnail of the embed.

        :param url: the url of the image to use
        """
        self.thumbnail = EmbedAttachment(url=url)

    def set_image(self, url: str) -> None:
        """
        Set the image of the embed.

        :param url: the url of the image to use
        """
        self.image = EmbedAttachment(url=url)

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> None:
        """
        Set the footer field of the embed.

        :param text: The text to go in the title section
        :param icon_url: A url of an image to use as the icon
        """
        self.footer = EmbedFooter(text=text, icon_url=icon_url)

    def add_field(self, name: str, value: str, inline: bool = False) -> None:
        """
        Add a field to the embed.

        :param name: The title of this field
        :param value: The value in this field
        :param inline: Should this field be inline with other fields?
        """
        self.fields.append(EmbedField(name, value, inline))
        self._fields_validation("fields", self.fields)

