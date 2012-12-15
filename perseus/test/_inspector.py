__all__ = [
    'bitcount',
    'bitpos',
    'FrozenDictInspector',
    'index',
    ]

from perseus._hamt import bitcount, bitpos, index

def FrozenDictInspector(x):
    return x
