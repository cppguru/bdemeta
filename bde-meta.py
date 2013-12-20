#!/usr/bin/env python

from __future__ import print_function
import argparse
import glob
import itertools
import os
import subprocess
import sys

def resolve_group(group):
    for root in os.getenv('ROOTS').split(':'):
        candidate = os.path.join(root, 'groups', group)
        if os.path.isdir(candidate):
            return candidate
    raise RuntimeError('"' + group + '" not found in roots. Set the ROOTS ' +
                       'environment variable to a colon-separated set of ' +
                       'paths pointing to a set of BDE-style source roots.')

def package_path(group, package):
    return os.path.join(resolve_group(group), package)

def get_items(items_filename):
    items = []
    with open(items_filename) as items_file:
        for l in items_file:
            if len(l) > 1 and l[0] != '#':
                items = items + l.split()
    return set(items)

def group_members(group):
    return get_items(os.path.join( resolve_group(group),
                                  'group',
                                   group + '.mem'))

def package_members(group, package):
    return get_items(os.path.join( resolve_group(group),
                                   package,
                                  'package',
                                   package + '.mem'))

def group_dependencies(group):
    return get_items(os.path.join( resolve_group(group),
                                  'group',
                                   group + '.dep'))

def package_dependencies(group):
    return lambda package: get_items(os.path.join( resolve_group(group),
                                                   package,
                                                  'package',
                                                   package + '.dep'))

def traverse(nodes, deps):
    return reduce(set.union, [traverse(deps(n), deps) for n in nodes], nodes)

def tsort(top_nodes, dependencies):
    tsorted = []
    nodes = traverse(top_nodes, dependencies)
    nodes = {node: {'mark': 'none', 'name': node} for node in nodes}

    def visit(node):
        if node['mark'] == 'none':
            node['mark'] = 'temporary'
            for child in dependencies(node['name']):
                visit(nodes[child])
            node['mark'] = 'permanent'
            tsorted.insert(0, node['name'])
        elif node['mark'] == 'permanent':
            return
        else:
            raise RuntimeError('cyclic graph')

    map(visit, nodes.values())
    return tsorted

def components(group):
    group_includes = []
    for g in tsort({group}, group_dependencies)[1:]:
        for p in group_members(g):
            group_includes.append(package_path(g, p))

    components = {}
    for package in group_members(group):
        package_includes = group_includes[:]
        for p in tsort({package}, package_dependencies(group)):
            package_includes.append(package_path(group, p))

        for c in package_members(group, package):
            path      = os.path.join(resolve_group(group), package)
            components[c] = {
                'includes':     package_includes,
                'cpp':          os.path.join(path, c + '.cpp'),
                'object':       os.path.join('out', 'objs', c + '.o'),
                'test_driver':  os.path.join(path, c + '.t.cpp'),
                'test':         os.path.join('out', 'tests', c + '.t'),
            }
    return components

def cflags(args):
    paths = []
    for g in tsort({args.group}, group_dependencies):
        for p in group_members(g):
            paths.append(package_path(g, p))
    print(' '.join(['-I' + path for path in paths]))

def deps(args):
    map(print, tsort(set(args.groups), group_dependencies))

def ldflags(args):
    deps = tsort(set(args.groups), group_dependencies)
    libs = ['-l' + dep for dep in deps]
    path = os.path.join('out', 'libs')

    print('-L{path} {libs}'.format(path=path, libs=' '.join(libs)))

def makefile(args):
    lib_rule = '''\
{lib}: {objects} | {libpath}
	ar -crs {lib} {objects}
'''
    tests_rule = '''\
.PHONY: tests
tests: {tests}
'''
    object_rule = '''\
{object}: {cpp} {headers} | {objpath}
	$(CXX) {cflags} -c {cpp} -o {object}
'''
    test_rule = '''\
{test}: {test_driver} {headers} | {testpath}
	$(CXX) {cflags} {test_driver} {ldflags} -o {test}
'''
    out_dir_rules = '''\
{libpath}:
	mkdir -p {libpath}

{objpath}:
	mkdir -p {objpath}

{testpath}:
	mkdir -p {testpath}
'''

    libpath  = os.path.join('out', 'libs')
    objpath  = os.path.join('out', 'objs')
    testpath = os.path.join('out', 'tests')

    lib  = os.path.join('out', 'libs', 'lib{}.a'.format(args.group))
    deps = tsort({ args.group }, group_dependencies)
    if deps:
        libs    = ['-l' + dep for dep in deps]
        ldflags = '-L{path} {libs}'.format(path = os.path.join('out', 'libs'),
                                           libs = ' '.join(libs))
    else:
        ldflags = ''
    if args.ldflags:
        ldflags = args.ldflags + ' ' + ldflags

    cs      = components(args.group)
    objects = ' '.join(c['object'] for c in cs.values())
    tests   = ' '.join(c['test']   for c in cs.values())

    print(lib_rule.format(lib = lib, libpath = libpath, objects = objects))
    print(tests_rule.format(tests = tests))
    for c in sorted(cs.keys()):
        incls   = cs[c]['includes']
        headers = ' '.join([os.path.join(path, '*') for path in incls])
        cflags  = ' '.join(['-I' + path             for path in incls])
        if args.cflags:
            cflags = args.cflags + ' ' + cflags
        print(object_rule.format(object   = cs[c]['object'],
                                 objpath  = objpath,
                                 cpp      = cs[c]['cpp'],
                                 headers  = headers,
                                 cflags   = cflags))
        print(test_rule.format(test        = cs[c]['test'],
                               test_driver = cs[c]['test_driver'],
                               headers     = headers,
                               testpath    = testpath,
                               cflags      = cflags,
                               ldflags     = ldflags))
    print(out_dir_rules.format(libpath  = libpath,
                               objpath  = objpath,
                               testpath = testpath))

