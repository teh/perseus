import ast
import itertools

from perseus import frozendict
from perseus.test._inspector import FrozenDictInspector, bitcount, index, bitpos

from testtools import TestCase


class HashTester(object):

    def __init__(self, hashObj, hashVal=None):
        self.hashval = hashVal or hash(hashObj)
        self.hashObj = hashObj


    def __hash__(self):
        return self.hashval


    def __repr__(self):
        return "<HashTester hash(%s)>" % (repr(self.hashObj),)



class FrozenDictTests(TestCase):
    """
    Tests for L{frozendict}.
    """

    def test_empty(self):
        """
        The empty frozendict is of length 0 and has no keys or values.
        """
        d = frozendict()
        self.assertEqual(len(d), 0)
        self.assertEqual(tuple(d.keys()), ())
        self.assertEqual(tuple(d.values()), ())
        self.assertEqual(tuple(d.items()), ())
        self.assertRaises(KeyError, lambda: d['a'])
        self.assertEqual(d.get('a', 'b'), 'b')
        self.assertFalse('a' in d)


    def test_emptyRoot(self):
        """
        The root node of an empty frozendict is None.
        """
        d = frozendict()
        di = FrozenDictInspector(d)
        self.assertEqual(di.root, None)



    def test_assocFromEmpty(self):
        """
        Adding an association to the empty frozendict creates a frozendict
        containing a single pair.
        """
        k, v = ('stuff', 42)
        d = frozendict()
        d2 = d.withPair(k, v)
        self.assertEqual(len(d2), 1)
        self.assertEqual(d2[k], v)
        self.assertTrue(k in d2)
        self.assertEqual(tuple(d2.keys()), (k,))
        self.assertEqual(tuple(d2.values()), (v,))
        self.assertEqual(tuple(d2.items()), ((k, v),))
        #different-hashed keys fail properly
        self.assertRaises(KeyError, lambda: d2['a'])
        self.assertFalse('a' in d2)
        #so do same-hashed keys
        self.assertRaises(KeyError, lambda: d2[HashTester('stuff')])
        self.assertFalse(HashTester('stuff') in d2)


    def test_duplicateAssoc(self):
        """
        The same frozendict is returned if an existing pair is added to it.
        """
        k, v = ('stuff', 42)
        d = frozendict()
        d2 = d.withPair(k, v)
        d3 = d2.withPair(k, v)
        self.assertTrue(d2 is d3)


    def test_replaceAssoc(self):
        """
        Calling withPair with a key existing in the frozendict creates a new
        frozendict with the given value replacing the existing one.
        """
        k, v = ('stuff', 42)
        d = frozendict()
        d2 = d.withPair(k, v)
        d3 = d2.withPair(k, 24)
        self.assertEqual(d2[k], v)
        self.assertEqual(d3[k], 24)
        self.assertEqual(len(d2), 1)
        self.assertEqual(len(d3), 1)


    def test_assocFromEmptyInternals(self):
        """
        Adding an association to the empty frozendict creates a frozendict
        containing a bitmap-indexed node, which contains only the requested pair.

        Furthermore, only one bit is set in the bitmap, it's in the rightmost
        region, and is correctly positioned for the key's hash.
        """
        k, v = ('stuff', 42)
        d = frozendict()
        d2 = d.withPair(k, v)
        di = FrozenDictInspector(d2)
        self.assertEqual(di.root.kind, 'BitmapIndexedNode')
        self.assertEqual(bitcount(di.root.bitmap), 1)
        self.assertNotEqual(di.root.bitmap & bitpos(hash(k), 0), 0)
        i = index(di.root.bitmap, bitpos(hash(k), 0))
        self.assertEqual(di.root.array[2*i], k)
        self.assertEqual(di.root.array[2*i+1], v)


    def test_nearlyFullNode(self):
        """
        Up to 15 entries can go into a single bitmap-indexed node.
        """

        vals = 'abcdefghijklmnop'
        d = frozendict()
        #integers hash to themselves, so no collisions here
        for i in range(16):
            d = d.withPair(i, vals[i])
        self.assertEqual(len(d), 16)
        self.assertEqual(set(d.keys()), set(range(16)))
        self.assertEqual(set(d.values()), set(vals))
        self.assertEqual(set(d.items()), set(zip(range(16), vals)))
        di = FrozenDictInspector(d)
        self.assertEqual(di.root.kind, 'BitmapIndexedNode')
        self.assertEqual(di.count, 16)
        self.assertEqual(bitcount(di.root.bitmap), 16)
        self.assertEqual(len(di.root.array), 32)
        self.assertEqual(set(di.root.array[::2]), set(range(16)))
        self.assertEqual(set(di.root.array[1::2]), set(vals))


    def test_convertToFullNode(self):
        """
        Nodes with 16 entries are converted to ArrayNodes.
        """
        d = frozendict()
        vals = 'abcdefghijklmnopq'
        for i in range(17):
            d = d.withPair(i, vals[i])
        self.assertEqual(len(d), 17)
        self.assertEqual(set(d.keys()), set(range(17)))
        self.assertEqual(set(d.values()), set(vals))
        self.assertEqual(set(d.items()), set(zip(range(17), vals)))
        di = FrozenDictInspector(d)
        self.assertEqual(di.root.kind, 'ArrayNode')
        self.assertEqual(di.count, 17)
        for i in range(17):
            self.assertEqual(di.root.array[i].kind, 'BitmapIndexedNode')


    def test_handleCollision(self):
        """
        Adding a pair to frozendict whose key has the same hash value as an existing key succeeds.
        """
        d = frozendict()
        k1, v1 = 'stuff', 42
        k2, v2 = HashTester(k1), 43
        d2 = d.withPair(k1, v1)
        d3 = d2.withPair(k2, v2)
        self.assertEqual(set(d3.keys()), set([k1, k2]))
        self.assertEqual(set(d3.values()), set([v1, v2]))
        self.assertEqual(set(d3.items()), set([(k1, v1), (k2, v2)]))
        self.assertEqual(len(d3), 2)
        self.assertEqual(d3[k1], v1)
        self.assertEqual(d3[k2], v2)


    def test_convertCollisionToFull(self):
        """
        Conversion to ArrayNodes works when the converted node contains collision subnodes.
        """
        k1, v1 = HashTester(0), 'collision'
        d = frozendict().withPair(k1, v1)
        vals = 'abcdefghijklmnopqr'
        for i in range(18):
            d = d.withPair(i, vals[i])

        k2, v2 = HashTester(1), 'collision'
        d = d.withPair(k2, v2)
        self.assertEqual(len(d), 20)
        self.assertEqual(set(d.items()), set([(k1, v1), (k2, v2)] + zip(range(18), vals)))
        di = FrozenDictInspector(d)
        self.assertEqual(di.root.kind, 'ArrayNode')
        self.assertEqual(di.count, 20)
        self.assertEqual(di.root.array[0].kind, "HashCollisionNode")
        for i in range(1, 16):
            self.assertEqual(di.root.array[i].kind, 'BitmapIndexedNode')


        for k, v  in zip([k1, k2] + range(18), [v1, v2] + list(vals)):
            self.assertEqual(d[k], v)
            self.assertEqual(d.get(k), v)

        self.assertRaises(KeyError, lambda: d[20])
        self.assertEqual(d.get(20, 'x'), 'x')
        self.assertTrue(d.withPair(k2, v2) is d)


    def test_handleExtraCollision(self):
        """
        Multiple keys with the same hash are accepted by frozendict.
        """
        k1, v1 = 'stuff', 42
        k2, v2 = HashTester(k1), 43
        k3, v3 = HashTester(k1), 44
        d = frozendict().withPair(k1, v1).withPair(k2, v2).withPair(k3, v3)
        self.assertEqual(set(d.items()), set([(k1, v1), (k2, v2), (k3, v3)]))


    def test_handleFalseCollision(self):
        """
        HashCollisionNodes deal with lookups for nonexistent keys.
        """

        k1, v1 = 'stuff', 42
        k2, v2 = HashTester('stuff'), 43
        d = frozendict().withPair(k1, v1).withPair(k2, v2)
        self.assertRaises(KeyError, lambda: d[HashTester(k1)])


    def test_updateExtraCollision(self):
        """
        Multiple keys with the same hash are accepted by frozendict.
        """
        k1, v1 = 'stuff', 42
        k2, v2 = HashTester(k1), 43
        k3, v3 = HashTester(k1), 44
        k3, v3 = HashTester(k1), 44
        d = frozendict().withPair(k1, v1).withPair(k2, v2).withPair(k3, v3)
        d2 = d.withPair(k2, 45)
        self.assertEqual(set(d.items()), set([(k1, v1), (k2, v2), (k3, v3)]))
        self.assertEqual(set(d2.items()), set([(k1, v1), (k2, 45), (k3, v3)]))

        self.assertTrue(d.withPair(k2, v2) is d)


    def test_localOnlyCollision(self):
        """
        Keys that collide within a node's 5-bit window result in the creation of a new BitmapIndexedNode.
        """
        k1, v1 = HashTester("stuff", 0x17), 42
        k2, v2 = HashTester("morestuff", 0x37), 43
        d = frozendict().withPair(k1, v1).withPair(k2, v2)
        self.assertEqual(len(d), 2)
        self.assertEqual(set(d.items()), set([(k1, v1), (k2, v2)]))
        di = FrozenDictInspector(d)
        self.assertEqual(di.root.kind, 'BitmapIndexedNode')
        self.assertEqual(di.root.array[1].kind, 'BitmapIndexedNode')


    def test_doubleMixedCollision(self):
        """
        A collision in the local 5-bit window with a hash collision node nests
        it in a bitmap node.
        """
        k1, v1 = HashTester("stuff", 0x17), 42
        k1a, v1a = HashTester("stuff", 0x17), 44
        k2, v2 = HashTester("morestuff", 0x37), 43
        d = frozendict().withPair(k1, v1).withPair(k1a, v1a).withPair(k2, v2)
        self.assertEqual(len(d), 3)
        self.assertEqual(set(d.items()), set([(k1, v1), (k1a, v1a), (k2, v2)]))


    def test_hashEq(self):
        """
        frozendicts are hashable and compare properly for equality.
        """
        d0a, d0b = frozendict(), frozendict()
        self.assertEqual(hash(d0a), hash(d0b), "empty frozendicts don't hash the same")
        self.assertEqual(d0a, d0b, "empty frozendicts don't compare equal")
        self.assertEqual(d0a, d0a)
        self.assertNotEqual(d0a, {})

        k1, v1 = HashTester(0), 'collision'
        d1a = frozendict().withPair(k1, v1)
        d1b = frozendict().withPair(k1, v1)
        vals = 'abcdefghijklmnopqr'
        for i in range(18):
            d1a = d1a.withPair(i, vals[i])
            d1b = d1b.withPair(i, vals[i])
        k2, v2 = HashTester(1), 'collision'
        d1a = d1a.withPair(k2, v2)
        d1b = d1b.withPair(k2, v2)

        self.assertEqual(hash(d1a), hash(d1b), "equal frozendicts don't hash the same")

        #explicitly using '==' and '!=' here to avoid guessing which the assert method calls.
        self.assertFalse(d1a == d0a)
        self.assertTrue(d1a != d0a)
        self.assertTrue(d1a == d1b, "equal frozendicts don't compare equal")
        self.assertFalse(d1a != d1b)
        self.assertFalse(d1b.withPair('extra', 'pair') == d1b.withPair('extra', HashTester('pair')))
        self.assertTrue(d1b.withPair('extra', 'pair') != d1b.withPair('extra', HashTester('pair')))


    def test_emptyWithout(self):
        """
        Empty frozendicts support 'without'.
        """
        d = frozendict()
        self.assertEqual(d.without('something'), d)


    def test_bitmappedNodeWithout(self):
        """
        Non-full nodes support 'without'.
        """
        k, v = ('stuff', 42)
        d = frozendict()
        d2 = d.withPair(k, v)
        self.assertEqual(d, d2.without(k))
        self.assertEqual(d2, d2.without('nothing'))


    def test_mixedNodeWithout(self):
        """
        Bitmapped nodes delegate 'without' to subnodes properly.
        """
        k1, v1 = HashTester("stuff", 0x17), 42
        k1a, v1a = HashTester("stuff", 0x17), 44
        k2, v2 = HashTester("morestuff", 0x37), 43
        d = frozendict().withPair(k1, v1).withPair(k1a, v1a).withPair(k2, v2)
        self.assertTrue(d.without(HashTester("stuff", 0x17)) is d)
        self.assertEqual(d.without(k1).without(k1a), frozendict().withPair(k2, v2))
        self.assertEqual(d.without(k2).without(k1).without(k1a), frozendict())


    def test_arrayNodeWithout(self):
        """
        'without' calls propagate through array nodes.
        """
        d = frozendict()
        vals = 'abcdefghijklmnopq'
        for i in range(17):
            previousD = d
            d = d.withPair(i, vals[i])
        self.assertEqual(previousD, d.without(16))
        self.assertTrue(d.without(HashTester(13)) is d)
        self.assertTrue(d.without(HashTester(27)) is d)


    def test_hashCollisionNodeWithout(self):
        """
        'without' works with hash collision nodes.
        """
        k1, v1 = HashTester(0), 'collision'
        d = frozendict().withPair(k1, v1)
        vals = 'abcdefghijklmnopqr'
        for i in range(18):
            d = d.withPair(i, vals[i])

        k2, v2 = HashTester(1), 'collision'
        d2 = d.withPair(k2, v2)

        self.assertEqual(d2.without(k2), d)
        self.assertTrue(d2.without(HashTester(k1)) is d2)


    def test_repackArrayNode(self):
        """
        When array nodes fall below 8 children, they're repacked into
        bitmapped nodes.
        """
        d = frozendict()
        vals = 'abcdefghijklmnopq'
        for i in range(17):
            d = d.withPair(i, vals[i])
        for i in range(10):
            d = d.without(i)
        di = FrozenDictInspector(d)
        self.assertEqual(bitcount(di.root.bitmap), 7)
        self.assertEqual(di.root.kind, "BitmapIndexedNode")
        self.assertEqual(d, frozendict(zip(itertools.count(10), list("klmnopq"))))


    def test_withUpdate(self):
        """
        frozendicts can be constructed from other mappings and sequences.
        """
        f = frozendict([(1, 2)])
        self.assertEqual(f, frozendict().withPair(1, 2))
        self.assertEqual(f, frozendict({1: 2}))
        self.assertEqual(f, frozendict([(1, 2)]))
        self.assertEqual(f, frozendict().withUpdate({1: 2}))


    def test_repr(self):
        """
        repr() for frozendicts is congruent to repr() for dicts.
        """
        md = {"stuff": 1,  17: [1, 2, 'a']}
        fd = frozendict()
        for k, v in md.iteritems():
            fd = fd.withPair(k, v)
        fr = repr(fd)
        self.assertTrue(fr.startswith("frozendict("))
        self.assertTrue(fr.endswith(")"))
        self.assertTrue(ast.literal_eval(fr[11:-1]), md)
