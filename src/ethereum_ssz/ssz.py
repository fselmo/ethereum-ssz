"""SSZ serialization and deserialization format used in Ethereum 2.0."""

from collections.abc import Sequence
from typing import (
    Protocol,
    TypeAlias,
    TypeVar,
    runtime_checkable,
)
from typing import (
    Union as PyUnion,
)

from ethereum_types.bytes import Bytes, FixedBytes
from ethereum_types.numeric import FixedUnsigned, Uint

from .bitfields import Bitlist, Bitvector
from .composite import List as SSZList
from .composite import Vector, encode_composite, is_variable_size
from .container import Container
from .exceptions import DecodingError, EncodingError
from .union import Union

# SSZ constants
BYTES_PER_LENGTH_OFFSET = 4
BITS_PER_BYTE = 8

# Type aliases similar to ethereum-rlp
Simple: TypeAlias = PyUnion[Sequence["Simple"], bytes]
Extended: TypeAlias = PyUnion[
    Sequence["Extended"], bytearray, bytes, Uint, FixedUnsigned, str, bool
]


@runtime_checkable
class SSZ(Protocol):
    """
    Protocol that describes the requirements to be SSZ-encodable.
    Similar to RLP protocol in ethereum-rlp.
    """

    pass


#
# SSZ Encode
#


def encode(raw_data: Extended) -> Bytes:
    """
    Encodes `raw_data` into a sequence of bytes using SSZ.

    SSZ encoding rules:
    - Integers are encoded as little-endian
    - Booleans are encoded as single byte (0x00 or 0x01)
    - Fixed-size byte arrays are encoded as-is
    - Variable-size types have offsets for variable parts
    """
    if isinstance(raw_data, bool):
        return encode_bool(raw_data)
    elif isinstance(raw_data, (Uint, FixedUnsigned)):
        return encode_uint(raw_data)
    elif isinstance(raw_data, (bytes, bytearray)):
        return encode_bytes(raw_data)
    elif isinstance(raw_data, str):
        return encode_bytes(raw_data.encode())
    elif isinstance(raw_data, Container):
        return encode_container(raw_data)
    elif isinstance(raw_data, Bitvector):
        return Bytes(raw_data.serialize())
    elif isinstance(raw_data, Bitlist):
        return Bytes(raw_data.serialize())
    elif isinstance(raw_data, Union):
        return Bytes(raw_data.serialize())
    elif isinstance(raw_data, Vector):
        return encode_vector(raw_data)
    elif isinstance(raw_data, SSZList):
        return encode_list(raw_data)
    elif isinstance(raw_data, Sequence):
        # For now, treat as a basic list
        return encode_sequence(raw_data)
    else:
        raise EncodingError(
            f"SSZ Encoding of type {type(raw_data)} is not supported"
        )


def encode_bool(value: bool) -> Bytes:
    """
    Encodes a boolean value using SSZ.

    - True -> 0x01
    - False -> 0x00
    """
    return Bytes([0x01 if value else 0x00])


def encode_uint(value: PyUnion[Uint, FixedUnsigned]) -> Bytes:
    """
    Encodes an unsigned integer using SSZ.

    SSZ uses little-endian encoding for integers.
    """
    # Determine byte length based on type
    if isinstance(value, FixedUnsigned):
        # For FixedUnsigned types, derive byte length from MAX_VALUE
        bits = value.MAX_VALUE._number.bit_length()
        byte_length = (bits + 7) // 8
    else:
        # For Uint, we need to determine appropriate size
        # Default to minimal bytes needed
        if value == 0:
            byte_length = 1
        else:
            byte_length = (value.bit_length() + 7) // 8
            # Round up to standard sizes (1, 2, 4, 8, 32)
            if byte_length <= 1:
                byte_length = 1
            elif byte_length <= 2:
                byte_length = 2
            elif byte_length <= 4:
                byte_length = 4
            elif byte_length <= 8:
                byte_length = 8
            elif byte_length <= 32:
                byte_length = 32
            else:
                raise EncodingError(
                    f"Integer {value} too large for SSZ encoding"
                )

    # Convert to little-endian bytes (SSZ uses LE, not BE like RLP)
    return Bytes(value.to_bytes(byte_length, byteorder="little"))


