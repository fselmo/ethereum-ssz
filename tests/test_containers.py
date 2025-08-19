"""
Test containers and complex structures adapted from remerkleable.

These tests verify SSZ encoding/decoding of complex composite types.
"""

import hashlib

from ethereum_types.bytes import Bytes, Bytes32
from ethereum_types.numeric import U8, U32, U64, U256

from ethereum_ssz import U16, U128, hash_tree_root, ssz
from ethereum_ssz.composite import List as SSZList
from ethereum_ssz.composite import Vector


def sha256(data: bytes) -> bytes:
    """SHA256 hash helper."""
    return hashlib.sha256(data).digest()


def h(a: bytes, b: bytes) -> bytes:
    """Hash two 32-byte chunks together."""
    return sha256(a + b)


def chunk(data: bytes) -> bytes:
    """Pad data to 32 bytes."""
    if len(data) >= 32:
        return data[:32]
    return data + b"\x00" * (32 - len(data))


def merge(a: bytes, branch: list[bytes]) -> bytes:
    """Merge (out on left, branch on right) leaf a with branch items."""
    out = a
    for b in branch:
        out = h(out, b)
    return out


# Precompute zero hashes for merkleization
zero_hashes = [chunk(b"")]
for layer in range(1, 32):
    zero_hashes.append(h(zero_hashes[layer - 1], zero_hashes[layer - 1]))


class TestContainers:
    """Test Container types (when we implement them)."""

    def test_container_placeholder(self):
        """Placeholder for container tests - to be implemented."""
        # When we implement Container class, these tests will verify:
        # - SingleFieldTestStruct with one byte field
        # - SmallTestStruct with two uint16 fields
        # - FixedTestStruct with mixed uint sizes
        # - VarTestStruct with fixed and variable fields
        # - ComplexTestStruct with nested containers and lists
        assert True  # Placeholder


class TestComplexVectors:
    """Test complex vector structures."""

    def test_vector_of_vectors(self):
        """Test encoding Vector[Vector[uint8, 3], 2]."""
        # Create inner vectors
        inner1 = Vector([U8(1), U8(2), U8(3)], length=3, element_type=U8)
        inner2 = Vector([U8(4), U8(5), U8(6)], length=3, element_type=U8)

        # Create outer vector
        outer = Vector([inner1, inner2], length=2, element_type=Vector)

        # Encode
        encoded = ssz.encode(outer)
        assert encoded == b"\x01\x02\x03\x04\x05\x06"

        # Hash tree root
        htr = hash_tree_root(outer)
        assert isinstance(htr, Bytes32)

    def test_vector_uint16_exact(self):
        """Test Vector[uint16, 2] with exact known encoding."""
        vec = Vector([U16(0x4567), U16(0x0123)], length=2, element_type=U16)
        encoded = ssz.encode(vec)

        # Little-endian encoding
        assert encoded == b"\x67\x45\x23\x01"

        # Verify hash tree root matches remerkleable exactly
        htr = hash_tree_root(vec)
        # From remerkleable test: chunk("67452301")
        expected_htr = Bytes32(bytes.fromhex("67452301") + b"\x00" * 28)
        assert htr == expected_htr

    def test_long_byte_vector_48(self):
        """Test Vector[byte, 48] (like BLS public key)."""
        vec = Vector([U8(i) for i in range(48)], length=48, element_type=U8)
        encoded = ssz.encode(vec)

        expected = bytes(range(48))
        assert encoded == expected

        # Hash tree root should be h(first_32_bytes, last_16_bytes_padded)
        htr = hash_tree_root(vec)
        expected_htr = Bytes32(
            h(bytes(range(32)), bytes(range(32, 48)) + b"\x00" * 16)
        )
        assert htr == expected_htr

    def test_long_byte_vector_96(self):
        """Test Vector[byte, 96] (like BLS signature)."""
        # Create test data matching remerkleable
        sig_test_data = [0] * 96
        sig_test_data[0] = 1
        sig_test_data[32] = 2
        sig_test_data[64] = 3
        sig_test_data[95] = 0xFF

        vec = Vector(
            [U8(x) for x in sig_test_data], length=96, element_type=U8
        )
        encoded = ssz.encode(vec)

        expected = bytes(sig_test_data)
        assert encoded == expected

        # Verify merkle root calculation
        htr = hash_tree_root(vec)
        expected_htr = Bytes32(
            h(
                h(chunk(b"\x01"), chunk(b"\x02")),
                h(b"\x03" + b"\x00" * 30 + b"\xff", chunk(b"")),
            )
        )
        assert htr == expected_htr


