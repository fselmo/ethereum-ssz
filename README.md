# ethereum-ssz

SSZ (Simple Serialize) encoding and decoding for Ethereum types.

## Installation

```bash
pip install ethereum-ssz
```

## Usage

### Basic Types

```python
from ethereum_ssz import ssz
from ethereum_types.numeric import U8, U32, U64, U256
from ethereum_types.bytes import Bytes, Bytes32

# Encode basic types
encoded = ssz.encode(U64(12345))
print(encoded.hex())  # '3930000000000000' (little-endian)

# Decode to specific type
decoded = ssz.decode_to(U64, encoded)
assert decoded == U64(12345)

# Boolean encoding
encoded_true = ssz.encode(True)   # b'\x01'
encoded_false = ssz.encode(False) # b'\x00'

# Bytes encoding
data = Bytes32(b'\xFF' * 32)
encoded = ssz.encode(data)
decoded = ssz.decode_to(Bytes32, encoded)
assert decoded == data
```

### Composite Types

```python
from ethereum_ssz.composite import Vector, List as SSZList
from ethereum_types.numeric import U32, U64

# Fixed-length Vector
vec = Vector([U32(1), U32(2), U32(3)], length=3, element_type=U32)
encoded = ssz.encode(vec)

# Variable-length List (with max length)
lst = SSZList([U64(100), U64(200)], max_length=10, element_type=U64)
lst.append(U64(300))  # Can append up to max_length
encoded = ssz.encode(lst)
```

### Merkleization (hash_tree_root)

```python
from ethereum_ssz import hash_tree_root
from ethereum_types.numeric import U64
from ethereum_ssz.composite import Vector

# Hash tree root of basic types
htr = hash_tree_root(U64(12345))
print(htr.hex())  # Merkle root as hex

# Hash tree root of composite types
vec = Vector([U64(1), U64(2), U64(3), U64(4)], length=4, element_type=U64)
htr = hash_tree_root(vec)
print(htr.hex())  # Merkle root of the vector
```

## Features

- ✅ Basic type encoding/decoding (bool, integers, bytes)
- ✅ Full support for ethereum-types (U8, U32, U64, U256, Bytes, FixedBytes)
- ✅ Little-endian encoding for integers (SSZ standard)
- ✅ Fixed-length vectors (Vector)
- ✅ Variable-length lists with max length (List)
- ✅ Merkleization support (hash_tree_root)
- 🚧 Containers (struct-like composites) - Coming soon
- 🚧 Pydantic model support - Coming soon
- 🚧 Offset encoding for variable-size elements - Coming soon
- 🚧 Decoding for composite types - Coming soon

## Development

This library provides SSZ serialization support for `ethereum-types`, following the same API patterns as `ethereum-rlp`.

### Testing

```bash
pip install -e .[dev]
pytest
```

### Type Checking

```bash
mypy -p ethereum_ssz
```