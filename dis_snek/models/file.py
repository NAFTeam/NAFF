from typing import Optional, TYPE_CHECKING, Union
import attr

if TYPE_CHECKING:
    from io import IOBase
    from pathlib import Path


@attr.s()
class File:
    """Representation of a file. Used to"""

    file: Union["IOBase", "Path", str] = attr.field()
    """Location of file to send or the bytes."""
    file_name: Optional[str] = attr.field(default=None)
    """Set a filename that will be displayed when uploaded to discord. If you leave this empty, the file will be called `file` by default"""
