"""
SSZ Union type - sum type that can hold one of several types.

Unions are tagged with a selector to indicate which type is active.
"""

from typing import Any

from ethereum_types.bytes import Bytes32


class Union:
    """
    SSZ Union type - can hold one value of several possible types.

    A Union has:
    - A selector (uint8) indicating which type is active (0-indexed)
    - A value of that type (or None for null variant)
    """

    def __init__(self, types: list[type], selector: int, value: Any):
        """
        Initialize a Union.

        Args:
            types: List of allowed types (None for null variant)
            selector: Index of the active type
            value: The value (must match types[selector])
        """
        if selector < 0 or selector >= len(types):
            raise ValueError(
                f"Invalid selector {selector} for Union with "
                f"{len(types)} types"
            )

        self.types = types
        self.selector = selector
        self.value = value

        # Validate value matches selected type
        expected_type = types[selector]
        if expected_type is None:
            if value is not None:
                raise ValueError(
                    f"Selector {selector} expects None, got {type(value)}"
                )
        elif value is None:
            raise ValueError(
                f"Selector {selector} expects {expected_type}, got None"
            )
        # For now, skip strict type checking of value

    def __eq__(self, other: Any) -> bool:
        """Check equality."""
        if not isinstance(other, Union):
            return False
        return (
            self.types == other.types
            and self.selector == other.selector
            and self.value == other.value
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Union{self.types}(selector={self.selector}, "
            f"value={self.value!r})"
        )

    def serialize(self) -> bytes:
        """
        Serialize to SSZ bytes.

        Format: selector (1 byte) || value_serialization
        """
        from .ssz import encode

        # Selector as uint8
        result = bytes([self.selector])

        # Serialize the value if not None
        if self.value is not None:
            result += encode(self.value)

        return result

    def hash_tree_root(self) -> Bytes32:
        """
        Calculate SSZ hash tree root.

        Union merkleization: h(value_root, selector_root)
        """
        from .merkle import hash, hash_tree_root

        # Get hash tree root of value (or zero for None)
        if self.value is None:
            value_root = Bytes32(b"\x00" * 32)
        else:
            value_root = hash_tree_root(self.value)

        # Selector as 32-byte chunk (little-endian)
        selector_bytes = self.selector.to_bytes(32, byteorder="little")

        # Merkleize: h(value_root, selector_chunk)
        return hash(value_root + selector_bytes)


def create_union_class(name: str, types: list[type]) -> type[Union]:
    """
    Create a Union class with specific types.

    This is a factory function to create typed Union classes,
    similar to how typing.Union works but for SSZ unions.

    Example:
        MyUnion = create_union_class("MyUnion", [uint16, uint32, None])
        u = MyUnion(selector=0, value=uint16(42))
    """

    class SpecificUnion(Union):
        def __init__(self, selector: int, value: Any):
            super().__init__(types, selector, value)

        def __repr__(self) -> str:
            type_names = []
            for t in types:
                if t is None:
                    type_names.append("None")
                else:
                    type_names.append(
                        t.__name__ if hasattr(t, "__name__") else str(t)
                    )
            return (
                f"Union[{', '.join(type_names)}](selector={self.selector}, "
                f"value={self.value!r})"
            )

    return SpecificUnion
