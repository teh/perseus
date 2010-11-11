#include "frozendictimpl.h"

bitmap_indexed_node *bitmap_indexed_node_new(uint32_t bitmap, PyObject *array) {
  bitmap_indexed_node *n = PyObject_Malloc(sizeof(*n));
  n->kind = KIND_BITMAP_INDEXED;
  n->bitmap = bitmap;
  n->array = array;
  return n;
}


array_node *array_node_new(uint32_t hash, PyObject *array) {
  array_node *n = PyObject_Malloc(sizeof(*n));
  n->kind = KIND_ARRAY;
  n->hash = hash;
  n->array = array;
  return n;
}

hash_collision_node *hash_collision_node_new(int32_t hash, uint32_t count, PyObject *array) {
  hash_collision_node *n = PyObject_Malloc(sizeof(*n));
  n->kind = KIND_HASH_COLLISION;
  n->count = count;
  n->array = array;
  return n;
}


uint32_t mask(uint32_t h, uint32_t sh) {
  return (h >> sh) & 0x1f;
}

uint32_t bitpos(uint32_t h, uint32_t sh) {
  return 1 << mask(h, sh);
}

uint32_t bitcount(uint32_t i) {
  uint32_t count = 0;
  while (i) {
    i &= i - 1;
    count += 1;
  }
  return count;
}


uint32_t bitindex(uint32_t bitmap, uint32_t bit) {
  return bitcount(bitmap & (bit - 1));
}


static PyObject *frozendict_withUpdate(PyObject *self, PyObject *args) {
  PyObject *arg = NULL;
  if (!PyArg_UnpackTuple(args, "withUpdate", 0, 1, &arg)) {
    return NULL;
  }
  return self;
}


static PyObject *frozendict_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
  PyObject *self = type->tp_alloc(type, 0);
  PyObject *arg = NULL;
  frozendict *f;
  if (self == NULL) {
    return NULL;
  }
  f = (frozendict *)self;
  Py_INCREF(Py_None);
  f->root = Py_None;
  f->count = 0;
  f->hash = 0;
  if (!PyArg_UnpackTuple(args, "frozendict", 0, 1, &arg)) {
    return NULL;
  }
  if (arg == NULL) {
    return self;
  } else {
    return frozendict_withUpdate(self, args);
  }
}


PyDoc_STRVAR(frozendict_doc,
"frozendict() -> the empty frozendict\n"
"frozendict(mapping) -> new frozendict initialized from a mapping object's\n"
"    (key, value) pairs\n"
"dict(iterable) -> new dictionary initialized as if via:\n"
"    d = frozendict()\n"
"    for k, v in iterable:\n"
"        d = d.withPair(k, v)\n");


PyDoc_STRVAR(withUpdate__doc___,
"d.withUpdate(E) -> frozendict.  Create a new frozendict instance with the current contents as well as the contents of iterable/mapping E.\n"
"If E has a .keys() method, does:     for k in E: d = d.withPair(k, E[k])\n\
If E lacks .keys() method, does:     for (k, v) in E: d = d.withPair(k, v)");

static PyMethodDef frozendict_methods[] = {
  {"withUpdate", (PyCFunction)frozendict_withUpdate, METH_VARARGS, withUpdate__doc___},
  {NULL}
};

static PyTypeObject frozendict_type = {
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    "perseus.frozendict",
    sizeof(frozendict),
    0,
    0,                                          /* tp_dealloc */
    0,                                          /* tp_print */
    0,                                          /* tp_getattr */
    0,                                          /* tp_setattr */
    0,                                          /* tp_compare */
    0,                                          /* tp_repr */
    0,                                          /* tp_as_number */
    0,                                          /* tp_as_sequence */
    0,                                          /* tp_as_mapping */
    0,                                          /* tp_hash */
    0,                                          /* tp_call */
    0,                                          /* tp_str */
    0,                                          /* tp_getattro */
    0,                                          /* tp_setattro */
    0,                                          /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,                         /* tp_flags */
    frozendict_doc,                             /* tp_doc */
    0,                                          /* tp_traverse */
    0,                                          /* tp_clear */
    0,                                          /* tp_richcompare */
    0,                                          /* tp_weaklistoffset */
    0,                                          /* tp_iter */
    0,                                          /* tp_iternext */
    frozendict_methods,                         /* tp_methods */
    0,                                          /* tp_members */
    0,                                          /* tp_getset */
    0,                                          /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    0,                                          /* tp_init */
    0,                                          /* tp_alloc */
    frozendict_new,                             /* tp_new */
};

PyMODINIT_FUNC init_frozendict(void) {
  PyObject *m;
  if (PyType_Ready(&frozendict_type) < 0) {
    return;
  }
  Py_INCREF(&frozendict_type);
  m = Py_InitModule3("_frozendict", NULL, "");
  if (m == NULL) {
    return;
  }
  PyModule_AddObject(m, "frozendict", (PyObject *)&frozendict_type);

}
