from perseus._hamt import (
    _absent,
    _not_found,
    EMPTY_BITMAP_INDEXED_NODE,
    )


class frozendict(object):

    def __new__(cls, input=_absent):
        f = super(frozendict, cls).__new__(cls)
        f.root = None
        f.count = 0
        f._hash = None
        if input is _absent:
            return f
        else:
            return f.withUpdate(input)


    def withUpdate(self, input):
        keys = getattr(input, 'keys', None)
        result = self
        if keys is not None:
            for k in input.keys():
                result = result.withPair(k, input[k])
        else:
            for k, v in input:
                result = result.withPair(k, v)
        return result


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
        # If you ever thought Python was good, this is where you can stop.
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
