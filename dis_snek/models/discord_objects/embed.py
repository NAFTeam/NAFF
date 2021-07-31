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

import attr
from attr.validators import instance_of
from attr.validators import optional

from dis_snek.models.timestamp import Timestamp


@attr.s(slots=True)
class Embed(object):
    """Represents a discord embed object.

    :param title: the title of the embed
    :param description: the description of the embed
    :param color: the color of the embed
    """

    title: Optional[str] = attr.ib(default=None)
    description: Optional[str] = attr.ib(default=None)
    color: Optional[str] = attr.ib(default=None)

    url: Optional[str] = attr.ib(validator=optional(instance_of(str)), default=None, init=False)
    timestamp: Optional[Timestamp] = attr.ib(validator=optional(instance_of(Timestamp)), default=None, init=False)
    footer: Optional[dict] = attr.ib(default=None, init=False)
    image: Optional[dict] = attr.ib(default=None, init=False)
    thumbnail: Optional[dict] = attr.ib(default=None, init=False)
    video: Optional[dict] = attr.ib(default=None, init=False)
    provider: Optional[dict] = attr.ib(default=None, init=False)
    author: Optional[dict] = attr.ib(default=None, init=False)
    fields: list = attr.ib(factory=list)

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
        # lets be nice and remove all the None values
        return attr.asdict(self, filter=lambda k, v: v)

    def __len__(self):
        # yes i know there are far more optimal ways to write this
        # its written like this for readability
        total = 0
        total += len(self.title) if self.title else 0
        total += len(self.description) if self.description else 0
        total += len(self.footer.get("text")) if self.footer else 0
        total += len(self.author.get("title")) if self.author else 0

        for field in self.fields:
            total += len(field["title"]) + len(field["value"])
        return total

    def set_thumbnail(self, url: str) -> None:
        """
        Set the thumbnail of the embed.

        :param url: the url of the image to use
        """
        self.thumbnail = {"url": url}

    def set_image(self, url: str) -> None:
        """
        Set the image of the embed.

        :param url: the url of the image to use
        """
        self.image = {"url": url}

    def set_author(self, name: str, icon_url: Optional[str] = None) -> None:
        """
        Set the author field of the embed.

        :param name: The text to go in the title section
        :param icon_url: A url of an image to use as the icon
        """
        self.author = {"title": name, "icon_url": icon_url}

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> None:
        """
        Set the footer field of the embed.

        :param text: The text to go in the title section
        :param icon_url: A url of an image to use as the icon
        """
        self.footer = {"text": text, "icon_url": icon_url}

    def add_field(self, name: str, value: str, inline: bool = False) -> None:
        """
        Add a field to the embed.

        :param name: The title of this field
        :param value: The value in this field
        :param inline: Should this field be inline with other fields?
        """
        self.fields.append({"title": name, "value": value, "inline": inline})
        self._fields_validation("fields", self.fields)
