#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""


# Copyright (c) 2019 Wolfgang Rohdewald <wolfgang@rohdewald.de>
# See LICENSE for details.

# PYTHON_ARGCOMPLETE_OK
# for command line argument completion, put this into your .bashrc:
# eval "$(register-python-argcomplete restaround)"
# or see https://argcomplete.readthedocs.io/en/latest/

"""

# pylint: disable=missing-docstring, multiple-statements, invalid-name, line-too-long, too-many-lines

import os
import sys
from pathlib import Path as PyPath
import shutil
import argparse
import logging
from subprocess import call, run, PIPE
import tempfile
import filecmp

try:
    import argcomplete
    # pylint: disable=unused-import
except ImportError:
    pass

VERSION = "0.1.3"


# PATHS defines directories for looking up profile definitions.
# This is without the 'restaround' part.
# If a profile is found in more than one path, apply them in the order found.

PATHS = (PyPath('/etc'), PyPath.home() / '.config')

class Test_restaround:

    profiles = []
    tmpdir = None
    test_env = None
    repo1 = None

    def setup_method(self):
        self.tmpdir = PyPath(tempfile.mkdtemp())
        global PATHS  # pylint: disable=global-statement
        Main.init_globals()
        PATHS = (self.tmpdir / 'etc', self.tmpdir / 'user')
        self.profiles = {}
        self.test_env = os.environ.copy()
        self.repo1 = self.tmpdir / 'repösitory 1 €=EUR'

    def teardown_method(self):
        shutil.rmtree(str(self.tmpdir))
        self.profiles = {}

    def define_profile(self, path_idx, name, content):
        path = PATHS[path_idx] / 'restaround' / name
        path.mkdir(parents=True)
        self.profiles[name] = path
        for key, value in content.items():
            full_path = path / key
            if value is None:
                full_path.touch()
            else:
                full_path.write_text(str(value) + '\n')
                if 'pre' in key.split('_') or 'post' in key.split('_'):
                    full_path.chmod(0o755)
        return path

    @staticmethod
    def compare_history(got_history, expect_hist):
        assert len(got_history) == len(expect_hist), 'got:%s' % got_history
        for idx, expect_entry in enumerate(expect_hist):
            got = got_history[idx]
            assert expect_entry[0] == got[0], 'RUN command differs'
            assert expect_entry[1] == got[1], 'exit code differs for {}'.format(got[0])
            for key, value in expect_entry[2].items():
                assert value == got[2][key]

    @staticmethod
    def compare_directories(a, b):
        cmp = filecmp.dircmp(str(a), str(b))
        assert not cmp.left_only
        assert not cmp.right_only
        assert not cmp.diff_files

    def run_test(self, profile, args, expect):
        Main.run_history = []
        argv = ['restaround', '--loglevel=debug', profile.name]
        argv.extend(args)
        main = Main([str(x) for x in argv])
        self.compare_history(main.run_history, expect)

    def run_init(self, profile):
        repo = ProfileEntry(profile / 'repo').flag().values[0]
        self.run_test(profile, ['init'], [(
            'RUN restic init --password-file={} --repo={}'.format(
                profile / 'password-file',
                repo,
            ), 0, {}), ])
        assert (repo / 'locks').is_dir()

    def test_init(self):
        profile = self.define_profile(1, 'profile with Umläut', {
            'repo': self.repo1,
            'password-file': 'secret password'})
        self.run_init(profile)

    def test_script_path(self):
        profile_name = 'profile with Umläut'
        profile = self.define_profile(1, profile_name, {
            'repo': self.repo1,
            'pre': '\n'.join([
                '#!/bin/bash',
                'echo "VALB=$0"'
                ]),
            'password-file': 'secret password'})
        prof = Profile()
        Main.command = 'init'  # needed for inherit()
        prof.inherit(profile_name)
        self.run_test(profile, ['init'], [
            ('RUN ' + str(profile / 'pre'), 0, {b'VALB': bytes(next(prof.pre_scripts()))}),
            ('RUN restic init --password-file={} --repo={}'.format(
                profile / 'password-file',
                self.repo1,
            ), 0, {})])

    def test_pre_fail(self):
        profile = self.define_profile(1, 'my_profile', {
            'repo': self.repo1,
            'pre': '\n'.join([
                '#!/bin/bash',
                'echo "VALA=bcde=f"',
                'exit 0']),
            'init_pre': '\n'.join([
                '#!/bin/bash',
                'echo "VALB=ccde=f"',
                'echo "RA_DR=$RESTAROUND_DRY_RUN"',
                'echo "RA_PID=$RESTAROUND_PID"',
                'echo "RA_PR=$RESTAROUND_PROFILE"',
                'echo "RA_LL=$RESTAROUND_LOGLEVEL"',
                'exit 3']),
            'password-file': 'secret password'})
        self.run_test(profile, ['init'], [
            ('RUN ' + str(profile / 'pre'), 0, {b'VALA': b'bcde=f'}),
            ('RUN ' + str(profile / 'init_pre'), 3, {
                b'VALA': b'bcde=f', b'VALB': b'ccde=f',
                b'RA_DR': b'0', b'RA_PID': str(os.getpid()).encode(),
                b'RA_PR': b'my_profile', b'RA_LL': b'debug'})])

    def test_pre_post(self):
        profile = self.define_profile(1, 'my_profile', {
            'repo': self.repo1,
            'pre': '\n'.join([
                '#!/bin/bash',
                'echo "VALA=bcde=f"',
                'exit 0']),
            'init_pre': '\n'.join([
                '#!/bin/bash',
                'echo "VALB=ccde=f"',
                'exit 0']),
            'post': '\n'.join([
                '#!/bin/bash',
                'exit 0']),
            'password-file': 'secret password'})
        self.run_test(profile, ['init'], [
            ('RUN ' + str(profile / 'pre'), 0, {b'VALA': b'bcde=f'}),
            ('RUN ' + str(profile / 'init_pre'), 0, {b'VALA': b'bcde=f', b'VALB': b'ccde=f'}),
            ('RUN restic init --password-file={} --repo={}'.format(
                profile / 'password-file',
                self.repo1,
            ), 0, {}),
            ('RUN ' + str(profile / 'post'), 0, {})])

    def test_path(self):
        profile = self.define_profile(1, 'my_profile', {
            'repo': self.repo1,
            'password-file': 'secret password',
            'path': '/path1\n/path2'})
        self.run_test(profile, ['init'], [(
            'RUN restic init --password-file={} --repo={}'.format(
                profile / 'password-file',
                self.repo1,
            ), 0, {}), ])
        self.run_test(profile, ['snapshots'], [(
            'RUN restic snapshots --password-file={} --repo={} --path=/path1 --path=/path2'.format(
                profile / 'password-file',
                self.repo1,
            ), 0, {}), ])

    def test_excludefile2(self):
        """Have 2 exclude-files"""
        default_profile = self.define_profile(0, 'default', {
            'exclude-file': 'default_filea\ndefault_dirb\ndefault_dirc\n'})
        profile = self.define_profile(1, 'my_profile', {
            'repo': self.repo1,
            'exclude-file': '_filea\n_dirb\n_dirc\n',
            'password-file': 'secret password',
            'path': '/path1\n/path2'})
        self.run_init(profile)
        self.run_test(profile, ['backup', PATHS[0]], [(
            'RUN restic backup --password-file={} --repo={} --exclude-file={} --exclude-file={} {}'.format(
                profile / 'password-file',
                self.repo1,
                default_profile / 'exclude-file',
                profile / 'exclude-file',
                PATHS[0]), 0, {}), ])

    def test_order(self):
        self.define_profile(0, 'default', {
            'verbose': '1',
            'exclude-caches': None})
        self.define_profile(1, 'profile repo', {
            'repo': self.repo1})
        profile = self.define_profile(1, 'Real profile with Umläut', {
            'verbose_4': None,
            'init_verbose_3': None,
            'inherit_profile repo': None,
            'password-file': 'secret password'})
        profile3 = self.define_profile(1, 'level3', {
            'backup_no_verbose': None,
            'inherit': 'Real profile with Umläut'})
        self.run_test(profile, ['init'], [(
            'RUN restic init --password-file={} --repo={} --verbose=3'.format(
                profile / 'password-file',
                self.repo1,
            ), 0, {}), ])
        self.run_test(profile3, ['backup', PATHS[0]], [(
            'RUN restic backup --password-file={} --repo={} --exclude-caches {}'.format(
                profile / 'password-file',
                self.repo1,
                PATHS[0]), 0, {}), ])
        self.run_test(profile, ['backup', '--verbose=9', PATHS[0]], [(
            'RUN restic backup --password-file={} --repo={} --verbose=9 --exclude-caches {}'.format(
                profile / 'password-file',
                self.repo1,
                PATHS[0]), 0, {}), ])

    def test_tag(self):
        profile = self.define_profile(1, 'pr', {
            'repo': self.repo1,
            'add_one_two_tag': None,
            'add': 'four\nfive',
            'host_mysystem_othersystem': None,
            'path': '/',
            'set': 'overwrite',
            'snapshotid': 'SNID\nID2',
            'password-file': 'secret password'})
        self.run_init(profile)
        self.run_test(profile, ['tag'], [(
            'RUN restic tag --password-file={} --repo={} --add=four --add=five --add=one --add=two --add=tag ' \
            '--host=mysystem --host=othersystem --path=/ --set=overwrite SNID ID2'.format(
                profile / 'password-file', self.repo1), 1, {})])

    def test_rescan(self):
        default_profile = self.define_profile(0, 'default', {
            'password-file': 'secret password',
            'pre': '\n'.join([
                '#!/bin/bash',
                'filename=$(dirname $0)/repo',
                'echo {} >$filename'.format(self.repo1)]),
            'exclude-caches': None})
        profile = self.define_profile(0, 'real', {
            'password-file': 'secret password'
            })
        self.run_test(profile, ['init'], [
            ('RUN ' + str(default_profile / 'pre'), 0, {}),
            ('RUN restic init --password-file={} --repo={}'.format(
                profile / 'password-file',
                self.repo1,
            ), 0, {}), ])

    def test_backup(self):
        parent_profile = self.define_profile(1, 'parent', {
            'repo': self.repo1,
            'password-file': 'secret password',
            })
        profile = self.define_profile(1, 'pr', {
            'add_one_two_tag': None,
            'inherit_parent': None,
            'add': 'four\nfive',
            'host_mysystem': None,
            'cache-dir': '/tmp',
            'limit-upload': 500,
            'limit-download': 1000,
            'path': '/',
            'filedir': PATHS[1],
            'set': 'overwrite',
            'snapshotid': 'SNID\nID2',
            })
        self.run_init(parent_profile)
        self.run_test(profile, ['backup'], [(
            'RUN restic backup ' \
            '--cache-dir=/tmp --limit-download=1000 --limit-upload=500 ' \
            '--password-file={} --repo={} --host=mysystem {}'.format(
                parent_profile / 'password-file',
                self.repo1,
                PATHS[1],
            ), 0, {})])

    def test_snapshots_forget(self):
        parent_profile = self.define_profile(1, 'parent', {
            'repo': self.repo1,
            'filedir': PATHS[1],
            'password-file': 'secret password'})
        profile = self.define_profile(1, 'pr', {
            'inherit_parent': None,
            'add_one_two_tag': None,
            'add': 'four\nfive',
            'keep-last': 5,
            'keep-hourly': 6,
            'keep-monthly': 7,
            'keep-yearly': 8,
            'keep-within': '1y5m7d2h',
            'keep-tag_a_b': None,
            'host_mysystem': None,
            'tag_a_b_c': None,
            'compact': None,
            'group-by': 'paths',
            'prune': None,
            'set': 'overwrite',
            })
        self.run_init(parent_profile)
        self.run_test(profile, ['backup'], [(
            'RUN restic backup ' \
            '--password-file={} --repo={} ' \
            '--host=mysystem --tag=a --tag=b --tag=c {}'.format(
                parent_profile / 'password-file',
                self.repo1,
                PATHS[1],
            ), 0, {})])
        self.run_test(profile, ['snapshots'], [(
            'RUN restic snapshots ' \
            '--password-file={} --repo={} --compact --group-by=paths ' \
            '--host=mysystem ' \
            '--tag=a --tag=b --tag=c'.format(
                parent_profile / 'password-file', self.repo1), 0, {})])
        self.run_test(profile, ['ls', '--recursive', 'latest', '/'], [(
            'RUN restic ls ' \
            '--password-file={} --repo={} ' \
            '--host=mysystem --recursive ' \
            '--tag=a --tag=b --tag=c latest /'.format(
                parent_profile / 'password-file', self.repo1), 0, {})])
        self.run_test(profile, ['forget', 'latest'], [(
            'RUN restic forget ' \
            '--password-file={} --repo={} ' \
            '--compact --group-by=paths ' \
            '--host=mysystem --keep-last=5 --keep-tag=a --keep-tag=b --keep-within=1y5m7d2h ' \
            '--keep-hourly=6 --keep-monthly=7 --keep-yearly=8 ' \
            '--prune --tag=a --tag=b --tag=c latest'.format(
                parent_profile / 'password-file', self.repo1), 0, {})])

    def test_restore(self):
        target_dir = self.tmpdir / 'restore_target'
        profile = self.define_profile(1, 'pr', {
            'repo': self.repo1,
            'filedir': PATHS[1],
            'exclude': 'patterna\n**.tmp\n/cache',
            'password-file': 'secret password',
            'target': target_dir,
            })
        self.run_init(profile)
        self.run_test(profile, ['backup'], [(
            'RUN restic backup ' \
            '--password-file={} --repo={} ' \
            '--exclude=patterna --exclude=**.tmp --exclude=/cache {}'.format(
                profile / 'password-file',
                self.repo1,
                PATHS[1]), 0, {}), ])
        self.run_test(profile, ['restore', 'latest'], [(
            'RUN restic restore ' \
            '--password-file={} --repo={} ' \
            '--exclude=patterna --exclude=**.tmp --exclude=/cache --target={} latest'.format(
                profile / 'password-file',
                self.repo1, target_dir,
                ), 0, {}), ])
        self.compare_directories(PATHS[1], target_dir / PyPath(str(self.tmpdir)[1:]) / 'user')

    def test_cpal(self):
        # 1. normal, mit rmcpal
        # 2. repo=sftp....
        profile = self.define_profile(1, 'pr', {
            'repo': self.repo1,
            'filedir': PATHS[1],
            'password-file': 'secret password',
            })
        self.run_init(profile)
        self.run_test(profile, ['backup'], [(
            'RUN restic backup ' \
            '--password-file={} --repo={} {}'.format(
                profile / 'password-file',
                self.repo1,
                PATHS[1]), 0, {}), ])

        cp_path = PyPath(str(self.repo1) + '.restaround_cpal')
        self.run_test(profile, ['cpal'], [(
            'RUN cp -al {} {}'.format(
                self.repo1,
                str(cp_path)), 0, {}), ])
        assert cp_path.exists()
        self.compare_directories(self.repo1, cp_path)
        self.run_test(profile, ['rmcpal'], [(
            'RUN rm -r {}'.format(str(cp_path)), 0, {}), ])
        assert not cp_path.exists()


class Flag:
    """
    There is a Flag class for every restic argument.

    Attributes:
        multi: flag can be given several times
        resolve_content:
            False: the flag name is the flag value
            True: the flag name is a file holding a list of flag values


    """

    multi = False
    resolve_content = True

    def __init__(self, entry=None):
        self.command = None  # None if the flag applies to all commands
        self.values = []
        self.remove = False
        if entry is not None:
            self.add(entry)

    def add(self, entry):
        assert isinstance(entry, ProfileEntry)
        assert entry.flag_name == self.restic_name()
        if entry.remove:
            self.remove = True
            return
        self.command = entry.command
        self.add_values(entry)

    def add_values(self, entry):
        values = entry.values
        if self.resolve_content:
            if not values:
                values = self.__file_lines(entry.path)
            if isinstance(self, BinaryFlag):
                values = [True]
        else:
            if isinstance(self, FileFlag):
                values = [entry.path]
        if self.multi:
            self.values.extend(values)
        else:
            if len(self.values) + len(values) > 1:
                logging.warning(
                    'ignoring line: must define only one value: %s + %s', self.values, values)
            else:
                self.values = values

    @staticmethod
    def __file_lines(path):
        """Return a list of all stripped lines, empty lines exclude.
        Lines starting with # are also excluded."""
        result = [x.strip() for x in open(str(path), encoding='utf-8').readlines()]
        return [x for x in result if x and not x.startswith('#')]

    def __iadd__(self, other):
        """Combine other values into self."""
        assert not other.remove
        if self.values is None:
            self.values = other.values
        elif isinstance(other.values, list):
            self.values = self.values + other.values
        else:
            self.values = other.values
        return self

    @classmethod
    def restic_name(cls):
        return cls.__name__.lower().replace('_', '-')

    def args(self):
        """Return a list of argument parts."""
        return ['--{}={}'.format(self.restic_name(), x) for x in self.values]

    @classmethod
    def add_as_argument_for(cls, command):
        """Add this flag to the command line parser."""
        command.cmd_parser.add_argument(
            '--{}'.format(cls.restic_name()))

    def apply_to(self, profile):
        flag_name = self.restic_name()
        if flag_name not in profile.flags:
            profile.flags[flag_name] = self
        elif self.multi:
            profile.flags[flag_name] += self
        else:
            profile.flags[flag_name] = self

    def remove_from(self, profile):
        flag_name = self.restic_name()
        if flag_name in profile.flags:
            del profile.flags[flag_name]

    def __str__(self):
        result = self.__class__.__name__ + '('
        if self.command:
            result += 'command=' + str(self.command)
            if self.values:
                result += ': '
        result += ','.join(str(x) for x in self.values)
        result += ')'
        return result

    def __repr__(self):
        return str(self)


