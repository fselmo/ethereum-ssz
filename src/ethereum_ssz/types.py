"""
Additional types for SSZ that aren't in ethereum-types.

This module provides U16 and U128 which are commonly used in SSZ
but not available in ethereum-types. These follow the exact same
pattern as ethereum-types for full compatibility.
"""

from typing import Any, ClassVar, TypeVar

from ethereum_types.numeric import FixedUnsigned

_V = TypeVar("_V", bound=FixedUnsigned)


def _max_value(class_: type[_V], bits: int) -> _V:
    """Create MAX_VALUE for a FixedUnsigned type."""
    value = object.__new__(class_)
    value._number = (2**bits) - 1  # type: ignore[misc]
    return value


class U16(FixedUnsigned):
    """
    Unsigned positive integer, which can represent `0` to `2 ** 16 - 1`,
    inclusive.
    """

    MAX_VALUE: ClassVar["U16"]
    """
    Largest value that can be represented by this integer type.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: Any
    ) -> Any:
        """
        Pydantic v2 schema that auto-converts int to U16.
        Only active when pydantic is installed.
        """
        try:
            from ethereum_types.pydantic_compat import (
                make_pydantic_schema_for_type,
            )

            return make_pydantic_schema_for_type(cls)
        except ImportError:
            # If pydantic support isn't available, just return the default
            return handler(source_type)


U16.MAX_VALUE = _max_value(U16, 16)


class U128(FixedUnsigned):
    """
    Unsigned positive integer, which can represent `0` to `2 ** 128 - 1`,
    inclusive.
    """

    MAX_VALUE: ClassVar["U128"]
    """
    Largest value that can be represented by this integer type.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: Any
    ) -> Any:
        """
        Pydantic v2 schema that auto-converts int to U128.
        Only active when pydantic is installed.
        """
        try:
            from ethereum_types.pydantic_compat import (
                make_pydantic_schema_for_type,
            )

            return make_pydantic_schema_for_type(cls)
        except ImportError:
            # If pydantic support isn't available, just return the default
            return handler(source_type)


U128.MAX_VALUE = _max_value(U128, 128)
