"""
Tests for SSZ encoding and decoding.
"""

import pytest
from ethereum_types.bytes import Bytes, Bytes32
from ethereum_types.numeric import U8, U32, U64, U256, Uint

from ethereum_ssz import ssz
from ethereum_ssz.exceptions import DecodingError, EncodingError

#
# Tests for SSZ encode
#


def test_encode__bool_true() -> None:
    """Test encoding of True boolean."""
    assert ssz.encode(True) == bytes([0x01])


def test_encode__bool_false() -> None:
    """Test encoding of False boolean."""
    assert ssz.encode(False) == bytes([0x00])


def test_encode__uint8() -> None:
    """Test encoding of U8 (single byte unsigned integer)."""
    assert ssz.encode(U8(0)) == bytes([0x00])
    assert ssz.encode(U8(1)) == bytes([0x01])
    assert ssz.encode(U8(255)) == bytes([0xFF])


def test_encode__uint32() -> None:
    """Test encoding of U32 (4-byte unsigned integer)."""
    # SSZ uses little-endian encoding
    assert ssz.encode(U32(0)) == bytes([0x00, 0x00, 0x00, 0x00])
    assert ssz.encode(U32(1)) == bytes([0x01, 0x00, 0x00, 0x00])
    assert ssz.encode(U32(0x12345678)) == bytes([0x78, 0x56, 0x34, 0x12])


def test_encode__uint64() -> None:
    """Test encoding of U64 (8-byte unsigned integer)."""
    assert ssz.encode(U64(0)) == bytes([0x00] * 8)
    assert ssz.encode(U64(1)) == bytes([0x01] + [0x00] * 7)
    assert ssz.encode(U64(0x0123456789ABCDEF)) == bytes(
        [0xEF, 0xCD, 0xAB, 0x89, 0x67, 0x45, 0x23, 0x01]
    )


def test_encode__uint256() -> None:
    """Test encoding of U256 (32-byte unsigned integer)."""
    assert ssz.encode(U256(0)) == bytes([0x00] * 32)
    assert ssz.encode(U256(1)) == bytes([0x01] + [0x00] * 31)
    # Max U256 value
    max_u256 = U256(2**256 - 1)
    assert ssz.encode(max_u256) == bytes([0xFF] * 32)


def test_encode__bytes() -> None:
    """Test encoding of raw bytes."""
    assert ssz.encode(b"") == b""
    assert ssz.encode(b"hello") == b"hello"
    assert ssz.encode(bytes([0x00, 0x01, 0x02])) == bytes([0x00, 0x01, 0x02])


def test_encode__bytearray() -> None:
    """Test encoding of bytearray."""
    assert ssz.encode(bytearray(b"test")) == b"test"
    assert ssz.encode(bytearray([0x00, 0xFF])) == bytes([0x00, 0xFF])


def test_encode__string() -> None:
    """Test encoding of string (as UTF-8 bytes)."""
    assert ssz.encode("hello") == b"hello"
    assert ssz.encode("") == b""


#
# Tests for SSZ decode_to
#


def test_decode_to__bool() -> None:
    """Test decoding to boolean."""
    assert ssz.decode_to(bool, bytes([0x00])) is False
    assert ssz.decode_to(bool, bytes([0x01])) is True

    with pytest.raises(DecodingError):
        ssz.decode_to(bool, bytes([0x02]))  # Invalid boolean value

    with pytest.raises(DecodingError):
        ssz.decode_to(bool, bytes([]))  # Empty bytes

    with pytest.raises(DecodingError):
        ssz.decode_to(bool, bytes([0x00, 0x00]))  # Too many bytes


def test_decode_to__uint8() -> None:
    """Test decoding to U8."""
    assert ssz.decode_to(U8, bytes([0x00])) == U8(0)
    assert ssz.decode_to(U8, bytes([0x01])) == U8(1)
    assert ssz.decode_to(U8, bytes([0xFF])) == U8(255)


