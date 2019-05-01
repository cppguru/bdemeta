[![Build Status](https://img.shields.io/travis/frutiger/bdemeta/master.svg?style=flat-square&logo=linux&logoColor=white)](https://travis-ci.org/frutiger/bdemeta)
[![Build Status](https://img.shields.io/appveyor/ci/frutiger/bdemeta/master.svg?style=flat-square&logo=windows)](https://ci.appveyor.com/project/frutiger/bdemeta)
[![Coverage Status](https://img.shields.io/coveralls/github/frutiger/bdemeta/master.svg?style=flat-square)](https://coveralls.io/github/frutiger/bdemeta?branch=master)

# bdemeta

Build and test BDE-style code.

## Synopsis

`bdemeta walk TARGET [TARGET ...]`<br/>
`bdemeta dot TARGET [TARGET ...]`<br/>
`bdemeta cmake TARGET [TARGET ...]`<br/>
`bdemeta runtests [TEST ...]`

## Description

`bdemeta` is a set of basic tools to assist building and testing [BDE-style
source trees](https://github.com/bloomberg/bde).  It can generate
[`CMake`](https://cmake.org) files for package groups and test drivers within
them.  It can also invoke BDE-style test drivers.

`bdemeta` supports finding targets across [disconnected directory
structures](#roots).

## Installation

Platforms running Python 3.6 or newer are supported.  Install using `pip`:

    $ pip install git+https://github.com/frutiger/bdemeta

## Modes

`bdemeta` runs in one of four modes as given by the first positional argument:

  * `walk TARGET [TARGET ...]`:<br/>
    Walk and topologically sort dependencies

  * `dot TARGET [TARGET ...]`:<br/>
    Generate a directed graph in the DOT language

  * `cmake TARGET [TARGET ...]`:<br/>
    Generate CMake files in the current directory

  * `runtests [TEST ...]`:<br/>
    Run specified or discovered unit tests

## Configuration

`bdemeta` is configured by a JSON configuration file in the current directory
called `.bdemeta.conf`.  The configuration is as follows:

    {
        "roots": [
            "<root>",
            ...
        ],
        "providers": {
            "<target1>: ["<target2>", "<target3>", ...],
            ...
        },
        "runtime_libraries": ["<target4>", "<target5">, ...],
        "pkg_configs": {
            "<target6>": "<pkg1>",
            ...
        }
    }

The meaning of each block is explained below.

### Roots

`bdemeta` will look for targets in directories specified by (possibly multiple)
`<root>`s in the configuration.  This makes it easy to build code across
multiple BDE-style repositories, including your own.

In particular, `bdemeta` will search for targets by name within each `<root>`
directory:

  * package groups in `<root>/groups/<name>`
  * standalone pacakges in `<root>/[adapters|nodeaddons|stanadlone]/<name>`
  * third party CMake packages in:
      * `<root>/thirdparty/CMakeLists.txt`
      * `<root>/CMakeLists.txt`

### Target providers

A number of third party targets may be specified by a single `CMakeLists.txt`.
However, the dependency from a target is on another target (i.e. library), not
on a directory.  A "target provider" may be used to specify that a directory
containing a `CMakeLists.txt` will actually provide other targets.

The sample configuration above indicates that the `CMakeLists.txt` in
`<target1>` will actually provide `<target2>` and `<target3>`.  This allows
`bdemeta` to consider the targets `<target2>` and `<target3>` found once it
finds `<target1>`.

Note that the `providers` block is optional.

### Runtime libraries

Some platforms require undefined symbols to be provided at link time.  However,
when building plug-in libraries, some symbols are expected to be supplied by
the hosting executable at runtime.  Enumerating the libraries that contain
symbols that will be supplied at runtime allows `bdemeta` to ensure that any
targets that depend those libraries are linked allowing undefined symbols.

The sample configuration indicates that any target depending (transitively or
not) on `<target4>` or `<target5>` should be linked allowing undefined symbols.

Note that the `runtime_libraries` block is optional.

### Package Config

A target may have its dependencies defined by the `pkg-config`, already
available on the system.  The `pkg_configs` block is consulted to map a target
name `<target6>` to a `pkg-config` package named `<pkg1>`.  This block
is only consulted if the search through every root as described above has been
exhausted.

Note that the `pkg_configs` block is optional.

## CMake

For every target specified to the `cmake` subcommand, `bdemeta` walks all
transitive dependencies based on the configuration described above.

For each BDE-type dependency, `bdemeta` generates:

  * a CMake library target
  * a CMake executable target for each test driver
  * a CMake custom target comprising all the test drivers, named `<name>.t`
  * a 'development' install target for the library & headers
  * a 'runtime' install target for the library

For each `PkgConfig`-type dependency, `bdemeta` generates a CMake interface
target consisting of the discovered include directories, compile options and
link libraries.

## License

Copyright (C) 2013 Masud Rahman

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

