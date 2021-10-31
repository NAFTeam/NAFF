import attr
from typing import Any, TypeVar, Callable, Tuple, Union

# this took way too lonk to solve
# but this solution is based on https://www.attrs.org/en/stable/extending.html
# or, well, more specifically, the pyright section
# doing this in the actual file itself causes the fucntion to return as a nonetype

_T = TypeVar("_T")
def __dataclass_transform__(
    *,
    eq_default: bool = True,
    order_default: bool = False,
    kw_only_default: bool = False,
    field_descriptors: Tuple[Union[type, Callable[..., Any]], ...] = (()),
) -> Callable[[_T], _T]: ...

@__dataclass_transform__(field_descriptors=(attr.attrib, attr.field))
def define(**kwargs):
    ...