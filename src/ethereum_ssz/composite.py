"""SSZ composite types: Vectors, Lists, and Containers."""

from collections.abc import Sequence
from typing import (
    Any,
    Generic,
    TypeVar,
    get_origin,
)

from ethereum_types.bytes import Bytes

# Type variable for generic container elements
T = TypeVar("T")

# SSZ constants
BYTES_PER_LENGTH_OFFSET = 4


class Vector(Generic[T], list):
    """
    Fixed-length homogeneous collection.

    In SSZ, vectors have a fixed number of elements of the same type.
    """

    length: int
    element_type: type[T]

    def __init__(
        self, elements: Sequence[T], length: int, element_type: type[T]
    ):
        """
        Initialize a Vector with fixed length.

        Args:
            elements: The elements to store
            length: The fixed length of the vector
            element_type: The type of elements
        """
        if len(elements) != length:
            raise ValueError(
                f"Vector requires exactly {length} elements, "
                f"got {len(elements)}"
            )
        super().__init__(elements)
        self.length = length
        self.element_type = element_type

    def __setitem__(self, key: int, value: T) -> None:
        """Override to maintain type safety."""
        if not isinstance(value, self.element_type):
            raise TypeError(
                f"Vector element must be of type {self.element_type.__name__}"
            )
        super().__setitem__(key, value)

    def append(self, value: T) -> None:
        """Disabled for fixed-length vectors."""
        raise NotImplementedError("Cannot append to fixed-length Vector")

    def extend(self, values: Sequence[T]) -> None:
        """Disabled for fixed-length vectors."""
        raise NotImplementedError("Cannot extend fixed-length Vector")

    def pop(self, index: int = -1) -> T:
        """Disabled for fixed-length vectors."""
        raise NotImplementedError("Cannot pop from fixed-length Vector")

    def remove(self, value: T) -> None:
        """Disabled for fixed-length vectors."""
        raise NotImplementedError("Cannot remove from fixed-length Vector")


class List(Generic[T], list):
    """
    Variable-length homogeneous collection with a maximum length.

    In SSZ, lists can have a variable number of elements up to a maximum.
    """

    max_length: int
    element_type: type[T]

    def __init__(
        self, elements: Sequence[T], max_length: int, element_type: type[T]
    ):
        """
        Initialize a List with maximum length constraint.

        Args:
            elements: The elements to store
            max_length: The maximum allowed length
            element_type: The type of elements
        """
        if len(elements) > max_length:
            raise ValueError(
                f"List exceeds maximum length {max_length}, "
                f"got {len(elements)}"
            )
        super().__init__(elements)
        self.max_length = max_length
        self.element_type = element_type

    def __setitem__(self, key: int, value: T) -> None:
        """Override to maintain type safety."""
        if not isinstance(value, self.element_type):
            raise TypeError(
                f"List element must be of type {self.element_type.__name__}"
            )
        super().__setitem__(key, value)

    def append(self, value: T) -> None:
        """Append with length check."""
        if len(self) >= self.max_length:
            raise ValueError(
                f"List would exceed maximum length {self.max_length}"
            )
        if not isinstance(value, self.element_type):
            raise TypeError(
                f"List element must be of type {self.element_type.__name__}"
            )
        super().append(value)

    def extend(self, values: Sequence[T]) -> None:
        """Extend with length check."""
        new_length = len(self) + len(values)
        if new_length > self.max_length:
            raise ValueError(
                f"List would exceed maximum length {self.max_length}"
            )
        for value in values:
            if not isinstance(value, self.element_type):
                raise TypeError(
                    f"List element must be of type "
                    f"{self.element_type.__name__}"
                )
        super().extend(values)


def is_variable_size(type_: type[Any]) -> bool:
    """
    Determine if a type is variable-size in SSZ.

    Variable-size types include:
    - bytes (when not fixed)
    - strings
    - Lists
    - Any sequence containing variable-size elements
    """
    # For now, basic implementation
    # TODO: Expand this based on actual type checking
    if type_ in (bytes, str):
        return True
    if isinstance(type_, type) and issubclass(type_, List):
        return True
    origin = get_origin(type_)
    if origin in (list, list):
        return True
    return False


def encode_composite(
    elements: Sequence[Any],
    element_types: Sequence[type[Any]],
    variable_sizes: Sequence[bool],
) -> Bytes:
    """
    Encode a composite type (Vector, List, or Container fields).

    This handles the complex offset logic for variable-size fields.

    Args:
        elements: The elements to encode
        element_types: The types of each element
        variable_sizes: Whether each element is variable-size

    Returns:
        The SSZ-encoded bytes
    """
    if not elements:
        return Bytes(b"")

    # Check if we have any variable-size elements
    has_variable = any(variable_sizes)

    if not has_variable:
        # All fixed-size: simple concatenation
        from .ssz import encode

        result = b""
        for element in elements:
            result += encode(element)
        return Bytes(result)

    # Mixed or all variable: need offset handling
    fixed_parts: list[bytes] = []
    variable_parts: list[bytes] = []

    # Calculate where variable parts start
    fixed_length = sum(
        BYTES_PER_LENGTH_OFFSET if is_var else get_fixed_size(elem_type)
        for is_var, elem_type in zip(variable_sizes, element_types)
    )

    current_offset = fixed_length

    from .ssz import encode

    for element, is_var in zip(elements, variable_sizes):
        if is_var:
            # Store offset in fixed part
            fixed_parts.append(
                current_offset.to_bytes(BYTES_PER_LENGTH_OFFSET, "little")
            )
            # Encode and store in variable part
            encoded = encode(element)
            variable_parts.append(encoded)
            current_offset += len(encoded)
        else:
            # Store value directly in fixed part
            fixed_parts.append(encode(element))

    # Concatenate fixed parts and variable parts
    result = b"".join(fixed_parts) + b"".join(variable_parts)
    return Bytes(result)


def get_fixed_size(type_: type[Any]) -> int:
    """
    Get the fixed size of a type in bytes.

    Returns the size for fixed-size types, raises for variable-size types.
    """
    from ethereum_types.numeric import U8, U32, U64, U256

    from .types import U16, U128

    # Map types to their byte sizes
    size_map = {
        bool: 1,
        U8: 1,
        U16: 2,
        U32: 4,
        U64: 8,
        U128: 16,
        U256: 32,
    }

    if type_ in size_map:
        return size_map[type_]

    # Check for FixedBytes subclasses
    from ethereum_types.bytes import FixedBytes

    if isinstance(type_, type) and issubclass(type_, FixedBytes):
        # FixedBytes has a LENGTH attribute
        return type_.LENGTH

    raise ValueError(f"Cannot determine fixed size for type {type_}")