def encode_bytes(raw_bytes: PyUnion[bytes, bytearray]) -> Bytes:
    """
    Encodes bytes using SSZ.

    For basic fixed-size byte arrays, SSZ encodes them as-is.
    For variable-size, we'll need to handle offsets (TODO).
    """
    return Bytes(raw_bytes)


def encode_container(container: Container) -> Bytes:
    """
    Encodes a Container using SSZ.

    Containers encode their fields in order.
    """
    return Bytes(container.serialize())


def encode_vector(vector: Vector) -> Bytes:
    """
    Encodes a fixed-length vector using SSZ.

    Vectors are encoded as concatenation of their encoded elements.
    If elements are variable-size, offset encoding is used.
    """
    # Determine if elements are variable size
    variable_sizes = [is_variable_size(type(elem)) for elem in vector]
    element_types = [type(elem) for elem in vector]

    return encode_composite(vector, element_types, variable_sizes)


def encode_list(ssz_list: SSZList) -> Bytes:
    """
    Encodes a variable-length list using SSZ.

    Lists are encoded with their length prefix (4 bytes) followed by
    the encoded elements.
    """
    # First encode the list contents like a vector
    variable_sizes = [is_variable_size(type(elem)) for elem in ssz_list]
    element_types = [type(elem) for elem in ssz_list]

    encoded_elements = encode_composite(
        ssz_list, element_types, variable_sizes
    )

    # For SSZ lists, we need to prepend the length
    # Note: In full SSZ, the length prefix handling depends on context
    # For now, we'll just concatenate the elements
    return encoded_elements


def encode_sequence(raw_sequence: Sequence[Extended]) -> Bytes:
    """
    Encodes a sequence of SSZ encodable objects.

    This is a simplified version - full SSZ has complex rules for
    variable vs fixed size elements and offset handling.
    """
    # For now, simple concatenation of encoded elements
    # TODO: Implement proper offset handling for variable-size elements
    result = b""
    for item in raw_sequence:
        result += encode(item)
    return Bytes(result)


#
# SSZ Decode
#


def decode(encoded_data: Bytes) -> Simple:
    """
    Decodes SSZ-encoded data.

    Note: This is a basic implementation. Full SSZ decoding requires
    type information to properly decode (unlike RLP which is self-describing).
    """
    if len(encoded_data) == 0:
        raise DecodingError("Cannot decode empty bytestring")

    # SSZ requires type information for proper decoding
    # This basic decode can only handle raw bytes
    return bytes(encoded_data)


U = TypeVar("U", bound=Extended)


def decode_to(cls: type[U], encoded_data: Bytes) -> U:
    """
    Decode the bytes in `encoded_data` to an object of type `cls`.

    Similar to ethereum-rlp's decode_to, but uses SSZ rules.
    """
    try:
        if cls is bool:
            return decode_bool(encoded_data)  # type: ignore
        elif issubclass(cls, (Uint, FixedUnsigned)):
            return decode_uint(cls, encoded_data)  # type: ignore
        elif issubclass(cls, (bytes, Bytes, FixedBytes)):
            return decode_bytes_to(cls, encoded_data)  # type: ignore
        elif issubclass(cls, Container):
            return decode_container(cls, encoded_data)  # type: ignore
        elif issubclass(cls, Vector):
            # Need more context for Vector (element type, length)
            raise NotImplementedError(
                "Vector decoding requires element_type and length parameters"
            )
        elif issubclass(cls, SSZList):
            # Need more context for List (element type, max_length)
            raise NotImplementedError(
                "List decoding requires element_type and max_length parameters"
            )
        elif issubclass(cls, (Bitvector, Bitlist)):
            return cls.deserialize(encoded_data)  # type: ignore
        elif issubclass(cls, Union):
            # Need more context for Union (types)
            raise NotImplementedError(
                "Union decoding requires types parameter"
            )
        else:
            raise NotImplementedError(
                f"SSZ decoding for {cls} not yet implemented"
            )
    except Exception as e:
        raise DecodingError(f"Cannot decode into `{cls.__name__}`") from e


