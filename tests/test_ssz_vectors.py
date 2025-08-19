"""
SSZ test vectors adapted from remerkleable.

These tests verify SSZ encoding against known test vectors.
"""

import hashlib

from ethereum_types.bytes import Bytes32, Bytes48, Bytes96
from ethereum_types.numeric import U8, U32, U64, U256

from ethereum_ssz import U16, hash_tree_root, ssz
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


class TestBasicTypes:
    """Test basic SSZ types against known vectors."""

    def test_bool_false(self):
        """Test boolean false encoding."""
        encoded = ssz.encode(False)
        assert encoded == b"\x00"

        htr = hash_tree_root(False)
        assert htr == Bytes32(b"\x00" * 32)

    def test_bool_true(self):
        """Test boolean true encoding."""
        encoded = ssz.encode(True)
        assert encoded == b"\x01"

        htr = hash_tree_root(True)
        assert htr == Bytes32(b"\x01" + b"\x00" * 31)

    def test_uint8_00(self):
        """Test uint8(0x00) encoding."""
        value = U8(0x00)
        encoded = ssz.encode(value)
        assert encoded == b"\x00"

        htr = hash_tree_root(value)
        assert htr == Bytes32(chunk(b"\x00"))

    def test_uint8_01(self):
        """Test uint8(0x01) encoding."""
        value = U8(0x01)
        encoded = ssz.encode(value)
        assert encoded == b"\x01"

        htr = hash_tree_root(value)
        assert htr == Bytes32(chunk(b"\x01"))

    def test_uint8_ab(self):
        """Test uint8(0xab) encoding."""
        value = U8(0xAB)
        encoded = ssz.encode(value)
        assert encoded == b"\xab"

        htr = hash_tree_root(value)
        assert htr == Bytes32(chunk(b"\xab"))

    def test_uint16_0000(self):
        """Test uint16(0x0000) encoding."""
        value = U16(0x0000)
        encoded = ssz.encode(value)
        assert encoded == b"\x00\x00"

        htr = hash_tree_root(value)
        assert htr == Bytes32(chunk(b"\x00\x00"))

    def test_uint16_abcd(self):
        """Test uint16(0xabcd) encoding - little endian."""
        value = U16(0xABCD)
        encoded = ssz.encode(value)
        assert encoded == b"\xcd\xab"  # Little-endian

        htr = hash_tree_root(value)
        assert htr == Bytes32(chunk(b"\xcd\xab"))

    def test_uint32_00000000(self):
        """Test uint32(0x00000000) encoding."""
        value = U32(0x00000000)
        encoded = ssz.encode(value)
        assert encoded == b"\x00\x00\x00\x00"

        htr = hash_tree_root(value)
        assert htr == Bytes32(chunk(b"\x00\x00\x00\x00"))

    def test_uint32_01234567(self):
        """Test uint32(0x01234567) encoding - little endian."""
        value = U32(0x01234567)
        encoded = ssz.encode(value)
        assert encoded == b"\x67\x45\x23\x01"  # Little-endian

        htr = hash_tree_root(value)
        assert htr == Bytes32(chunk(b"\x67\x45\x23\x01"))

    def test_uint64_0000000000000000(self):
        """Test uint64(0) encoding."""
        value = U64(0x0000000000000000)
        encoded = ssz.encode(value)
        assert encoded == b"\x00" * 8

        htr = hash_tree_root(value)
        assert htr == Bytes32(chunk(b"\x00" * 8))

    def test_uint64_0123456789abcdef(self):
        """Test uint64(0x0123456789abcdef) encoding - little endian."""
        value = U64(0x0123456789ABCDEF)
        encoded = ssz.encode(value)
        assert encoded == b"\xef\xcd\xab\x89\x67\x45\x23\x01"  # Little-endian

        htr = hash_tree_root(value)
        assert htr == Bytes32(chunk(b"\xef\xcd\xab\x89\x67\x45\x23\x01"))


