from io import IOBase
from pathlib import Path
from typing import Optional, Union

import attr

__all__ = ["File"]


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