def test_decode_to__uint32() -> None:
    """Test decoding to U32."""
    assert ssz.decode_to(U32, bytes([0x00, 0x00, 0x00, 0x00])) == U32(0)
    assert ssz.decode_to(U32, bytes([0x01, 0x00, 0x00, 0x00])) == U32(1)
    assert ssz.decode_to(U32, bytes([0x78, 0x56, 0x34, 0x12])) == U32(
        0x12345678
    )


def test_decode_to__uint64() -> None:
    """Test decoding to U64."""
    assert ssz.decode_to(U64, bytes([0x00] * 8)) == U64(0)
    assert ssz.decode_to(U64, bytes([0x01] + [0x00] * 7)) == U64(1)
    assert ssz.decode_to(
        U64, bytes([0xEF, 0xCD, 0xAB, 0x89, 0x67, 0x45, 0x23, 0x01])
    ) == U64(0x0123456789ABCDEF)


def test_decode_to__uint256() -> None:
    """Test decoding to U256."""
    assert ssz.decode_to(U256, bytes([0x00] * 32)) == U256(0)
    assert ssz.decode_to(U256, bytes([0x01] + [0x00] * 31)) == U256(1)
    assert ssz.decode_to(U256, bytes([0xFF] * 32)) == U256(2**256 - 1)


def test_decode_to__bytes() -> None:
    """Test decoding to bytes."""
    assert ssz.decode_to(bytes, b"hello") == b"hello"
    assert ssz.decode_to(bytes, b"") == b""
    assert ssz.decode_to(Bytes, b"test") == Bytes(b"test")


def test_decode_to__bytes32() -> None:
    """Test decoding to Bytes32."""
    data = b"\x00" * 32
    assert ssz.decode_to(Bytes32, data) == Bytes32(data)

    data = b"\xff" * 32
    assert ssz.decode_to(Bytes32, data) == Bytes32(data)

    # Wrong length should raise error
    with pytest.raises(DecodingError):
        ssz.decode_to(Bytes32, b"\x00" * 31)

    with pytest.raises(DecodingError):
        ssz.decode_to(Bytes32, b"\x00" * 33)


#
# Round-trip tests
#


def test_roundtrip__bool() -> None:
    """Test round-trip encoding/decoding of booleans."""
    for value in [True, False]:
        encoded = ssz.encode(value)
        decoded = ssz.decode_to(bool, encoded)
        assert decoded == value


def test_roundtrip__uint8() -> None:
    """Test round-trip encoding/decoding of U8."""
    for value in [U8(0), U8(1), U8(127), U8(255)]:
        encoded = ssz.encode(value)
        decoded = ssz.decode_to(U8, encoded)
        assert decoded == value


def test_roundtrip__uint32() -> None:
    """Test round-trip encoding/decoding of U32."""
    test_values = [
        U32(0),
        U32(1),
        U32(256),
        U32(65536),
        U32(0x12345678),
        U32(0xFFFFFFFF),
    ]
    for value in test_values:
        encoded = ssz.encode(value)
        decoded = ssz.decode_to(U32, encoded)
        assert decoded == value


def test_roundtrip__uint64() -> None:
    """Test round-trip encoding/decoding of U64."""
    test_values = [
        U64(0),
        U64(1),
        U64(256),
        U64(65536),
        U64(0x0123456789ABCDEF),
        U64(0xFFFFFFFFFFFFFFFF),
    ]
    for value in test_values:
        encoded = ssz.encode(value)
        decoded = ssz.decode_to(U64, encoded)
        assert decoded == value


def test_roundtrip__uint256() -> None:
    """Test round-trip encoding/decoding of U256."""
    test_values = [
        U256(0),
        U256(1),
        U256(256),
        U256(2**128),
        U256(2**255),
        U256(2**256 - 1),
    ]
    for value in test_values:
        encoded = ssz.encode(value)
        decoded = ssz.decode_to(U256, encoded)
        assert decoded == value
