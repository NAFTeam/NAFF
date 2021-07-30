from typing import Optional, List

from dis_snek.models.timestamp import Timestamp


class Embed:
    def __init__(self, name: Optional[str] = None, color: Optional[int] = None, description: Optional[str] = None):
        self.name: Optional[str] = name
        self.color: Optional[int] = color
        self.description: Optional[str] = description

        self.url: Optional[str] = None
        self.timestamp: Optional[Timestamp] = None
        self.footer: Optional[dict] = None
        self.image: Optional[dict] = None
        self.thumbnail: Optional[dict] = None
        self.video: Optional[dict] = None
        self.provider: Optional[dict] = None
        self.author: Optional[dict] = None
        self.fields: Optional[List[dict]] = []

    def __setattr__(self, key, value):
        if key == "title":
            if len(value) > 256:
                raise ValueError("Title cannot exceed 256 characters")
        elif key == "description":
            if len(value) > 4096:
                raise ValueError("Description cannot exceed 4096 characters")
        super().__setattr__(key, value)

    def to_dict(self):
        """
        Convert this object into a dict ready for discord
        :return: dict
        """
        if len(self.fields) > 25:
            raise ValueError("Embeds can only hold 25 fields")
        if len(self) > 6000:
            raise ValueError(
                "Your embed is too large, please view https://discord.com/developers/docs/resources/channel#embed-limits"
            )
        data = self.__dict__
        # lets be nice and remove all the None values
        return {key: value for key, value in data.items() if value}

    def __len__(self):
        # yes i know there are far more optimal ways to write this
        # its written like this for readability
        total = 0
        total += len(self.name) if self.name else 0
        total += len(self.description) if self.description else 0
        total += len(self.footer.get("text")) if self.footer else 0
        total += len(self.author.get("name")) if self.author else 0

        for field in self.fields:
            total += len(field["name"]) + len(field["value"])
        return total

    def set_thumbnail(self, url):
        self.thumbnail = {"url": url}

    def set_image(self, url):
        self.image = {"url": url}

    def set_author(self, name: str, icon_url: Optional[str] = None, url: Optional[str] = None):
        self.author = {"name": name, "icon_url": icon_url, "url": url}

    def set_footer(self, text: str, icon_url: Optional[str] = None):
        self.footer = {"text": text, "icon_url": icon_url}

    def add_field(self, name: str, value: str, inline: bool = False):
        self.fields.append({"name": name, "value": value, "inline": inline})