class TestVectors:
    """Test Vector encoding against known vectors."""

    def test_vector_uint16_2(self):
        """Test Vector[uint16, 2] encoding."""
        vec = Vector([U16(0x4567), U16(0x0123)], length=2, element_type=U16)
        encoded = ssz.encode(vec)
        # Little-endian encoding of each element
        assert encoded == b"\x67\x45\x23\x01"

        # For vectors, merkle root is different
        htr = hash_tree_root(vec)
        assert isinstance(htr, Bytes32)

    def test_vector_byte_48(self):
        """Test Vector[byte, 48] encoding (like BLS signature)."""
        # Create a 48-byte vector
        vec = Vector([U8(i) for i in range(48)], length=48, element_type=U8)
        encoded = ssz.encode(vec)

        expected = bytes(range(48))
        assert encoded == expected

        htr = hash_tree_root(vec)
        assert isinstance(htr, Bytes32)

    def test_vector_byte_96(self):
        """Test Vector[byte, 96] encoding (like full BLS signature)."""
        # Test data similar to remerkleable
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

        htr = hash_tree_root(vec)
        assert isinstance(htr, Bytes32)


class TestLists:
    """Test List encoding against known vectors."""

    def test_empty_list_small(self):
        """Test empty List[byte, 10] encoding."""
        lst = SSZList([], max_length=10, element_type=U8)
        encoded = ssz.encode(lst)
        assert encoded == b""

        htr = hash_tree_root(lst)
        assert isinstance(htr, Bytes32)

    def test_empty_list_large(self):
        """Test empty List[byte, 2048] encoding."""
        lst = SSZList([], max_length=2048, element_type=U8)
        encoded = ssz.encode(lst)
        assert encoded == b""

        htr = hash_tree_root(lst)
        assert isinstance(htr, Bytes32)

    def test_list_byte_7(self):
        """Test List[byte, 7] with 7 elements."""
        lst = SSZList([U8(i) for i in range(7)], max_length=7, element_type=U8)
        encoded = ssz.encode(lst)
        assert encoded == bytes(range(7))

        htr = hash_tree_root(lst)
        assert isinstance(htr, Bytes32)

    def test_list_byte_50(self):
        """Test List[byte, 50] with 50 elements."""
        lst = SSZList(
            [U8(i) for i in range(50)], max_length=50, element_type=U8
        )
        encoded = ssz.encode(lst)
        assert encoded == bytes(range(50))

        htr = hash_tree_root(lst)
        assert isinstance(htr, Bytes32)

    def test_list_byte_6_of_256(self):
        """Test List[byte, 256] with only 6 elements."""
        lst = SSZList(
            [U8(i) for i in range(6)], max_length=256, element_type=U8
        )
        encoded = ssz.encode(lst)
        assert encoded == bytes(range(6))

        htr = hash_tree_root(lst)
        assert isinstance(htr, Bytes32)

    def test_list_uint16_variable(self):
        """Test List[uint16, 1024] with a few elements."""
        lst = SSZList(
            [U16(1), U16(2), U16(3)], max_length=1024, element_type=U16
        )
        encoded = ssz.encode(lst)
        # Little-endian encoding of each uint16
        assert encoded == b"\x01\x00\x02\x00\x03\x00"

        htr = hash_tree_root(lst)
        assert isinstance(htr, Bytes32)


class TestComplexStructures:
    """Test more complex SSZ structures."""

    def test_nested_vectors(self):
        """Test Vector of Vectors."""
        # Create Vector[Vector[uint8, 3], 2]
        inner1 = Vector([U8(1), U8(2), U8(3)], length=3, element_type=U8)
        inner2 = Vector([U8(4), U8(5), U8(6)], length=3, element_type=U8)
        outer = Vector([inner1, inner2], length=2, element_type=Vector)

        encoded = ssz.encode(outer)
        assert encoded == b"\x01\x02\x03\x04\x05\x06"

        htr = hash_tree_root(outer)
        assert isinstance(htr, Bytes32)

    def test_list_of_vectors(self):
        """Test List of Vectors."""
        vec1 = Vector([U16(1), U16(2)], length=2, element_type=U16)
        vec2 = Vector([U16(3), U16(4)], length=2, element_type=U16)
        lst = SSZList([vec1, vec2], max_length=10, element_type=Vector)

        encoded = ssz.encode(lst)
        # Little-endian uint16s
        assert encoded == b"\x01\x00\x02\x00\x03\x00\x04\x00"

        htr = hash_tree_root(lst)
        assert isinstance(htr, Bytes32)