def ninja(args):
    rules = '''\
rule cc-object
  deps    = gcc
  depfile = $out.d
  command = c++ $cflags -c $in -MMD -MF $out.d -o $out

rule cc-test
  deps    = gcc
  depfile = $out.d
  command = c++ $cflags $in $ldflags -MMD -MF $out.d -o $out

rule ar
  command = ar -crs $out $in
'''
    lib_template='''\
build {lib}: ar {objects}
default {lib}
'''
    tests_template='''\
build tests: phony {tests}
'''
    object_template='''\
build {object}: cc-object {cpp}
  cflags = {cflags}
'''
    test_template='''\
build {test}: cc-test {test_driver}
  cflags  = {cflags}
  ldflags = {ldflags}
'''

    lib  = os.path.join('out', 'libs', 'lib{}.a'.format(args.group))
    deps = tsort({ args.group }, group_dependencies)
    if deps:
        libs    = ['-l' + dep for dep in deps]
        ldflags = '-L{path} {libs}'.format(path = os.path.join('out', 'libs'),
                                           libs = ' '.join(libs))
    else:
        ldflags = ''
    if args.ldflags:
        ldflags = args.ldflags + ' ' + ldflags

    cs      = components(args.group)
    objects = ' '.join(c['object'] for c in cs.values())
    tests   = ' '.join(c['test']   for c in cs.values())

    print(rules)
    print(lib_template.format(lib = lib, objects = objects))
    print(tests_template.format(tests = tests))
    for c in sorted(cs.keys()):
        cflags    = ' '.join(['-I' + path for path in cs[c]['includes']])
        if args.cflags:
            cflags = args.cflags + ' ' + cflags
        print(object_template.format(object   = cs[c]['object'],
                                     cpp      = cs[c]['cpp'],
                                     cflags   = cflags))
        print(test_template.format(test        = cs[c]['test'],
                                   test_driver = cs[c]['test_driver'],
                                   cflags      = cflags,
                                   ldflags     = ldflags))

def runtest(test):
    for testcase in itertools.count():
        rc = subprocess.call([test, str(testcase)])
        if rc == 0:
            continue
        elif rc == 255:
            break
        else:
            return rc
    return 0

def runtests(args):
    tests = args.tests
    if len(tests) == 0:
        tests = glob.glob(os.path.join('out', 'tests', '*'))
    else:
        tests = [os.path.join('out', 'tests', t + '.t') for t in tests]

    for test in sorted(tests):
        if runtest(test):
            return -1

def main():
    parser    = argparse.ArgumentParser();
    subparser = parser.add_subparsers(title='subcommands')

    cflags_parser = subparser.add_parser('cflags', help='Generate a set of '
    '`-I` directives that will allow a compilation unit depending on the '
    'specified `<group>` to compile correctly.')
    cflags_parser.add_argument('group', type=str)
    cflags_parser.set_defaults(func=cflags)

    deps_parser = subparser.add_parser('deps', help='Print the list of '
    'dependencies of the specified `<group>`s in topologically sorted order.')
    deps_parser.add_argument('groups', type=str, nargs='+')
    deps_parser.set_defaults(func=deps)

    ldflags_parser = subparser.add_parser('ldflags', help='Generate a set of '
    '`-L` and `-l` directives that allow a link of objects depending on the '
    'specified `<group>`s to link correctly.')
    ldflags_parser.add_argument('groups', type=str, nargs='+')
    ldflags_parser.set_defaults(func=ldflags)

    ninja_parser = subparser.add_parser('ninja', help='Generate a ninja '
    'build file that will build a statically linked library for the specified '
    '`<group>`.')
    ninja_parser.add_argument('group', type=str)
    ninja_parser.add_argument('--cflags', type=str)
    ninja_parser.add_argument('--ldflags', type=str)
    ninja_parser.set_defaults(func=ninja)

    runtests_parser = subparser.add_parser('runtests', help='Run all of the '
    'specified BDE-style `<test>` programs to be found in `out/tests` or all '
    'of the tests in that subdirectory.')
    runtests_parser.add_argument('tests', type=str, nargs='*')
    runtests_parser.set_defaults(func=runtests)

    args = parser.parse_args()
    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())

