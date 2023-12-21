About `Myrrh`
=============

`Myrrh` is an open-source version and complete refactoring of a project originally designed for testing purposes. Using `Myrrh` does not necessarily require you to install Python on remote systems, or even an agent.

`Myrrh` uses standard network protocols through its "provider" to realize operations on distant systems and is designed to be expandable.

The `Myrrh` "0.*.*" versions are prototypes intended for project fine-tuning and provider developments.

Requirements
============

* Python: 3.11
* OS: Nt or POSIX

Installation
============

To install `Myrrh` simply run:

```shell
$ pip install myrrh
```

Getting Started
===============

Python scripting
----------------

`Myrrh` framework contains two main libraries `bmy` and `mlib`

`bmy` is a library containing basic functions for interacting and manipulating entities.

```python
import bmy

bmy.new(path='**/local')
bmy.build()
bmy.lsdir()
```

`mlib` is a wrapper for performing Python module operations on remote machines

```python
import bmy

bmy.new(path='**/local')
bmy.build()

with bmy.select() :
    from mlib.py import os

os.getcwd()
```

using the Command Line Interface
--------------------------------

```shell
$ myrrhc
 Welcome to Myrrhc Console (for test purpose only)
  - Use it with fairplay -
Type help, copyright, credits, license for more information

ctrl-D to exit console


(myrrhc)
```
