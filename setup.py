from distutils.core import setup, Extension

setup(
    name="perseus",
    description="A copy on write dictionary implementing efficient immutable" +
        "dictionaries through node sharing.",
    url='https://github.com/jml/perseus/',
    packages=['perseus'],
)
