"""
Tests for SSZ composite types (Vector, List).
"""

import pytest
from ethereum_types.bytes import Bytes32
from ethereum_types.numeric import U8, U32, U64

from ethereum_ssz import ssz
from ethereum_ssz.composite import List as SSZList
from ethereum_ssz.composite import Vector
from ethereum_ssz.exceptions import EncodingError

#
# Vector tests
#


def test_vector_creation() -> None:
    """Test creating a Vector with fixed length."""
    # Create a vector of 4 U8 values
    vec = Vector([U8(1), U8(2), U8(3), U8(4)], length=4, element_type=U8)
    assert len(vec) == 4
    assert vec[0] == U8(1)
    assert vec[3] == U8(4)


def test_vector_length_mismatch() -> None:
    """Test that Vector enforces length constraint."""
    with pytest.raises(ValueError, match="requires exactly 3 elements"):
        Vector([U8(1), U8(2)], length=3, element_type=U8)

    with pytest.raises(ValueError, match="requires exactly 2 elements"):
        Vector([U8(1), U8(2), U8(3)], length=2, element_type=U8)


def test_vector_immutable_length() -> None:
    """Test that Vector length cannot be changed."""
    vec = Vector([U8(1), U8(2)], length=2, element_type=U8)

    with pytest.raises(NotImplementedError):
        vec.append(U8(3))

    with pytest.raises(NotImplementedError):
        vec.extend([U8(3)])

    with pytest.raises(NotImplementedError):
        vec.pop()

    with pytest.raises(NotImplementedError):
        vec.remove(U8(1))


def test_encode_vector_fixed_size() -> None:
    """Test encoding a vector of fixed-size elements."""
    vec = Vector([U8(1), U8(2), U8(3)], length=3, element_type=U8)
    encoded = ssz.encode(vec)

    # Should be simple concatenation for fixed-size elements
    assert encoded == bytes([0x01, 0x02, 0x03])


def test_encode_vector_u32() -> None:
    """Test encoding a vector of U32 values."""
    vec = Vector(
        [U32(0x12345678), U32(0xABCDEF00)], length=2, element_type=U32
    )
    encoded = ssz.encode(vec)

    # Little-endian encoding of each U32
    expected = bytes(
        [
            0x78,
            0x56,
            0x34,
            0x12,  # First U32
            0x00,
            0xEF,
            0xCD,
            0xAB,  # Second U32
        ]
    )
    assert encoded == expected


#
# List tests
#


def test_list_creation() -> None:
    """Test creating a List with max length."""
    # Create a list with max_length=10
    lst = SSZList([U8(1), U8(2), U8(3)], max_length=10, element_type=U8)
    assert len(lst) == 3
    assert lst[0] == U8(1)
    assert lst[2] == U8(3)


def test_list_max_length_constraint() -> None:
    """Test that List enforces max_length constraint."""
    # Should work with length <= max_length
    lst = SSZList([U8(1), U8(2)], max_length=2, element_type=U8)
    assert len(lst) == 2

    # Should fail with length > max_length
    with pytest.raises(ValueError, match="exceeds maximum length"):
        SSZList([U8(1), U8(2), U8(3)], max_length=2, element_type=U8)


def test_list_append_within_limit() -> None:
    """Test appending to a List within the limit."""
    lst = SSZList([U8(1)], max_length=3, element_type=U8)

    lst.append(U8(2))
    assert len(lst) == 2
    assert lst[1] == U8(2)

    lst.append(U8(3))
    assert len(lst) == 3
    assert lst[2] == U8(3)


def test_list_append_exceeds_limit() -> None:
    """Test that appending beyond max_length fails."""
    lst = SSZList([U8(1), U8(2)], max_length=2, element_type=U8)

    with pytest.raises(ValueError, match="would exceed maximum length"):
        lst.append(U8(3))


def test_list_extend_within_limit() -> None:
    """Test extending a List within the limit."""
    lst = SSZList([U8(1)], max_length=5, element_type=U8)

    lst.extend([U8(2), U8(3)])
    assert len(lst) == 3
    assert list(lst) == [U8(1), U8(2), U8(3)]


def test_list_extend_exceeds_limit() -> None:
    """Test that extending beyond max_length fails."""
    lst = SSZList([U8(1)], max_length=2, element_type=U8)

    with pytest.raises(ValueError, match="would exceed maximum length"):
        lst.extend([U8(2), U8(3)])


def test_encode_list_fixed_size() -> None:
    """Test encoding a list of fixed-size elements."""
    lst = SSZList([U8(1), U8(2), U8(3)], max_length=10, element_type=U8)
    encoded = ssz.encode(lst)

    # For fixed-size elements, should be simple concatenation
    # (length prefix handling depends on context in full SSZ)
    assert encoded == bytes([0x01, 0x02, 0x03])


def test_encode_empty_list() -> None:
    """Test encoding an empty list."""
    lst = SSZList([], max_length=10, element_type=U8)
    encoded = ssz.encode(lst)
    assert encoded == b""


def test_encode_list_u64() -> None:
    """Test encoding a list of U64 values."""
    lst = SSZList(
        [U64(0x0123456789ABCDEF), U64(0xFEDCBA9876543210)],
        max_length=5,
        element_type=U64,
    )
    encoded = ssz.encode(lst)

    # Little-endian encoding of each U64
    expected = bytes(
        [
            0xEF,
            0xCD,
            0xAB,
            0x89,
            0x67,
            0x45,
            0x23,
            0x01,  # First U64
            0x10,
            0x32,
            0x54,
            0x76,
            0x98,
            0xBA,
            0xDC,
            0xFE,  # Second U64
        ]
    )
    assert encoded == expected


#
# Mixed fixed/variable size tests (for future implementation)
#


def test_encode_vector_mixed_sizes() -> None:
    """Test encoding a vector with mixed fixed/variable size elements."""
    # This would require more complex offset handling
    # For now, we'll skip this test
    pytest.skip("Mixed size encoding not yet implemented")


def test_encode_list_variable_size_elements() -> None:
    """Test encoding a list with variable-size elements."""
    # Lists of bytes or strings would be variable-size
    # This requires offset encoding
    pytest.skip("Variable size element encoding not yet implemented")
