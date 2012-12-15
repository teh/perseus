_absent = object()
_not_found = object()


class _TrieNode(object):

    kind = None

    def iteritems(self):
        raise NotImplementedError(self.iteritems)

    def find(self, shift, keyHash, key):
        raise NotImplementedError(self.find)

    def assoc(self, shift, keyHash, key, val):
        raise NotImplementedError(self.assoc)

    def without(self, shift, keyHash, key):
        raise NotImplementedError(self.without)


class _BitmapIndexedNode(_TrieNode):

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
            if len(self.array) == 2:
                #last pair in this node
                return _absent
            newArray = self.array[:]
            del newArray[2 * idx:2 * idx + 2]
            return _BitmapIndexedNode(self.bitmap ^ bit, newArray)
        else:
            return self



EMPTY_BITMAP_INDEXED_NODE = _BitmapIndexedNode(0, [])


class _ArrayNode(_TrieNode):

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
                return self.pack(idx)
            return _ArrayNode(self.count - 1, newArray)
        else:
            return _ArrayNode(self.count, newArray)


    def pack(self, idx):
        newArray = [_absent] * (2 * (self.count - 1))
        j = 1
        bitmap = 0
        for i in range(len(self.array)):
            if i != idx and self.array[i] is not _absent:
                newArray[j] = self.array[i]
                bitmap |= 1 << i
                j += 2
        return _BitmapIndexedNode(bitmap, newArray)



class _HashCollisionNode(_TrieNode):

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
    """
    How many bits are in a binary representation of 'i'?
    """
    count = 0
    while i:
        i &= i - 1
        count += 1
    return count
