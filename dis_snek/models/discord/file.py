from io import IOBase
from pathlib import Path
from typing import Optional, Union

import attr

__all__ = ["File", "open_file"]


@attr.s()
class File:
    """
    Representation of a file.

    Used to

    """

    file: Union["IOBase", "Path", str] = attr.field()
    """Location of file to send or the bytes."""
    file_name: Optional[str] = attr.field(default=None)
    """Set a filename that will be displayed when uploaded to discord. If you leave this empty, the file will be called `file` by default"""

    def open_file(self) -> "IOBase":
        if isinstance(self.file, IOBase):
            return self.file
        else:
            return open(str(self.file), "rb")


def open_file(file: Union[File, "IOBase", "Path", str]) -> IOBase:
    match file:
        case File():
            return file.open_file()
        case IOBase():
            return file
        case Path() | str():
            return open(str(file), "rb")
        case _:
            raise ValueError(f"{file} is not a valid file")
