from dis_snek.client import const
from dis_snek.client.utils import define, field

__all__ = ("LocalisedField",)


@define()
class LocalisedField:
    default_locale: str = field(default=const.default_locale)

    bulgarian: str | None = field(default=None, metadata={"locale-code": "bg"})
    chinese_china: str | None = field(default=None, metadata={"locale-code": "zh-CN"})
    chinese_taiwan: str | None = field(default=None, metadata={"locale-code": "zh-TW"})
    croatian: str | None = field(default=None, metadata={"locale-code": "hr"})
    czech: str | None = field(default=None, metadata={"locale-code": "cs"})
    danish: str | None = field(default=None, metadata={"locale-code": "da"})
    dutch: str | None = field(default=None, metadata={"locale-code": "nl"})
    english_uk: str | None = field(default=None, metadata={"locale-code": "en-GB"})
    english_us: str | None = field(default=None, metadata={"locale-code": "en-US"})
    finnish: str | None = field(default=None, metadata={"locale-code": "fi"})
    french: str | None = field(default=None, metadata={"locale-code": "fr"})
    german: str | None = field(default=None, metadata={"locale-code": "de"})
    greek: str | None = field(default=None, metadata={"locale-code": "el"})
    hindi: str | None = field(default=None, metadata={"locale-code": "hi"})
    hungarian: str | None = field(default=None, metadata={"locale-code": "hu"})
    italian: str | None = field(default=None, metadata={"locale-code": "it"})
    japanese: str | None = field(default=None, metadata={"locale-code": "ja"})
    korean: str | None = field(default=None, metadata={"locale-code": "ko"})
    lithuanian: str | None = field(default=None, metadata={"locale-code": "lt"})
    norwegian: str | None = field(default=None, metadata={"locale-code": "no"})
    polish: str | None = field(default=None, metadata={"locale-code": "pl"})
    portuguese_brazilian: str | None = field(default=None, metadata={"locale-code": "pt-BR"})
    romanian_romania: str | None = field(default=None, metadata={"locale-code": "ro"})
    russian: str | None = field(default=None, metadata={"locale-code": "ru"})
    spanish: str | None = field(default=None, metadata={"locale-code": "es-ES"})
    swedish: str | None = field(default=None, metadata={"locale-code": "sv-SE"})
    thai: str | None = field(default=None, metadata={"locale-code": "th"})
    turkish: str | None = field(default=None, metadata={"locale-code": "tr"})
    ukrainian: str | None = field(default=None, metadata={"locale-code": "uk"})
    vietnamese: str | None = field(default=None, metadata={"locale-code": "vi"})

    def __str__(self) -> str:
        return str(getattr(self, self.default_locale))

    def __bool__(self) -> bool:
        return getattr(self, self.default_locale) is not None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: default_locale={self.default_locale}, value='{self.__str__()}'>"

    @classmethod
    def converter(cls, value: str | None) -> "LocalisedField":
        if isinstance(value, LocalisedField):
            return value
        obj = cls()
        if value:
            obj.__setattr__(obj.default_locale, str(value))

        return obj

    @default_locale.validator
    def _default_locale_validator(self, _, value: str) -> None:
        try:
            getattr(self, value)
        except AttributeError:
            raise ValueError(f"`{value}` is not a supported default localisation") from None

    def as_dict(self) -> str:
        return str(self)

    def to_locale_dict(self) -> dict:
        data = {}
        for attr in self.__attrs_attrs__:
            if attr.name != self.default_locale:
                if "locale-code" in attr.metadata:
                    if val := getattr(self, attr.name):
                        data[attr.metadata["locale-code"]] = val
        return data