class BinaryFlag(Flag):

    def args(self):
        if self.values[0]:
            return ['--' + self.restic_name()]
        return []

    @classmethod
    def add_as_argument_for(cls, command):
        """Add this flag to the command line parser."""
        command.cmd_parser.add_argument(
            '--{}'.format(cls.restic_name()), action='store_true', default=False)


class ListFlag(Flag):
    """The flag is repeated for every line in the config file."""

    multi = True

    @classmethod
    def add_as_argument_for(cls, command):
        """Add this flag to the command line parser."""
        command.cmd_parser.add_argument(
            '--{}'.format(cls.restic_name()), action='append')


class FileFlag(Flag):
    """Children get PyPath values."""
    resolve_content = False

    def add_values(self, entry):
        super().add_values(entry)
        self.values = [PyPath(x) if not isinstance(x, PyPath) else x for x in self.values]


class PositionalFlag(ListFlag):

    def args(self):
        return self.values

    @classmethod
    def add_as_argument_for(cls, command):
        """Add this flag to the command line parser."""
        command.cmd_parser.add_argument(cls.restic_name(), nargs='*')


class SinglePositionalFlag(PositionalFlag):

    multi = False

    @classmethod
    def add_as_argument_for(cls, command):
        """Add this flag to the command line parser."""
        command.cmd_parser.add_argument(cls.restic_name(), nargs='?')


