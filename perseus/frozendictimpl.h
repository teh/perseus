#ifndef FROZENDICT_IMPL_H
#define FROZENDICT_IMPL_H
#include "Python.h"
#include "stdint.h"


#define KIND_BITMAP_INDEXED  0
#define KIND_ARRAY 1
#define KIND_HASH_COLLISION 2


typedef struct {
  PyObject_HEAD
  char kind;
  uint32_t bitmap;
  PyObject *array;
} bitmap_indexed_node;

typedef struct {
  PyObject_HEAD
  char kind;
  int32_t hash;
  PyObject *array;
} array_node;

typedef struct {
  PyObject_HEAD
  char kind;
  int32_t hash;
  uint32_t count;
  PyObject *array;
} hash_collision_node;

typedef struct {
  PyObject_HEAD
  PyObject *root;
  uint32_t count;
  uint32_t hash;
} frozendict;

#endif
