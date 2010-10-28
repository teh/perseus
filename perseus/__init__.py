#XXX redo with array-edit versions since we can rely on GIL

class frozendict(object):
    def __init__(self):
        self.root = None
        self.count = 0
        self._hash = None


    def __len__(self):
        return self.count


    def __getitem__(self, key):
        if self.root is None:
            raise KeyError(key)
        val = self.root.find(0, hash(key), key)
        if val is _not_found:
            raise KeyError(key)
        else:
            return val


    def get(self, key, default=None):
        if self.root is None:
            return default
        val = self.root.find(0, hash(key), key)
        if val is _not_found:
            return default
        else:
            return val


    def __contains__(self, key):
        if self.root is None:
            return False
        else:
            return self.root.find(0, hash(key), key) is not _not_found

    def __hash__(self):
        if self._hash is not None:
            return self._hash
        hashval = 0x3039
        for k, v in self.items():
            hashval += hash(k) ^ hash(v)
        self._hash = hashval
        return hashval


    def __eq__(self, other):
        if self is other:
            return True
        if not self.__class__ == other.__class__:
            return False
        if len(self) != len(other) or hash(self) != hash(other):
            return False
        for k, v in self.items():
            otherV = other.get(k, _not_found)
            if otherV is _not_found or v != otherV:
                return False
        return True


    def __ne__(self, other):
        #If you ever thought Python was good, this is where you can stop.
        return not self.__eq__(other)


    def keys(self):
        if self.root is None:
            return
        else:
            for k, v in self.root.iteritems():
                yield k


    def values(self):
        if self.root is None:
            return
        else:
            for k, v in self.root.iteritems():
                yield v


    def items(self):
        if self.root is None:
            return (x for x in ())
        else:
            return self.root.iteritems()


    def withPair(self, k, v):
        if self.root is None:
            newroot = EMPTY_BITMAP_INDEXED_NODE
        else:
            newroot = self.root

        newroot, addedLeaf = newroot.assoc(0, hash(k), k, v)

        if newroot is self.root:
            return self

        newf = frozendict()
        newf.count = self.count
        newf.root = newroot
        if addedLeaf:
            newf.count = self.count + 1
        return newf


    def without(self, k):
        if self.root is None:
            return self
        newroot = self.root.without(0, hash(k), k)
        if newroot is _absent:
            return frozendict()
        if newroot is self.root:
            return self
        else:
            newf = frozendict()
            newf.count = self.count - 1
            newf.root = newroot
            return newf


    def __repr__(self):
        #for today, we're straight up cheatin'
        d = dict(self)
        return "frozendict(%r)" % (d,)



_absent = object()
_not_found = object()

class _BitmapIndexedNode(object):
    kind = 'BitmapIndexedNode'
    def __init__(self, bitmap, array):
        self.bitmap = bitmap
        self.array = array


    def iteritems(self):
        for i in range(0, len(self.array), 2):
            if self.array[i] is _absent:
                for item in self.array[i + 1].iteritems():
                    yield item
            else:
                yield (self.array[i], self.array[i + 1])


    def find(self, shift, keyHash, key):
        bit = bitpos(keyHash, shift)
        if (self.bitmap & bit) == 0:
            return _not_found
        idx = index(self.bitmap, bit)
        k = self.array[2 * idx]
        v = self.array[2 * idx + 1]
        if k is _absent:
            return v.find(shift + 5, keyHash, key)
        if k == key:
            return v
        else:
            return _not_found


    def assoc(self, shift, keyHash, key, val):
        """
        Create new nodes as needed to include a new key/val pair.
        """
        bit = bitpos(keyHash, shift)
        idx = index(self.bitmap, bit)
        #look up hash in the current node
        if(self.bitmap & bit) != 0:
            #this spot's already occupied.
            someKey = self.array[2 * idx]
            someVal = self.array[2 * idx + 1]
            if someKey is _absent:
                #value slot is a subnode
                n, addedLeaf = someVal.assoc(shift + 5, keyHash, key, val)
                if n is someVal:
                    return self, False
                else:
                    newArray = self.array[:]
                    newArray[2 * idx + 1] = n
                    return _BitmapIndexedNode(self.bitmap, newArray), addedLeaf
            if key == someKey:
                if val == someVal:
                    return self, False
                else:
                    newArray = self.array[:]
                    newArray[2 * idx + 1] = val
                    return _BitmapIndexedNode(self.bitmap, newArray), False
            else:
                #there was a hash collision in the local 5 bits of the bitmap
                newArray = self.array[:]
                newArray[2 * idx] = _absent
                newArray[2 * idx + 1] = createNode(shift + 5, someKey,
                                                   someVal, keyHash, key, val)
                newNode = _BitmapIndexedNode(self.bitmap, newArray)
                return newNode, True
        else:
            #spot for this hash is open
            n = bitcount(self.bitmap)
            if n >= 16:
                # this node is full, convert to ArrayNode
                nodes = [_absent] * 32
                jdx = mask(keyHash, shift)
                nodes[jdx], addedLeaf = EMPTY_BITMAP_INDEXED_NODE.assoc(
                    shift + 5, keyHash, key, val)
                j = 0
                for i in range(32):
                    if ((self.bitmap >> i) & 1) != 0:
                        if self.array[j] is _absent:
                            nodes[i] = self.array[j + 1]
                        else:
                            nodes[i], al = EMPTY_BITMAP_INDEXED_NODE.assoc(
                                shift + 5, hash(self.array[j]),
                                self.array[j], self.array[j + 1])
                            addedLeaf = True
                    j += 2
                return _ArrayNode(n + 1, nodes), addedLeaf
            else:
                newArray = [_absent] * (2 * (n + 1))
                newArray[:2 * idx] =  self.array[:2 * idx]
                newArray[2 * idx] = key
                newArray[2 * idx + 1] = val
                newArray[2 * (idx + 1):2 * (n + 1)] = self.array[2 * idx:2 * n]
                return _BitmapIndexedNode(self.bitmap | bit, newArray), True


    def without(self, shift, keyHash, key):
        bit = bitpos(keyHash, shift)
        if (self.bitmap & bit) == 0:
            return self
        idx = index(self.bitmap, bit)
        someKey = self.array[2 * idx]
        someVal = self.array[(2 * idx) + 1]
        if someKey is _absent:
            # delegate to subnode
            n = someVal.without(shift + 5, keyHash, key)
            if n is someVal:
                return self
            if n is not _absent:
                newArray = self.array[:]
                newArray[2 * idx + 1] = n
                return _BitmapIndexedNode(self.bitmap, newArray)
            if self.bitmap == bit:
                return _absent
            newArray = self.array[:]
            del newArray[2 * idx:2 * idx + 2]
            return _BitmapIndexedNode(self.bitmap ^ bit, newArray)
        if someKey == key:
            newArray = self.array[:]
            del newArray[2 * idx:2 * idx + 2]
            return _BitmapIndexedNode(self.bitmap ^ bit, newArray)
        else:
            return self



