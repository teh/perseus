#XXX redo with array-edit versions since we can rely on GIL

class frozendict(object):
    def __init__(self):
        self.root = None
        self.count = 0


    def __len__(self):
        return self.count


    def __getitem__(self, key):
        if self.root is None:
            raise KeyError(key)
        return self.root.find(0, hash(key), key)

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



_absent = object()

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
            raise KeyError(key)
        idx = index(self.bitmap, bit)
        k = self.array[2 * idx]
        v = self.array[2 * idx + 1]
        if k is _absent:
            return v.find(shift + 5, keyHash, key)
        if k == key:
            return v
        else:
            raise KeyError(key)


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
                newArray[2 * idx + 1] = createNode(shift + 5, someKey, someVal, keyHash, key, val)
                newNode = _BitmapIndexedNode(self.bitmap, newArray)
                return newNode, True
        else:
            #spot for this hash is open
            n = bitcount(self.bitmap)
            if n >= 16:
                # this node is full, convert to ArrayNode
                nodes = [_absent] * 32
                jdx = mask(keyHash, shift)
                nodes[jdx], addedLeaf = EMPTY_BITMAP_INDEXED_NODE.assoc(shift + 5, keyHash, key, val)
                j = 0
                for i in range(32):
                    if ((self.bitmap >> i) & 1) != 0:
                        if self.array[j] is _absent:
                            nodes[i] = self.array[j + 1]
                        else:
                            nodes[i], al = EMPTY_BITMAP_INDEXED_NODE.assoc(shift + 5, hash(self.array[j]), self.array[j], self.array[j + 1])
                            #al may always be false, i guess? not sure
                            addedLeaf = addedLeaf or al
                    j += 2
                return _ArrayNode(n + 1, nodes), addedLeaf
            else:
                newArray = [_absent] * (2 * (n + 1))
                newArray[:2 * idx] =  self.array[:2 * idx]
                newArray[2 * idx] = key
                newArray[2 * idx + 1] = val
                newArray[2 * (idx + 1):2 * (n + 1)] = self.array[2 * idx:2 * n]
                return _BitmapIndexedNode(self.bitmap | bit, newArray), True



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
            raise KeyError(key)
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