class TestComplexLists:
    """Test complex list structures."""

    def test_uint16_list(self):
        """Test List[uint16, 32] encoding."""
        lst = SSZList(
            [U16(0xAABB), U16(0xC0AD), U16(0xEEFF)],
            max_length=32,
            element_type=U16,
        )
        encoded = ssz.encode(lst)

        # Little-endian encoding of each uint16
        assert encoded == b"\xbb\xaa\xad\xc0\xff\xee"

        # Verify hash tree root
        htr = hash_tree_root(lst)
        assert isinstance(htr, Bytes32)

    def test_uint32_list(self):
        """Test List[uint32, 128] encoding."""
        lst = SSZList(
            [U32(0xAABB), U32(0xC0AD), U32(0xEEFF)],
            max_length=128,
            element_type=U32,
        )
        encoded = ssz.encode(lst)

        # Little-endian encoding with padding
        assert encoded == b"\xbb\xaa\x00\x00\xad\xc0\x00\x00\xff\xee\x00\x00"

        htr = hash_tree_root(lst)
        assert isinstance(htr, Bytes32)

    def test_empty_list_small(self):
        """Test empty List[byte, 10]."""
        lst = SSZList([], max_length=10, element_type=U8)
        encoded = ssz.encode(lst)

        assert encoded == b""

        # Empty list should still have a valid hash tree root
        htr = hash_tree_root(lst)
        expected_htr = Bytes32(h(chunk(b""), chunk(b"\x00")))
        assert htr == expected_htr

    def test_empty_list_large(self):
        """Test empty List[byte, 2048]."""
        lst = SSZList([], max_length=2048, element_type=U8)
        encoded = ssz.encode(lst)

        assert encoded == b""

        # Large empty list uses deeper tree
        htr = hash_tree_root(lst)
        expected_htr = Bytes32(h(zero_hashes[6], chunk(b"\x00")))
        assert htr == expected_htr

    def test_byte_list_exact_7(self):
        """Test List[byte, 7] with exactly 7 elements."""
        lst = SSZList([U8(i) for i in range(7)], max_length=7, element_type=U8)
        encoded = ssz.encode(lst)

        assert encoded == bytes(range(7))

        htr = hash_tree_root(lst)
        expected_htr = Bytes32(h(chunk(bytes(range(7))), chunk(b"\x07")))
        assert htr == expected_htr

    def test_byte_list_50(self):
        """Test List[byte, 50] with 50 elements."""
        lst = SSZList(
            [U8(i) for i in range(50)], max_length=50, element_type=U8
        )
        encoded = ssz.encode(lst)

        assert encoded == bytes(range(50))

        htr = hash_tree_root(lst)
        expected_htr = Bytes32(
            h(
                h(bytes(range(32)), bytes(range(32, 50)) + b"\x00" * 14),
                chunk(b"\x32"),  # length = 50 = 0x32
            )
        )
        assert htr == expected_htr

    def test_byte_list_partial_256(self):
        """Test List[byte, 256] with only 6 elements."""
        lst = SSZList(
            [U8(i) for i in range(6)], max_length=256, element_type=U8
        )
        encoded = ssz.encode(lst)

        assert encoded == bytes(range(6))

        # 256 max = 2^8 = 8 chunks = 3 deep tree
        htr = hash_tree_root(lst)
        expected_htr = Bytes32(
            h(
                h(
                    h(
                        h(chunk(bytes(range(6))), zero_hashes[0]),
                        zero_hashes[1],
                    ),
                    zero_hashes[2],
                ),
                chunk(b"\x06"),
            )
        )
        assert htr == expected_htr


class TestNestedStructures:
    """Test nested composite types."""

    def test_list_of_vectors(self):
        """Test List[Vector[uint16, 2], 10]."""
        vec1 = Vector([U16(1), U16(2)], length=2, element_type=U16)
        vec2 = Vector([U16(3), U16(4)], length=2, element_type=U16)

        lst = SSZList([vec1, vec2], max_length=10, element_type=Vector)
        encoded = ssz.encode(lst)

        # Little-endian uint16s
        assert encoded == b"\x01\x00\x02\x00\x03\x00\x04\x00"

        htr = hash_tree_root(lst)
        assert isinstance(htr, Bytes32)

    def test_vector_of_lists(self):
        """Test Vector[List[uint8, 4], 2]."""
        lst1 = SSZList([U8(1), U8(2)], max_length=4, element_type=U8)
        lst2 = SSZList([U8(3), U8(4), U8(5)], max_length=4, element_type=U8)

        # Note: This will require offset encoding for variable-size lists
        # For now, we'll just verify the types work
        vec = Vector([lst1, lst2], length=2, element_type=SSZList)

        # This test will need updating when offset encoding is implemented
        # for variable-size elements in vectors
        assert vec[0] == lst1
        assert vec[1] == lst2

    def test_deeply_nested_vectors(self):
        """Test Vector[Vector[Vector[uint8, 2], 2], 2]."""
        # Innermost level
        inner1 = Vector([U8(1), U8(2)], length=2, element_type=U8)
        inner2 = Vector([U8(3), U8(4)], length=2, element_type=U8)
        inner3 = Vector([U8(5), U8(6)], length=2, element_type=U8)
        inner4 = Vector([U8(7), U8(8)], length=2, element_type=U8)

        # Middle level
        middle1 = Vector([inner1, inner2], length=2, element_type=Vector)
        middle2 = Vector([inner3, inner4], length=2, element_type=Vector)

        # Outer level
        outer = Vector([middle1, middle2], length=2, element_type=Vector)

        encoded = ssz.encode(outer)
        assert encoded == b"\x01\x02\x03\x04\x05\x06\x07\x08"

        htr = hash_tree_root(outer)
        assert isinstance(htr, Bytes32)


class TestUint256Lists:
    """Test lists of large integers."""

    def test_uint256_list_small(self):
        """Test List[uint256, 32] with 3 elements."""
        lst = SSZList(
            [U256(0xAABB), U256(0xC0AD), U256(0xEEFF)],
            max_length=32,
            element_type=U256,
        )

        encoded = ssz.encode(lst)

        # Each U256 is 32 bytes, little-endian
        expected = (
            b"\xbb\xaa"
            + b"\x00" * 30
            + b"\xad\xc0"
            + b"\x00" * 30
            + b"\xff\xee"
            + b"\x00" * 30
        )
        assert encoded == expected

        htr = hash_tree_root(lst)
        assert isinstance(htr, Bytes32)

    def test_uint256_list_long(self):
        """Test List[uint256, 128] with 19 elements."""
        lst = SSZList(
            [U256(i) for i in range(1, 20)], max_length=128, element_type=U256
        )

        encoded = ssz.encode(lst)

        # Verify encoding of each element
        expected = b"".join(i.to_bytes(32, "little") for i in range(1, 20))
        assert encoded == expected

        htr = hash_tree_root(lst)
        assert isinstance(htr, Bytes32)
