"""
SSZ Container implementation - struct-like composites.

Containers are heterogeneous collections of named fields.
"""

from dataclasses import dataclass, fields, is_dataclass
from typing import Any, get_type_hints

from ethereum_types.bytes import Bytes32


class Container:
    """
    Base class for SSZ containers.

    Containers are fixed collections of heterogeneous fields.
    They should be defined as dataclasses with type annotations.
    """

    def __init_subclass__(cls, **kwargs):
        """Automatically make subclasses into dataclasses."""
        super().__init_subclass__(**kwargs)
        # Only apply dataclass if not already applied
        if not is_dataclass(cls):
            dataclass(cls)

    @classmethod
    def get_fields(cls) -> list[tuple[str, type]]:
        """Get the fields and their types."""
        if is_dataclass(cls):
            return [(f.name, f.type) for f in fields(cls)]
        else:
            # Fallback to type hints
            return list(get_type_hints(cls).items())

    def serialize(self) -> bytes:
        """Serialize the container to SSZ bytes."""
        from .composite import (
            encode_composite,
            is_variable_size,
        )

        field_list = self.get_fields()

        # Prepare data for composite encoding
        elements = []
        element_types = []
        variable_sizes = []

        for field_name, field_type in field_list:
            value = getattr(self, field_name)
            elements.append(value)
            element_types.append(field_type)
            variable_sizes.append(is_variable_size(field_type))

        # Use the composite encoder which handles offsets properly
        return encode_composite(elements, element_types, variable_sizes)

    def hash_tree_root(self) -> Bytes32:
        """Calculate the SSZ hash tree root of the container."""
        from .merkle import hash_tree_root, merkleize

        # Get hash tree roots of all fields
        roots = []
        for field_name, _ in self.get_fields():
            value = getattr(self, field_name)
            roots.append(hash_tree_root(value))

        # Merkleize the field roots
        return merkleize(roots)

    def __eq__(self, other):
        """Check equality based on field values."""
        if not isinstance(other, self.__class__):
            return False

        for field_name, _ in self.get_fields():
            if getattr(self, field_name) != getattr(other, field_name):
                return False

        return True

    def __repr__(self):
        """String representation of the container."""
        field_strs = []
        for field_name, _ in self.get_fields():
            value = getattr(self, field_name)
            field_strs.append(f"{field_name}={value!r}")

        return f"{self.__class__.__name__}({', '.join(field_strs)})"


def is_container(obj: Any) -> bool:
    """Check if an object is a Container."""
    return isinstance(obj, type) and issubclass(obj, Container)
