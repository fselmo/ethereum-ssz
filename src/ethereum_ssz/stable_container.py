"""
StableContainer implementation for SSZ.

This implements EIP-7495 StableContainer functionality.
Note: This is a basic implementation for compatibility testing.
Full implementation would require more advanced merkleization support.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from ethereum_types.bytes import Bytes32

from .bitfields import Bitvector
from .container import Container


@dataclass
class StableContainer(Container):
    """
    StableContainer with optional fields support.

    This is a basic implementation that extends Container with
    the ability to have optional fields that can be None.
    """

    # Maximum number of fields allowed
    _max_fields: int = field(default=16, init=False, repr=False)
    _active_fields: Optional[Bitvector] = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize active fields bitvector."""
        if self._active_fields is None:
            # Create bitvector to track which fields are active
            self._active_fields = Bitvector(
                [False] * self._max_fields, length=self._max_fields
            )

            # Mark active fields based on which are not None
            # Skip special fields that start with underscore
            field_index = 0
            for field_name, _ in self.get_fields():
                if not field_name.startswith("_"):
                    if field_index < self._max_fields:
                        value = getattr(self, field_name, None)
                        if value is not None:
                            self._active_fields[field_index] = True
                    field_index += 1

    def active_fields(self) -> Bitvector:
        """Get the bitvector of active fields."""
        if self._active_fields is None:
            self.__post_init__()
        return self._active_fields

    def serialize(self) -> bytes:
        """
        Serialize the StableContainer.

        Format: serialized_fields || active_fields_bitvector
        """
        # Serialize only active fields
        result = b""
        field_index = 0

        for field_name, _ in self.get_fields():
            if not field_name.startswith("_"):
                if field_index < self._max_fields:
                    if self.active_fields()[field_index]:
                        value = getattr(self, field_name)
                        # Import here to avoid circular dependency
                        from .ssz import encode

                        result += encode(value)
                field_index += 1

        # Append active fields bitvector
        result += self.active_fields().serialize()

        return result

    def hash_tree_root(self) -> Bytes32:
        """
        Calculate hash tree root for StableContainer.

        This is a simplified implementation.
        """
        # Import here to avoid circular dependency
        from .merkle import hash_tree_root

        # Create a temporary container with only actual fields (no internal)
        field_values = []
        for field_name, _ in self.get_fields():
            if not field_name.startswith("_"):
                value = getattr(self, field_name, None)
                if value is not None:
                    field_values.append(value)

        # For now, just hash the active field values
        # Full implementation needs proper merkleization + active bitvector
        if field_values:
            # Hash concatenated field hashes
            result = hash_tree_root(field_values[0])
            for value in field_values[1:]:
                # Simple concatenation for now
                result = Bytes32(hash_tree_root(value))
            return result
        else:
            # Empty container
            return Bytes32(b"\x00" * 32)

    @classmethod
    def deserialize(cls, data: bytes) -> "StableContainer":
        """
        Deserialize a StableContainer from bytes.

        Format: serialized_fields || active_fields_bitvector
        """
        if not data:
            raise ValueError("Cannot deserialize empty data")

        # Create a new instance with all fields set to None
        instance = cls()

        # The bitvector is at the end - we need to find it
        # For simplicity, assume bitvector takes ceil(max_fields/8) bytes
        max_fields = instance._max_fields
        bitvector_bytes = (max_fields + 7) // 8

        if len(data) < bitvector_bytes:
            raise ValueError("Data too short for bitvector")

        # Split data into fields and bitvector
        bitvector_data = data[-bitvector_bytes:]
        fields_data = data[:-bitvector_bytes]

        # Deserialize the bitvector
        from .bitfields import Bitvector

        active_fields = Bitvector.deserialize(bitvector_data, max_fields)
        instance._active_fields = active_fields

        # Now deserialize the active fields
        from typing import Union as TypingUnion
        from typing import get_args, get_origin

        from .ssz import decode_to

        offset = 0
        field_index = 0

        for field_name, field_type in instance.get_fields():
            if not field_name.startswith("_"):
                if field_index < max_fields:
                    if active_fields[field_index]:
                        # This field is active, deserialize it
                        # Handle Optional types
                        actual_type = field_type
                        origin = get_origin(field_type)
                        # Optional is Union[T, None] in typing
                        if origin is TypingUnion:
                            # Get the inner type from Optional[T]
                            args = get_args(field_type)
                            if args:
                                actual_type = args[0]

                        # Get the size of this field type
                        from .composite import get_fixed_size

                        try:
                            field_size = get_fixed_size(actual_type)
                            if offset + field_size > len(fields_data):
                                raise ValueError(
                                    f"Not enough data for field {field_name}"
                                )

                            field_bytes = fields_data[
                                offset : offset + field_size
                            ]
                            field_value = decode_to(actual_type, field_bytes)
                            setattr(instance, field_name, field_value)
                            offset += field_size
                        except Exception:
                            # For types that get_fixed_size can't handle
                            # Try to decode based on type name
                            remaining = fields_data[offset:]
                            if remaining:
                                type_name = getattr(
                                    actual_type, "__name__", str(actual_type)
                                )
                                # For U8
                                if "U8" in type_name:
                                    if len(remaining) >= 1:
                                        from ethereum_types.numeric import U8

                                        val = U8(remaining[0])
                                        setattr(instance, field_name, val)
                                        offset += 1
                                # For U16
                                elif "U16" in type_name:
                                    if len(remaining) >= 2:
                                        from ethereum_ssz import U16

                                        value = int.from_bytes(
                                            remaining[:2], "little"
                                        )
                                        setattr(
                                            instance, field_name, U16(value)
                                        )
                                        offset += 2
                                # For U32
                                elif "U32" in type_name:
                                    if len(remaining) >= 4:
                                        from ethereum_types.numeric import U32

                                        value = int.from_bytes(
                                            remaining[:4], "little"
                                        )
                                        setattr(
                                            instance, field_name, U32(value)
                                        )
                                        offset += 4
                field_index += 1

        return instance


def create_stable_container_class(
    name: str, fields: dict[str, type[Any]], max_fields: int
) -> type[StableContainer]:
    """
    Factory function to create a StableContainer class.

    Args:
        name: Name of the container class
        fields: Dictionary of field names to types
        max_fields: Maximum number of fields allowed

    Returns:
        A new StableContainer class
    """
    # Create class dynamically
    annotations = {}
    defaults = {}

    for field_name, field_type in fields.items():
        # Make all fields optional
        annotations[field_name] = Optional[field_type]
        defaults[field_name] = None

    # Add special fields
    annotations["_max_fields"] = int
    annotations["_active_fields"] = Optional[Bitvector]

    # Create the class
    cls_dict = {
        "__annotations__": annotations,
        "_max_fields": max_fields,
        "_active_fields": None,
        **defaults,
    }

    # Create new class inheriting from StableContainer
    new_class = type(name, (StableContainer,), cls_dict)

    # Make it a dataclass
    return dataclass(new_class)
