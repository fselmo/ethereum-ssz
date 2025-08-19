#!/usr/bin/env python3
from dataclasses import dataclass

from ethereum_types.numeric import U8

from ethereum_ssz import U16, Container
from ethereum_ssz import List as SSZList
from ethereum_ssz.composite import is_variable_size


@dataclass
class VarTestStruct(Container):
    A: U16
    B: SSZList  # List[uint16, 1024]
    C: U8

print(f'VarTestStruct is variable: {is_variable_size(VarTestStruct)}')
print(f'VarTestStruct fields: {VarTestStruct.get_fields()}')

# Check the B field
for name, field_type in VarTestStruct.get_fields():
    print(f'Field {name}: type={field_type}, is_variable={is_variable_size(field_type)}')