class ScriptFlag(FileFlag):

    multi = True

    def args(self):
        return []


class Add(ListFlag): pass
class Exclude_If_Present(ListFlag): pass
class Exclude(ListFlag): pass
class Files_From(ListFlag): resolve_content = False
class Group_By(Flag): pass
class Host(ListFlag): pass
class IExclude(ListFlag): pass
class IInclude(ListFlag): pass
class Include(ListFlag): pass

class Inherit(ListFlag):

    def apply_to(self, profile):
        for _ in self.values:
            profile.inherit(_)

    def remove_from(self, profile):
        logging.error('no_%s is not implemented, ignoring', self.restic_name())

class Key_Hint(Flag): pass
class Keep_Daily(Flag): pass
class Keep_Hourly(Flag): pass
class Keep_Last(Flag): pass
class Keep_Monthly(Flag): pass
class Keep_Tag(ListFlag): pass
class Keep_Weekly(Flag): pass
class Keep_Within(Flag): pass
class Keep_Yearly(Flag): pass
class Limit_Download(Flag): pass
class Limit_Upload(Flag): pass
class Max_Age(Flag): pass
class Mode(Flag): pass
class Newest(Flag): pass
class Oldest(Flag): pass
class Parent(Flag): pass
class Password_Command(FileFlag): pass
class Path(Flag): multi = True
class Post(ScriptFlag): pass
class Pre(ScriptFlag): pass
class Read_Data_Subset(Flag): pass
class Remove(Flag): pass
class Repo(FileFlag): resolve_content = True

