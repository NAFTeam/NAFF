from typing import Union

from dis_snek.models.timestamp import Timestamp

Snowflake_Type = Union[str, int]


class Snowflake:
    """A base object for anything with a snowflake
    Holds several methods that are likely to be used by them"""

    id: Snowflake_Type

    def __eq__(self, other):
        if hasattr(other, "id"):
            return self.id == other.id
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return int(self.id) << 32

    @property
    def created_at(self) -> Timestamp:
        """
        Returns a timestamp representing the date-time this discord object was created
        :return:
        """
        return Timestamp.fromsnowflake(self.id)
