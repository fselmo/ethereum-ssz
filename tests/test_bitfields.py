"""
Test bitfield types adapted from remerkleable.

These tests verify SSZ encoding and hash tree root of Bitvector and Bitlist.
"""

import hashlib

from ethereum_types.bytes import Bytes32

from ethereum_ssz import Bitlist, Bitvector, hash_tree_root, ssz


def sha256(data: bytes) -> bytes:
    """SHA256 hash helper."""
    return hashlib.sha256(data).digest()


def h(a: bytes, b: bytes) -> bytes:
    """Hash two 32-byte chunks together."""
    if isinstance(a, str):
        a = bytes.fromhex(a)
    if isinstance(b, str):
        b = bytes.fromhex(b)
    return sha256(a + b)


def chunk(data: str) -> bytes:
    """Pad hex string to 32 bytes."""
    if isinstance(data, str):
        data = bytes.fromhex(data)
    if len(data) >= 32:
        return data[:32]
    return data + b'\x00' * (32 - len(data))


class TestBitvector:
    """Test Bitvector functionality with exact test vectors."""

    def test_bitvector_TTFTFTFF(self):
        """Test Bitvector[8] with pattern TTFTFTFF."""
        # TTFTFTFF = 11010100 in binary (reading left to right)
        # In little-endian bit encoding: bit 0=1, bit 1=1, bit 2=0, bit 3=1, bit 4=0, bit 5=1, bit 6=0, bit 7=0
        # This gives byte value: 0x2b (00101011 in binary)
        bv = Bitvector([1, 1, 0, 1, 0, 1, 0, 0], length=8)

        # Test serialization
        encoded = ssz.encode(bv)
        assert encoded == b'\x2b'

        # Test hash tree root - should be chunk("2b")
        htr = hash_tree_root(bv)
        expected = Bytes32(chunk("2b"))
        assert htr == expected

    def test_bitvector_FTFT(self):
        """Test Bitvector[4] with pattern FTFT."""
        # FTFT = 0101 in binary (reading left to right)
        # In little-endian: bit 0=0, bit 1=1, bit 2=0, bit 3=1
        # This gives: 0x0a (00001010 in binary)
        bv = Bitvector([0, 1, 0, 1], length=4)

        encoded = ssz.encode(bv)
        assert encoded == b'\x0a'

        htr = hash_tree_root(bv)
        expected = Bytes32(chunk("0a"))
        assert htr == expected

    def test_bitvector_FTF(self):
        """Test Bitvector[3] with pattern FTF."""
        # FTF = 010 in binary
        # In little-endian: bit 0=0, bit 1=1, bit 2=0
        # This gives: 0x02 (00000010 in binary)
        bv = Bitvector([0, 1, 0], length=3)

        encoded = ssz.encode(bv)
        assert encoded == b'\x02'

        htr = hash_tree_root(bv)
        expected = Bytes32(chunk("02"))
        assert htr == expected

    def test_bitvector_TFTFFFTTFT(self):
        """Test Bitvector[10] with pattern TFTFFFTTFT."""
        # TFTFFFTTFT = 1010001101 in binary
        # In little-endian: bits = [1,0,1,0,0,0,1,1,0,1]
        # Byte 0: 11000101 = 0xc5
        # Byte 1: 00000010 = 0x02
        # Result: 0xc502
        bv = Bitvector([1, 0, 1, 0, 0, 0, 1, 1, 0, 1], length=10)

        encoded = ssz.encode(bv)
        assert encoded == b'\xc5\x02'

        htr = hash_tree_root(bv)
        expected = Bytes32(chunk("c502"))
        assert htr == expected

    def test_bitvector_TFTFFFTTFTFFFFTT(self):
        """Test Bitvector[16] with pattern TFTFFFTTFTFFFFTT."""
        # In little-endian bit order:
        # bits = [1,0,1,0,0,0,1,1,0,1,0,0,0,0,1,1]
        # Byte 0: 11000101 = 0xc5
        # Byte 1: 11000010 = 0xc2
        bv = Bitvector([1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1], length=16)

        encoded = ssz.encode(bv)
        assert encoded == b'\xc5\xc2'

        htr = hash_tree_root(bv)
        expected = Bytes32(chunk("c5c2"))
        assert htr == expected

    def test_long_bitvector_512(self):
        """Test Bitvector[512] with all bits set."""
        bv = Bitvector([1] * 512, length=512)

        encoded = ssz.encode(bv)
        assert encoded == b'\xff' * 64

        # For 512 bits = 64 bytes = 2 chunks, merkle root is h(chunk1, chunk2)
        htr = hash_tree_root(bv)
        expected = Bytes32(h(b'\xff' * 32, b'\xff' * 32))
        assert htr == expected

    def test_odd_bitvector_513(self):
        """Test Bitvector[513] with all bits set."""
        bv = Bitvector([1] * 513, length=513)

        encoded = ssz.encode(bv)
        # 513 bits = 65 bytes
        assert encoded == b'\xff' * 64 + b'\x01'

        # 513 bits = 65 bytes = 3 chunks, need to merkleize properly
        htr = hash_tree_root(bv)
        # h(h(chunk0, chunk1), h(chunk2, zero))
        expected = Bytes32(h(
            h(b'\xff' * 32, b'\xff' * 32),
            h(chunk("01"), chunk(""))
        ))
        assert htr == expected