class Set(Flag): pass
class Snapshot(Flag): pass
class Snapshot_Template(Flag): pass
class Stdin_Filename(Flag): pass
class Tag(ListFlag): pass
class Target(Flag): pass
class Time(Flag): pass
class Tls_Client_Cert(FileFlag):
    multi = False

class Verbose(Flag): pass

class Allow_Other(BinaryFlag): pass
class Allow_Root(BinaryFlag): pass
class Blob(BinaryFlag): pass
class Check_Unused(BinaryFlag): pass
class Cleanup(BinaryFlag): pass
class Cleanup_Cache(BinaryFlag): pass
class Compact(BinaryFlag): pass
class Dry_Run(BinaryFlag): pass
class Exclude_Caches(BinaryFlag): pass
class Force(BinaryFlag): pass
class Ignore_Case(BinaryFlag): pass
class Ignore_Inode(BinaryFlag): pass
class Json(BinaryFlag): pass
class Last(BinaryFlag): pass
class Long(BinaryFlag): pass
class Metadata(BinaryFlag): pass
class No_Cache(BinaryFlag): pass
class No_Default_Permissions(BinaryFlag): pass
class No_Lock(BinaryFlag): pass
class No_Size(BinaryFlag): pass
class One_File_System(BinaryFlag): pass
class Owner_Root(BinaryFlag): pass
class Pack(BinaryFlag): pass
class Prune(BinaryFlag): pass
class Quiet(BinaryFlag): pass
class Recursive(BinaryFlag): pass
class Read_Data(BinaryFlag): pass
class Remove_All(BinaryFlag): pass
class Show_Pack_Id(BinaryFlag): pass
class Stdin(BinaryFlag): pass
class Tree(BinaryFlag): pass
class Verify(BinaryFlag): pass
class With_Atime(BinaryFlag): pass
class With_Cache(BinaryFlag): pass