def decode_bool(encoded_data: Bytes) -> bool:
    """Decodes a boolean from SSZ encoding."""
    if len(encoded_data) != 1:
        raise DecodingError(f"Boolean must be 1 byte, got {len(encoded_data)}")

    value = encoded_data[0]
    if value == 0x00:
        return False
    elif value == 0x01:
        return True
    else:
        raise DecodingError(f"Invalid boolean value: {value:#x}")


def decode_uint(
    cls: PyUnion[type[Uint], type[FixedUnsigned]], encoded_data: Bytes
) -> PyUnion[Uint, FixedUnsigned]:
    """
    Decodes an unsigned integer from SSZ encoding.

    SSZ uses little-endian encoding.
    """
    if len(encoded_data) == 0:
        raise DecodingError("Cannot decode empty bytes as uint")

    # Convert from little-endian bytes
    value = int.from_bytes(encoded_data, byteorder="little")

    try:
        return cls(value)
    except (ValueError, OverflowError) as e:
        raise DecodingError(
            f"Value {value} out of range for {cls.__name__}"
        ) from e


def decode_bytes_to(
    cls: PyUnion[type[Bytes], type[FixedBytes], type[bytes]],
    encoded_data: Bytes,
) -> PyUnion[Bytes, FixedBytes, bytes]:
    """Decodes bytes from SSZ encoding."""
    if cls is bytes:
        return bytes(encoded_data)
    elif cls is Bytes:
        return Bytes(encoded_data)
    else:
        # FixedBytes subclass
        try:
            return cls(encoded_data)
        except ValueError as e:
            raise DecodingError(f"Invalid bytes for {cls.__name__}") from e


def decode_container(cls: type[Container], encoded_data: Bytes) -> Container:
    """
    Decodes a Container from SSZ encoding.

    Containers may have mixed fixed and variable-size fields.
    """
    from .composite import get_fixed_size, is_variable_size

    field_list = cls.get_fields()

    # Parse offsets for variable-size fields
    pos = 0
    field_values = {}
    variable_offsets = []

    # First pass: read fixed fields and offsets
    for field_name, field_type in field_list:
        if is_variable_size(field_type):
            # Read offset (4 bytes little-endian)
            if pos + BYTES_PER_LENGTH_OFFSET > len(encoded_data):
                raise DecodingError("Insufficient data for offset")
            offset = int.from_bytes(
                encoded_data[pos : pos + BYTES_PER_LENGTH_OFFSET], "little"
            )
            variable_offsets.append((field_name, field_type, offset))
            pos += BYTES_PER_LENGTH_OFFSET
        else:
            # Read fixed-size field
            field_size = get_fixed_size(field_type)
            if pos + field_size > len(encoded_data):
                raise DecodingError(
                    f"Insufficient data for field {field_name}"
                )
            field_data = encoded_data[pos : pos + field_size]
            field_values[field_name] = decode_to(field_type, field_data)
            pos += field_size

    # Second pass: read variable fields using offsets
    for i, (field_name, field_type, offset) in enumerate(variable_offsets):
        # Determine the end of this field
        if i + 1 < len(variable_offsets):
            end = variable_offsets[i + 1][2]
        else:
            end = len(encoded_data)

        if offset > end or offset < pos:
            raise DecodingError(f"Invalid offset for field {field_name}")

        field_data = encoded_data[offset:end]
        field_values[field_name] = decode_to(field_type, field_data)

    # Create the container instance
    return cls(**field_values)