class TestBitlist:
    """Test Bitlist functionality with exact test vectors."""

    def test_bitlist_empty(self):
        """Test empty Bitlist[8]."""
        bl = Bitlist([], max_length=8)

        # Empty bitlist encodes as just the sentinel bit
        encoded = ssz.encode(bl)
        assert encoded == b'\x01'

        # Hash tree root: h(chunk(""), chunk("00"))
        htr = hash_tree_root(bl)
        expected = Bytes32(h(chunk(""), chunk("00")))
        assert htr == expected

    def test_bitlist_TTFTFTFF(self):
        """Test Bitlist[8] with pattern TTFTFTFF."""
        bl = Bitlist([1, 1, 0, 1, 0, 1, 0, 0], max_length=8)

        # Bits: 11010100 = 0x2b
        # With sentinel at position 8: 100101011 = 0x012b (little-endian)
        encoded = ssz.encode(bl)
        assert encoded == b'\x2b\x01'

        # Hash tree root: h(chunk("2b"), chunk("08"))
        htr = hash_tree_root(bl)
        expected = Bytes32(h(chunk("2b"), chunk("08")))
        assert htr == expected

    def test_bitlist_FTFT(self):
        """Test Bitlist[4] with pattern FTFT."""
        bl = Bitlist([0, 1, 0, 1], max_length=4)

        # Bits: 0101 = 0x0a
        # With sentinel at position 4: 10101 = 0x1a
        encoded = ssz.encode(bl)
        assert encoded == b'\x1a'

        # Hash tree root: h(chunk("0a"), chunk("04"))
        htr = hash_tree_root(bl)
        expected = Bytes32(h(chunk("0a"), chunk("04")))
        assert htr == expected

    def test_bitlist_FTF(self):
        """Test Bitlist[3] with pattern FTF."""
        bl = Bitlist([0, 1, 0], max_length=3)

        # Bits: 010 = 0x02
        # With sentinel at position 3: 1010 = 0x0a
        encoded = ssz.encode(bl)
        assert encoded == b'\x0a'

        # Hash tree root: h(chunk("02"), chunk("03"))
        htr = hash_tree_root(bl)
        expected = Bytes32(h(chunk("02"), chunk("03")))
        assert htr == expected

    def test_bitlist_TFTFFFTTFT(self):
        """Test Bitlist[16] with pattern TFTFFFTTFT (10 bits)."""
        bl = Bitlist([1, 0, 1, 0, 0, 0, 1, 1, 0, 1], max_length=16)

        # Bits: 1010001101 = 0xc502
        # With sentinel at position 10: 11010001101 = 0x06c5
        encoded = ssz.encode(bl)
        assert encoded == b'\xc5\x06'

        # Hash tree root: h(chunk("c502"), chunk("0a"))
        htr = hash_tree_root(bl)
        expected = Bytes32(h(chunk("c502"), chunk("0a")))
        assert htr == expected

    def test_bitlist_TFTFFFTTFTFFFFTT(self):
        """Test Bitlist[16] with all 16 bits."""
        bl = Bitlist([1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1], max_length=16)

        # Bits: 1010001101000011 = 0xc2c5
        # With sentinel at position 16: 11010001101000011 = 0x01c2c5
        encoded = ssz.encode(bl)
        assert encoded == b'\xc5\xc2\x01'

        # Hash tree root: h(chunk("c5c2"), chunk("10"))
        htr = hash_tree_root(bl)
        expected = Bytes32(h(chunk("c5c2"), chunk("10")))
        assert htr == expected

    def test_long_bitlist_single_bit(self):
        """Test Bitlist[512] with single bit set."""
        bl = Bitlist([1], max_length=512)

        # Single bit plus sentinel: 11 = 0x03
        encoded = ssz.encode(bl)
        assert encoded == b'\x03'

        # Hash tree root
        htr = hash_tree_root(bl)
        # Contents root for 512 max = depth 2
        # h(h(chunk("01"), chunk("")), chunk("01"))
        expected = Bytes32(h(h(chunk("01"), chunk("")), chunk("01")))
        assert htr == expected

    def test_long_bitlist_full_512(self):
        """Test Bitlist[512] with all 512 bits set."""
        bl = Bitlist([1] * 512, max_length=512)

        # 512 bits of 1s plus sentinel
        encoded = ssz.encode(bl)
        assert encoded == b'\xff' * 64 + b'\x01'

        # Hash tree root
        htr = hash_tree_root(bl)
        # h(h(ff*32, ff*32), chunk("0002"))
        expected = Bytes32(h(h(b'\xff' * 32, b'\xff' * 32), chunk("0002")))
        assert htr == expected

    def test_odd_bitlist_513_full(self):
        """Test Bitlist[513] with all 513 bits set."""
        bl = Bitlist([1] * 513, max_length=513)

        # 513 bits of 1s plus sentinel at position 513
        encoded = ssz.encode(bl)
        assert encoded == b'\xff' * 64 + b'\x03'

        # Hash tree root
        htr = hash_tree_root(bl)
        # Contents: h(h(ff*32, ff*32), h(chunk("01"), chunk("")))
        # Mixed with length: h(contents, chunk("0102"))
        contents = h(
            h(b'\xff' * 32, b'\xff' * 32),
            h(chunk("01"), chunk(""))
        )
        expected = Bytes32(h(contents, chunk("0102")))
        assert htr == expected