class Cacert(FileFlag):
    multi = False
    resolve_content = True

class Cache_Dir(FileFlag):
    multi = False
    resolve_content = True

class Exclude_File(FileFlag): multi = True
class Password_File(FileFlag): pass

class Mountpoint(PositionalFlag): pass
class FileDir(PositionalFlag): pass
class Dir(PositionalFlag): pass
class SnapshotID(PositionalFlag): pass
class SingleSnapshotID(SinglePositionalFlag): pass
class Objects(PositionalFlag): pass
class Pattern(PositionalFlag): pass


class ProfileEntry:

    # pylint: disable=too-few-public-methods

    def __init__(self, path):
        self.path = path
        self.command = None
        self.remove = False
        fparts = path.parts[-1].split('_')
        for cmd in Main.commands.values():
            if (len(fparts) > 1 and cmd.restic_name() == fparts[0] and
                    ((fparts[1] in Main.flags) or (fparts[1] == 'no' and fparts[2] in Main.flags))):
                self.command = cmd.restic_name()
                fparts = fparts[1:]  # command split off
                break
        if fparts[0] == 'no':
            self.remove = True
            fparts = fparts[1:]
        self.flag_name = fparts[0]
        self.values = fparts[1:]
        if self.values and path.stat().st_size:
            logging.error("ignoring %s: must be empty", path)
            self.path = None  # marker for illegal entry

    def flag(self):
        if self.command is not None and self.command != Main.command:
            return None
        return Main.flags[self.flag_name].__class__(self)

    def __str__(self):
        result = 'Entry('
        if self.command:
            result += 'command=' + self.command + ','
        result += 'path=' + str(self.path) + ','
        result += 'values=' + ','.join(str(x) for x in self.values) + ')'
        return result


