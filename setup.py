import Cython.Compiler.Options
from Cython.Build import cythonize
from setuptools import setup

Cython.Compiler.Options.annotate = True

# Add "annotate=True" to cythonize to get HTML with useful compilation info.
setup(ext_modules = cythonize('automata/base/dfa_worker.pyx'))