EMPTY_BITMAP_INDEXED_NODE = _BitmapIndexedNode(0, [])


class _ArrayNode(object):
    kind = "ArrayNode"

    def __init__(self, count, array):
        self.count = count
        self.array = array


    def iteritems(self):
        for node in self.array:
            if node is not _absent:
                for item in node.iteritems():
                    yield item


    def find(self, shift, keyHash, key):
        idx = mask(keyHash, shift)
        node = self.array[idx]
        if node is _absent:
            return _not_found
        else:
            return node.find(shift + 5, keyHash, key)



    def assoc(self, shift, keyHash, key, val):
        idx = mask(keyHash, shift)
        node = self.array[idx]
        if node is _absent:
            newArray = self.array[:]
            newArray[idx], _ = EMPTY_BITMAP_INDEXED_NODE.assoc(shift + 5, keyHash, key, val)
            return _ArrayNode(self.count + 1, newArray), True
        else:
            n, addedLeaf = node.assoc(shift + 5, keyHash, key, val)
            if n is node:
                return self, False
            newArray = self.array[:]
            newArray[idx] = n
            return _ArrayNode(self.count, newArray), addedLeaf


    def without(self, shift, keyHash, key):
        idx = mask(keyHash, shift)
        node = self.array[idx]
        if node is _absent:
            return self
        n = node.without(shift + 5, keyHash, key)
        if n is node:
            return self
        newArray = self.array[:]
        newArray[idx] = n
        if n is _absent:
            if self.count <= 8:
                return self.pack(None, idx)
            return _ArrayNode(self.count - 1, newArray)
        else:
            return _ArrayNode(self.count, newArray)



class _HashCollisionNode(object):
    kind = "HashCollisionNode"

    def __init__(self, hash, count, array):
        self.hash = hash
        self.count = count
        self.array = array


    def iteritems(self):
        for i in range(0, len(self.array), 2):
            yield (self.array[i], self.array[i + 1])


    def find(self, shift, keyHash, key):
        try:
            idx = 2 * self.array[::2].index(key)
        except ValueError:
            return _not_found
        return self.array[idx + 1]


    def assoc(self, shift, keyHash, key, val):
        if keyHash == self.hash:
            try:
                idx = 2 * self.array[::2].index(key)
            except ValueError:
                newArray = self.array[:]
                newArray.extend([key, val])
                return _HashCollisionNode(self.hash, self.count + 1, newArray), True
            else:
                if self.array[idx + 1] == val:
                    return self, False
                newArray = self.array[:]
                newArray[idx + 1] = val
                return _HashCollisionNode(self.hash, self.count, newArray), False
        else:
            # nest it in a bitmap node
            return _BitmapIndexedNode(bitpos(self.hash, shift), [_absent, self]).assoc(shift, keyHash, key, val)


    def without(self, shift, keyHash, key):
        try:
            idx = 2 * self.array[::2].index(key)
        except ValueError:
            return self
        else:
            if self.count == 1:
                return _absent
            else:
                newArray = self.array[:]
                del newArray[idx:idx + 2]
                return _HashCollisionNode(self.hash, self.count - 1, newArray)



## implementation crap

def createNode(shift, oldKey, oldVal, newHash, newKey, newVal):
    oldHash = hash(oldKey)
    if oldHash == newHash:
        return _HashCollisionNode(oldHash, 2, [oldKey, oldVal, newKey, newVal])
    else:
        # something collided in a node's 5-bit window that isn't a real hash collision.
        return EMPTY_BITMAP_INDEXED_NODE.assoc(shift, oldHash, oldKey, oldVal
                                     )[0].assoc(shift, newHash, newKey, newVal)[0]


def mask(h, sh):
    return (h >> sh) & 0x1f


def bitpos(h, sh):
    return 1 << mask(h, sh)


def index(bitmap, bit):
    return bitcount(bitmap & (bit - 1))


def bitcount(i):
    count = 0
    while i:
        i &= i - 1
        count += 1
    return count