class Profile:

    """
    This holds everything defined in a profile that may apply to command.
    """

    def __init__(self, options=None):
        self.options = options
        self.flags = dict()   # key: restic_name
        self.inherit('default')
        if options is not None:
            self.inherit(options.profile)
            self.use_options()

    @staticmethod
    def command_accepts():
        """Returns accepted flag classes."""
        return Command.accepts_flags + Main.commands[Main.command].accepts_flags

    def use_options(self):
        """Use options to set up profile flags."""
        opt = self.options.__dict__
        for flag_class in self.command_accepts():
            flagname = flag_class.__name__.lower()
            if flagname in opt:
                if opt[flagname] is not None and opt[flagname] is not False:
                    flag = flag_class()
                    if isinstance(opt[flagname], list):
                        flag.values = opt[flagname]
                    else:
                        flag.values = [opt[flagname]]
                    logging.debug('option sets %s', flag.args())
                    flag.apply_to(self)

    def sorted_flags(self):
        """Sort applicable flags to the order of accepts_flags."""
        result = []
        for cls in self.command_accepts():
            result.extend(self.find_flags(cls))
        return result

    def restic_parameters(self):
        """Return all formatted flags applicable to command."""
        for flag in self.sorted_flags():
            assert flag.values is not None, 'Flag {} has values None'.format(flag)
            for _ in flag.args():
                yield _

    def find_flags(self, flag_class):
        result = []
        for flag in self.flags.values():
            if flag.__class__ is flag_class:
                result.append(flag)
        return result

    def find_flag(self, flag_class):
        flags = self.find_flags(flag_class)
        if flags:
            assert len(flags) == 1
            return flags[0]
        return None

    def pre_scripts(self):
        for pre_flag in self.find_flags(Pre):
            for _ in pre_flag.values:
                yield _

    def post_scripts(self):
        for pre_flag in self.find_flags(Post):
            for _ in pre_flag.values:
                yield _

    def scan(self, profile_name):
        """"returns an unsorted list of Flag() for all filenames applicable to Main.command"""
        result = []
        for basedir in PATHS:
            profile_dir = basedir / 'restaround' / profile_name
            if profile_dir.is_dir():
                for filename in profile_dir.iterdir():
                    flag = ProfileEntry(profile_dir / filename).flag()
                    if flag is not None:
                        if flag.__class__ in self.command_accepts():
                            result.append(flag)
        return result

    @classmethod
    def choices(cls):
        result = ['help', 'selftest']
        for basedir in PATHS:
            dirname = basedir / 'restaround'
            if dirname.is_dir():
                result.extend(x.name for x in dirname.iterdir())
        return sorted(str(x) for x in set(result) if str(x) != 'default')

    def inherit(self, profile_name):
        """Inherit settings from other profile."""
        # command specific flags first
        given = sorted(self.scan(profile_name), key=lambda x: x.command or '')
        inherit_flags = [x for x in given if x.__class__ is Inherit]
        given = [x for x in given if x.__class__ is not Inherit]
        positive = [x for x in given if not x.remove]
        negative = [x for x in given if x.remove]
        for flag in inherit_flags:
            flag.apply_to(self)
        for flag in positive:
            flag.apply_to(self)
            logging.debug('%s sets %s', profile_name, ' '.join(flag.args()) if flag.args() else flag.restic_name())
        for flag in negative:
            flag.remove_from(self)
            logging.debug('%s removes %s', profile_name, flag.restic_name())   # for command if command


class Command:
    # Inherit must be first !
    accepts_flags = (
        Cacert, Cache_Dir, Cleanup_Cache,
        Inherit, Json, Key_Hint, Limit_Download, Limit_Upload,
        No_Cache, No_Lock,
        Password_Command, Password_File,
        Pre, Post,
        Quiet, Repo, Tls_Client_Cert, Verbose)

    subparsers = None

    description = 'For a description see restic help'

    def __init__(self):
        self.cmd_parser = None

    def add_subparser(self):
        if self.cmd_parser is None:
            self.cmd_parser = Command.subparsers.add_parser(
                name=self.restic_name(), description=self.description)
        self.add_flags()

    def add_flags(self):
        to_be_added = list(Command.accepts_flags)
        for _ in self.accepts_flags:
            if _ not in to_be_added:
                to_be_added.append(_)
        for _ in to_be_added:
            Main.flags[_.restic_name()].add_as_argument_for(self)

    @staticmethod
    def run_script(script, env):
        if not script.exists():
            logging.warning('%s does not exist', script)
        cmdline = 'RUN ' + str(script)
        logging.info(cmdline)
        process = run(str(script), env=env, stdout=PIPE)
        if process.stdout:
            for line in process.stdout.split(b'\n'):
                if b'=' in line:
                    parts = line.split(b'=')
                    key = parts[0]
                    value = b'='.join(parts[1:])
                    env[key] = value
        Main.run_history.append((cmdline, process.returncode, env))
        return env, process.returncode

    def run_args(self, profile):
        args = ['restic', self.restic_name()]
        args.extend(profile.restic_parameters())
        return args

    def run(self, profile, options):
        if options.dry:
            logging.info('RUN %s', ' '.join(self.run_args(profile)))
            return 0
        env = os.environ.copy()
        for pre_script in profile.pre_scripts():
            env, returncode = self.run_script(pre_script, env)
            if returncode:
                logging.warning('Aborting because script %s returned exit code %d', pre_script, returncode)
                return returncode
            # now rescan, the script may have changed files
            profile = Profile(profile.options)
        returncode = self.run_command(profile)
        env['RESTIC_EXITCODE'] = str(returncode)
        for post_script in profile.post_scripts():
            self.run_script(post_script, env)
        return returncode

    def run_command(self, profile):
        args = self.run_args(profile)
        cmdline = 'RUN %s' % ' '.join(str(x) for x in args)
        logging.info(cmdline)
        returncode = call(args)
        Main.run_history.append((cmdline, returncode, None))
        return returncode

    @classmethod
    def restic_name(cls):
        return cls.__name__.lower().replace('_', '-')[3:]

    def __str__(self):
        return 'Command({})'.format(self.restic_name())


class CmdBackup(Command):
    accepts_flags = (
        Exclude, Exclude_File, Exclude_Caches,
        Exclude_If_Present, Files_From,
        Force, Host, IExclude, Ignore_Inode,
        One_File_System, Parent, Stdin,
        Stdin_Filename, Tag, Time, With_Atime, FileDir)


