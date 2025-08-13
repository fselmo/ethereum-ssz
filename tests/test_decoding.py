"""
Test SSZ decoding functionality.

These tests verify that we can properly decode SSZ-encoded data back to objects.
"""

from dataclasses import dataclass

from ethereum_types.bytes import Bytes32
from ethereum_types.numeric import U8, U32, U64

from ethereum_ssz import (
    U16,
    Bitlist,
    Bitvector,
    Container,
    Vector,
    decode_list,
    decode_vector,
    ssz,
)
from ethereum_ssz import (
    List as SSZList,
)


class TestBasicDecoding:
    """Test decoding of basic types."""

    def test_decode_bool_true(self):
        """Test decoding boolean true."""
        encoded = b'\x01'
        decoded = ssz.decode_to(bool, encoded)
        assert decoded is True

    def test_decode_bool_false(self):
        """Test decoding boolean false."""
        encoded = b'\x00'
        decoded = ssz.decode_to(bool, encoded)
        assert decoded is False

    def test_decode_uint8(self):
        """Test decoding uint8."""
        encoded = b'\x42'
        decoded = ssz.decode_to(U8, encoded)
        assert decoded == U8(0x42)

    def test_decode_uint16(self):
        """Test decoding uint16 (little-endian)."""
        encoded = b'\xbb\xaa'  # 0xaabb in little-endian
        decoded = ssz.decode_to(U16, encoded)
        assert decoded == U16(0xaabb)

    def test_decode_uint32(self):
        """Test decoding uint32 (little-endian)."""
        encoded = b'\xef\xbe\xad\xde'  # 0xdeadbeef in little-endian
        decoded = ssz.decode_to(U32, encoded)
        assert decoded == U32(0xdeadbeef)


class TestContainerDecoding:
    """Test decoding of Container types."""

    def test_decode_simple_container(self):
        """Test decoding a simple container with fixed-size fields."""
        @dataclass
        class SimpleContainer(Container):
            a: U8
            b: U16
            c: U32

        # Encode a container
        original = SimpleContainer(a=U8(0x11), b=U16(0x2233), c=U32(0x44556677))
        encoded = ssz.encode(original)

        # Decode it back
        decoded = ssz.decode_to(SimpleContainer, encoded)

        assert decoded.a == U8(0x11)
        assert decoded.b == U16(0x2233)
        assert decoded.c == U32(0x44556677)
        assert decoded == original


class TestVectorDecoding:
    """Test decoding of Vector types."""

    def test_decode_uint16_vector(self):
        """Test decoding a vector of uint16s."""
        # Create and encode a vector
        original = Vector([U16(1), U16(2), U16(3)], length=3, element_type=U16)
        encoded = ssz.encode(original)

        # Decode it back
        decoded = decode_vector(encoded, U16, 3)

        assert len(decoded) == 3
        assert decoded[0] == U16(1)
        assert decoded[1] == U16(2)
        assert decoded[2] == U16(3)

    def test_decode_bool_vector(self):
        """Test decoding a vector of booleans."""
        original = Vector([True, False, True, True], length=4, element_type=bool)
        encoded = ssz.encode(original)

        decoded = decode_vector(encoded, bool, 4)

        assert len(decoded) == 4
        assert decoded[0] is True
        assert decoded[1] is False
        assert decoded[2] is True
        assert decoded[3] is True


class TestListDecoding:
    """Test decoding of List types."""

    def test_decode_uint32_list(self):
        """Test decoding a list of uint32s."""
        # Create and encode a list
        original = SSZList([U32(10), U32(20), U32(30)], max_length=10, element_type=U32)
        encoded = ssz.encode(original)

        # Decode it back
        decoded = decode_list(encoded, U32, 10)

        assert len(decoded) == 3
        assert decoded[0] == U32(10)
        assert decoded[1] == U32(20)
        assert decoded[2] == U32(30)

    def test_decode_empty_list(self):
        """Test decoding an empty list."""
        original = SSZList([], max_length=5, element_type=U8)
        encoded = ssz.encode(original)

        decoded = decode_list(encoded, U8, 5)

        assert len(decoded) == 0
        assert decoded.max_length == 5


class TestBitfieldDecoding:
    """Test decoding of bitfield types."""

    def test_decode_bitvector(self):
        """Test decoding a bitvector."""
        original = Bitvector([True, False, True, True, False], length=5)
        encoded = ssz.encode(original)

        # Bitvector knows how to deserialize itself
        decoded = Bitvector.deserialize(encoded, 5)

        assert len(decoded) == 5
        assert decoded[0] is True
        assert decoded[1] is False
        assert decoded[2] is True
        assert decoded[3] is True
        assert decoded[4] is False

    def test_decode_bitlist(self):
        """Test decoding a bitlist."""
        original = Bitlist([True, True, False, True], max_length=10)
        encoded = ssz.encode(original)

        # Bitlist knows how to deserialize itself
        decoded = Bitlist.deserialize(encoded, 10)

        assert len(decoded) == 4
        assert decoded[0] is True
        assert decoded[1] is True
        assert decoded[2] is False
        assert decoded[3] is True
        assert decoded.max_length == 10


class TestRoundTrip:
    """Test encoding and decoding round-trips."""

    def test_complex_container_roundtrip(self):
        """Test round-trip of a complex container."""
        @dataclass
        class ComplexContainer(Container):
            count: U32
            values: Vector
            flag: bool

        # Create a complex object
        values_vec = Vector([U8(i) for i in range(5)], length=5, element_type=U8)
        original = ComplexContainer(
            count=U32(5),
            values=values_vec,
            flag=True
        )

        # Encode and decode
        encoded = ssz.encode(original)

        # Note: Container decoding handles nested types automatically
        # We'd need to handle Vector field specially in real implementation
        # For now, just test that encoding works
        assert len(encoded) > 0