def decode_vector(
    encoded_data: Bytes, element_type: type, length: int
) -> Vector:
    """
    Decode a Vector from SSZ bytes.

    Args:
        encoded_data: SSZ-encoded bytes
        element_type: Type of vector elements
        length: Fixed length of the vector

    Returns:
        Decoded Vector instance
    """
    from .composite import get_fixed_size, is_variable_size

    elements = []

    if not is_variable_size(element_type):
        # Fixed-size elements - simple division
        elem_size = get_fixed_size(element_type)
        expected_size = elem_size * length

        if len(encoded_data) != expected_size:
            raise DecodingError(
                f"Invalid data size for Vector[{element_type.__name__}, "
                f"{length}]: expected {expected_size}, got {len(encoded_data)}"
            )

        for i in range(length):
            start = i * elem_size
            end = start + elem_size
            elem_data = encoded_data[start:end]
            elements.append(decode_to(element_type, elem_data))
    else:
        # Variable-size elements - use offsets
        if length == 0:
            return Vector([], length, element_type)

        # Read offsets
        offsets = []
        for i in range(length):
            offset_start = i * BYTES_PER_LENGTH_OFFSET
            offset_end = offset_start + BYTES_PER_LENGTH_OFFSET
            if offset_end > len(encoded_data):
                raise DecodingError("Insufficient data for offsets")
            offset = int.from_bytes(
                encoded_data[offset_start:offset_end], "little"
            )
            offsets.append(offset)

        # Decode elements using offsets
        for i in range(length):
            start = offsets[i]
            end = offsets[i + 1] if i + 1 < length else len(encoded_data)

            if start > end or start < length * BYTES_PER_LENGTH_OFFSET:
                raise DecodingError(f"Invalid offset at index {i}")

            elem_data = encoded_data[start:end]
            elements.append(decode_to(element_type, elem_data))

    return Vector(elements, length, element_type)


def decode_list(
    encoded_data: Bytes, element_type: type, max_length: int
) -> SSZList:
    """
    Decode a List from SSZ bytes.

    Args:
        encoded_data: SSZ-encoded bytes
        element_type: Type of list elements
        max_length: Maximum allowed length

    Returns:
        Decoded List instance
    """
    from .composite import get_fixed_size, is_variable_size

    if len(encoded_data) == 0:
        return SSZList([], max_length, element_type)

    elements = []

    if not is_variable_size(element_type):
        # Fixed-size elements - simple division
        elem_size = get_fixed_size(element_type)

        if len(encoded_data) % elem_size != 0:
            raise DecodingError(
                f"Invalid data size for List[{element_type.__name__}]: "
                f"not a multiple of element size {elem_size}"
            )

        count = len(encoded_data) // elem_size
        if count > max_length:
            raise DecodingError(
                f"List count {count} exceeds maximum length {max_length}"
            )

        for i in range(count):
            start = i * elem_size
            end = start + elem_size
            elem_data = encoded_data[start:end]
            elements.append(decode_to(element_type, elem_data))
    else:
        # Variable-size elements - use offsets
        # First offset tells us the count
        if len(encoded_data) < BYTES_PER_LENGTH_OFFSET:
            raise DecodingError("Insufficient data for first offset")

        first_offset = int.from_bytes(
            encoded_data[:BYTES_PER_LENGTH_OFFSET], "little"
        )

        if first_offset % BYTES_PER_LENGTH_OFFSET != 0:
            raise DecodingError("First offset not aligned")

        count = first_offset // BYTES_PER_LENGTH_OFFSET
        if count > max_length:
            raise DecodingError(
                f"List count {count} exceeds maximum length {max_length}"
            )

        # Read all offsets
        offsets = [first_offset]
        for i in range(1, count):
            offset_start = i * BYTES_PER_LENGTH_OFFSET
            offset_end = offset_start + BYTES_PER_LENGTH_OFFSET
            if offset_end > len(encoded_data):
                raise DecodingError("Insufficient data for offsets")
            offset = int.from_bytes(
                encoded_data[offset_start:offset_end], "little"
            )
            offsets.append(offset)

        # Decode elements using offsets
        for i in range(count):
            start = offsets[i]
            end = offsets[i + 1] if i + 1 < count else len(encoded_data)

            if start > end or start < count * BYTES_PER_LENGTH_OFFSET:
                raise DecodingError(f"Invalid offset at index {i}")

            elem_data = encoded_data[start:end]
            elements.append(decode_to(element_type, elem_data))

    return SSZList(elements, max_length, element_type)