class CmdCpal(Command):

    accepts_flags = ()

    description = """Make a copy of the repository. All files will be hard linked.
    The name of the copy will be that of the repository + 'restaround_cpal'

    Works only on local or mounted file system.

    This can be useful before doing a critical operation you might want to undo.
    See also rmcpal."""

    @staticmethod
    def repo(profile):
        repo_flag = profile.find_flag(Repo)
        if repo_flag is None:
            logging.error('%s needs --repo', Main.command)
            return 2
        return repo_flag.values[0]

    def copydir(self, profile):
        repodir = self.repo(profile)
        return repodir / '..' / (str(repodir) + '.restaround_cpal')

    def run_args(self, profile):
        return ['cp', '-al', str(self.repo(profile)), str(self.copydir(profile))]

    def repo_parent(self, profile):
        return PyPath(os.path.normpath(os.path.join(str(self.repo(profile)), '..')))

    def check_same_fs(self, profile):
        repo = PyPath(str(self.repo(profile)))
        repo_parent = self.repo_parent(profile)
        repo_dev = repo.stat().st_dev
        repo_parent_dev = repo_parent.stat().st_dev
        if repo_parent_dev != repo_dev:
            logging.error(
                '%s: %s is a mount point, this is not supported',
                Main.command, repo)
            return 2
        return 0

    def run_command(self, profile):
        self.check_same_fs(profile)
        copydir = self.copydir(profile)
        if copydir.exists():
            logging.error('cpal: %s already exists', copydir)
            return 2
        return Command.run_command(self, profile)


class CmdRmcpal(CmdCpal):

    accepts_flags = ()

    description = """remove the copy made with cpal. See also cpal."""

    def run_args(self, profile):
        return ['rm', '-r', str(self.copydir(profile))]

    def run_command(self, profile):
        copydir = self.copydir(profile)
        if not copydir.exists():
            logging.error('rmcpal: %s does not exist', copydir)
            return 2
        return Command.run_command(self, profile)


class CmdCat(Command):
    accepts_flags = (Objects, )


class CmdCheck(Command):
    accepts_flags = (Check_Unused, Read_Data, Read_Data_Subset, With_Cache)


class CmdDiff(Command):
    accepts_flags = (Metadata, SnapshotID)


class CmdDump(Command):
    accepts_flags = (Host, Path, Tag)


class CmdFind(Command):
    accepts_flags = (
        Blob, Ignore_Case, Long, Newest, Oldest, Host,
        Pack, Path, Show_Pack_Id, Snapshot, Tag, Tree, Pattern)


class CmdForget(Command):
    accepts_flags = (
        Compact, Dry_Run, Group_By, Host,
        Keep_Last, Keep_Tag, Keep_Within,
        Keep_Hourly, Keep_Daily, Keep_Weekly, Keep_Monthly, Keep_Yearly,
        Path, Prune, Tag, SnapshotID)


class CmdInit(Command):
    accepts_flags = ()

class CmdList(Command):
    accepts_flags = (Objects, )


class CmdLs(Command):
    accepts_flags = (Host, Long, Path, Recursive, Tag, SingleSnapshotID, Dir)


class CmdMount(Command):
    accepts_flags = (
        Allow_Other, Allow_Root, Host,
        No_Default_Permissions,
        Owner_Root, Path, Snapshot_Template,
        Tag, Mountpoint)

class CmdPrune(Command):
    accepts_flags = ()

class CmdRebuild_Index(Command):
    accepts_flags = ()

class CmdRecover(Command):
    accepts_flags = ()


class CmdRestore(Command):
    accepts_flags = (
        Exclude, Host, IExclude, IInclude,
        Include, Path, Tag, Target, Verify, SnapshotID)


class CmdSnapshots(Command):
    accepts_flags = (Compact, Group_By, Host, Last, Path, Tag, SnapshotID)


class CmdStats(Command):
    accepts_flags = (Host, Mode, SnapshotID)


class CmdTag(Command):
    accepts_flags = (Add, Host, Path, Remove, Set, Tag, SnapshotID)


class CmdUnlock(Command):
    accepts_flags = (Remove_All, )

