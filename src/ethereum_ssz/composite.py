"""SSZ composite types: Vectors, Lists, and Containers."""

from collections.abc import Sequence
from typing import (
    Any,
    Generic,
    TypeVar,
    get_origin,
)
from typing import (
    Union as PyUnion,
)

from ethereum_types.bytes import Bytes

# Type variable for generic container elements
T = TypeVar("T")

# SSZ constants
BYTES_PER_LENGTH_OFFSET = 4


class Vector(Generic[T], list[T]):
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

    def __setitem__(self, key: int, value: T) -> None:  # type: ignore[override]
        """Override to maintain type safety."""
        if not isinstance(value, self.element_type):
            raise TypeError(
                f"Vector element must be of type {self.element_type.__name__}"
            )
        super().__setitem__(key, value)

    def append(self, value: T) -> None:
        """Disabled for fixed-length vectors."""
        raise NotImplementedError("Cannot append to fixed-length Vector")

    def extend(self, values: Sequence[T]) -> None:  # type: ignore[override]
        """Disabled for fixed-length vectors."""
        raise NotImplementedError("Cannot extend fixed-length Vector")

    def pop(self, index: int = -1) -> T:  # type: ignore[override]
        """Disabled for fixed-length vectors."""
        raise NotImplementedError("Cannot pop from fixed-length Vector")

    def remove(self, value: T) -> None:
        """Disabled for fixed-length vectors."""
        raise NotImplementedError("Cannot remove from fixed-length Vector")


class List(Generic[T], list[T]):
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

    def __setitem__(self, key: int, value: T) -> None:  # type: ignore[override]
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

    def extend(self, values: Sequence[T]) -> None:  # type: ignore[override]
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


def is_variable_size(type_: PyUnion[type[Any], Any]) -> bool:
    """
    Determine if a type is variable-size in SSZ.

    Variable-size types include:
    - bytes (when not fixed)
    - strings
    - Lists
    - Any sequence containing variable-size elements
    - Containers with variable-size fields
    """
    # Handle Container instances directly
    from .container import Container

    if isinstance(type_, Container):
        # A container instance is variable if any of its fields are variable
        for field_name, field_type in type_.get_fields():
            value = getattr(type_, field_name)
            if value is not None:
                if is_variable_size(
                    value
                    if isinstance(value, (Vector, List, Container))
                    else type(value)
                ):
                    return True
            elif is_variable_size(field_type):
                return True
        return False

    # Handle List instances directly (variable size)
    if isinstance(type_, List):
        return True

    # Handle Vector instances directly (ALWAYS fixed size in SSZ)
    # Even if elements are variable, the Vector itself is fixed
    if isinstance(type_, Vector):
        return False

    # Check for generic list origin first (list[T] syntax)
    origin = get_origin(type_)
    if origin is list:
        return True

    # Handle instances vs types
    if not isinstance(type_, type):
        # If it's an instance, get its type
        type_ = type(type_)

    # Check for basic variable types
    if type_ in (bytes, str):
        return True

    # Check for List types (class) - use try/except for non-class types
    try:
        if issubclass(type_, List):
            return True
    except TypeError:
        pass

    # Check for Vector types (class - always fixed size)
    try:
        if issubclass(type_, Vector):
            return False
    except TypeError:
        pass

    # Check for Container types with variable fields
    from .container import Container

    try:
        if issubclass(type_, Container):
            # A container is variable if any of its fields are variable
            for _field_name, field_type in type_.get_fields():
                if is_variable_size(field_type):
                    return True
            return False
    except TypeError:
        pass

    return False


def encode_composite(
    elements: Sequence[Any],
    element_types: Sequence[PyUnion[type[Any], Any]],
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


def get_fixed_size(type_: PyUnion[type[Any], Any]) -> int:
    """
    Get the fixed size of a type in bytes.

    Returns the size for fixed-size types, raises for variable-size types.
    """
    # Handle Container instances first
    from .container import Container

    if isinstance(type_, Container):
        # For Container instances, check if it's variable
        if is_variable_size(type_):
            raise ValueError(
                f"Container {type_.__class__.__name__} is variable size"
            )
        # Calculate total size of all fixed fields
        total_size = 0
        for field_name, field_type in type_.get_fields():
            value = getattr(type_, field_name)
            if value is not None:
                total_size += get_fixed_size(
                    value
                    if isinstance(value, (Vector, List, Container))
                    else type(value)
                )
            else:
                total_size += get_fixed_size(field_type)
        return total_size

    # Handle Vector instances
    if isinstance(type_, Vector):
        # Vectors are tricky - fixed-size from container's perspective
        # but their actual byte size depends on whether elements are variable
        # For now, we need to actually encode it to get the size
        # This is inefficient but correct
        from .ssz import encode

        encoded = encode(type_)
        return len(encoded)

    # Handle List instances (they are variable size)
    if isinstance(type_, List):
        raise ValueError("Lists are variable size")

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

    # Handle instances vs types
    if not isinstance(type_, type):
        # If it's an instance, get its type
        type_ = type(type_)

    # Check for FixedBytes subclasses
    from ethereum_types.bytes import FixedBytes

    if issubclass(type_, FixedBytes):
        # FixedBytes has a LENGTH attribute
        return type_.LENGTH

    # Check for Vector types (class, not instance)
    if isinstance(type_, type) and issubclass(type_, Vector):
        # For Vector class without instance, we can't determine size
        raise ValueError(
            "Cannot determine fixed size for Vector class without instance"
        )

    # Check for Container types (class)
    if isinstance(type_, type) and issubclass(type_, Container):
        # Check if container is variable-size
        if is_variable_size(type_):
            raise ValueError(f"Container {type_.__name__} is variable size")
        # A container is fixed-size if all its fields are fixed-size
        # Calculate total size of all fixed fields
        total_size = 0
        for _field_name, field_type in type_.get_fields():
            total_size += get_fixed_size(field_type)
        return total_size

    raise ValueError(f"Cannot determine fixed size for type {type_}")
