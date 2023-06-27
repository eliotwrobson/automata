import Cython.Compiler.Options
from Cython.Build import cythonize
from setuptools import setup

Cython.Compiler.Options.annotate = True

setup(ext_modules = cythonize('automata/base/dfa_worker.pyx', annotate=True))