class CmdSelftest(Command):

    description = """
        This executes several tests. It also checks if all commands and possible arguments of the
        currently installed restic are supported."""

    def run(self, profile, options):
        """Check if we support all restic commands."""
        return self.check_restic() + self.run_pytest()

    def check_restic(self):
        returncode = 0
        will_not_implement_command = (
            'help', 'cache', 'generate', 'key', 'migrate', 'self-update', 'version')
        will_not_implement_flags = {
            'option', 'help', 'inherit', 'mountpoint', 'pattern', 'dir',
            'pre', 'post', 'direct', 'snapshotid', 'singlesnapshotid', 'filedir', 'objects'}
        commands = self.parse_general_help()
        for command in commands:
            if command in will_not_implement_command:
                continue
            if command not in Main.commands:
                logging.warning('restic %s is not supported', command)
                returncode += 1
                continue
            restic_flags = set(Command.accepts_flags)
            restic_flags |= set(Main.commands[command].accepts_flags)
            restic_flags = {x.restic_name() for x in restic_flags}
            flags_in_help = self.parse_command_help(command)
            for unimplemented in flags_in_help - restic_flags - will_not_implement_flags:
                logging.warning('restic %s --%s is not implemented', command, unimplemented)
                returncode += 1
            for too_much in restic_flags - flags_in_help - will_not_implement_flags:
                logging.warning('flag %s is not supported by restic', too_much)
                returncode += 1
        return returncode

    @staticmethod
    def run_pytest():
        try:
            import pytest
        except ImportError:
            logging.warning('please install pytest: "pip install -U pytest"')
            return 1
        with tempfile.TemporaryDirectory() as tmpdir:
            path = shutil.which('restaround')
            tmpfile = shutil.copyfile(path, os.path.join(tmpdir, 'restaround_test.py'))
            # parallel execution: install pytest-xdist return pytest.main(['-n', '6', '-vv', tmpfile])
            return pytest.main(['-vv', tmpfile])

    @staticmethod
    def parse_general_help():
        header_section = False
        flags_section = False
        commands = []
        global_flags = []
        help_stdout = run(['restic', 'help'], stdout=PIPE).stdout
        for _ in help_stdout.split(b'\n'):
            _ = _.decode('utf-8').strip()
            if not _:
                header_section = False
                flags_section = False
            if _.endswith('Commands:'):
                header_section = True
                continue
            if _.endswith('Flags:'):
                flags_section = True
                continue
            if header_section:
                commands.append(_.split(' ')[0])
            elif flags_section:
                global_flags.append(_.split('--')[1].split(' ')[0])
        return commands

    @staticmethod
    def parse_command_help(command):
        flags_in_help = set()
        help_command = run(['restic', 'help', command], stdout=PIPE).stdout
        header_seen = False
        for _ in help_command.split(b'\n'):
            _ = _.decode('utf-8').strip()
            if _ == 'Flags:':
                header_seen = True
                continue
            if header_seen and ' --' in _ or _.startswith('--'):
                flag = _.split('--')[1].split(' ')[0]
                flags_in_help.add(flag)
        return flags_in_help

class Main:

    commands = dict()
    flags = dict()
    command = None
    run_history = []  # tuple: RUN-Command, returncode, returned variables (by Pre)

    def __init__(self, argv):
        if argv[1] == '--version':
            print('restaround version', VERSION)
            sys.exit(0)
        self.init_globals()
        parser = self.build_parser()
        options = parser.parse_args(argv[1:])
        if options.dry:
            if options.loglevel != 'debug':
                options.loglevel = 'info'
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
        logging.getLogger().setLevel(options.loglevel.upper())
        Main.command = options.subparser_name
        options.profile = options.profile[0]
        os.environ['RESTAROUND_PID'] = str(os.getpid())
        os.environ['RESTAROUND_PROFILE'] = options.profile
        os.environ['RESTAROUND_DRY_RUN'] = '1' if options.dry else '0'
        os.environ['RESTAROUND_LOGLEVEL'] = options.loglevel
        if options.profile == 'help':
            if options.subparser_name is None:
                parser.print_help()
            else:
                Command.subparsers._name_parser_map[  # pylint: disable=protected-access
                    Main.commands[Main.command].restic_name()].print_help()
            self.returncode = 0
        elif options.profile == 'selftest':
            self.returncode = Main.commands['selftest'].__class__().run(None, options)
        else:
            profile = Profile(options)
            self.returncode = Main.commands[Main.command].__class__().run(profile, options)
        if self.returncode and self.returncode % 256 == 0:
            self.returncode -= 1

    @staticmethod
    def init_globals():
        Main.run_history = []
        Main.commands = {x.restic_name(): x for x in Main.find_classes(Command)}
        Main.flags = {x.restic_name(): x for x in Main.find_classes(Flag)
                      if not x.__class__.__name__.endswith('Flag')}
    @staticmethod
    def build_parser():
        parser = argparse.ArgumentParser(description="""
          Makes using restic simpler with the help of profiles. Profile 'default' is
          always used.
          """, usage='restaround [-h] [-n] profile command [restic arguments]')
        parser.add_argument(
            '-n', '--dry', help="""Only show the restic command to be executed""",
            action='store_true', default=False)
        parser.add_argument(
            '-l', '--loglevel', help='set the loglevel only for restaround, not for restic',
            choices=('error', 'warning', 'info', 'debug'), default='info')
        parser.add_argument(
            'profile', nargs=1, choices=Profile.choices(), help="""
            Use PROFILE. A relative name is first looked for
            in ~/.config/restaround/, then in /etc/restaround/""")
        Command.subparsers = parser.add_subparsers(dest='subparser_name')
        for _ in Main.commands.values():
            _.add_subparser()

        try:
            argcomplete.autocomplete(parser)
        except NameError:
            pass
        return parser

    @staticmethod
    def find_classes(baseclass):
        result = list()
        for glob in globals().values():
            if hasattr(glob, "__mro__"):
                if glob.__mro__[-2] == baseclass and len(glob.__mro__) > 2:
                    try:
                        instance = glob()
                    except Exception:
                        logging.error('cannot instantiate %s', glob.__name__)
                        raise
                    result.append(instance)
        return result


def exec_main():
    main_instance = Main(sys.argv)
    sys.exit(main_instance.returncode)


if __name__ == '__main__':
    exec_main()
