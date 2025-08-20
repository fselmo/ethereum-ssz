"""
SSZ Container implementation - struct-like composites.

Containers are heterogeneous collections of named fields.
"""

from typing import Any
from typing import Union as PyUnion

from ethereum_types.bytes import Bytes32
from pydantic import BaseModel, ConfigDict


class Container(BaseModel):
    """
    Base class for SSZ containers.

    Containers are fixed collections of heterogeneous fields.
    They are now Pydantic models with type annotations.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Allow ethereum-types
        validate_assignment=True,  # Validate on assignment
        extra="forbid",  # Don't allow extra fields
    )

    @classmethod
    def get_fields(cls) -> list[tuple[str, type]]:
        """Get the fields and their types."""
        # Use Pydantic's model_fields
        return [
            (name, field.annotation)
            for name, field in cls.model_fields.items()
        ]

    def serialize(self) -> bytes:
        """Serialize the container to SSZ bytes."""
        from .composite import (
            List,
            Vector,
            encode_composite,
            is_variable_size,
        )

        field_list = self.get_fields()

        # Prepare data for composite encoding
        elements: list[Any] = []
        element_types: list[PyUnion[type[Any], Any]] = []
        variable_sizes: list[bool] = []

        for field_name, field_type in field_list:
            value = getattr(self, field_name)
            elements.append(value)
            # For composite types (Vector, List, Container), pass the instance
            # For basic types, pass the type
            if isinstance(value, (Vector, List, Container)):
                # Pass instance for size calculation
                element_types.append(value)
                variable_sizes.append(is_variable_size(value))
            else:
                actual_type = type(value) if value is not None else field_type
                element_types.append(actual_type)
                variable_sizes.append(is_variable_size(actual_type))

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

    def __repr__(self) -> str:
        """String representation of the container."""
        field_strs = []
        for field_name, _ in self.get_fields():
            value = getattr(self, field_name)
            field_strs.append(f"{field_name}={value!r}")

        return f"{self.__class__.__name__}({', '.join(field_strs)})"


def is_container(obj: Any) -> bool:
    """Check if an object is a Container."""
    return isinstance(obj, type) and issubclass(obj, Container)
