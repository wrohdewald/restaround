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

# pylint: disable=missing-docstring, multiple-statements, invalid-name

import os
import argparse
from subprocess import call, run

try:
    import argcomplete
    # pylint: disable=unused-import
except ImportError:
    pass


class Flag:
    """
    There is a Flag class for every restic argument.
    """

    index = 0
    nargs = None
    action = None

    def __init__(self):
        self.values = None
        self.remove = False

    def __iadd__(self, other):
        """Combine other values into self."""
        assert not other.remove
        if self.values is None:
            self.values = other.values
        elif isinstance(other.values, list):
            self.values = other.values + self.values
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
            '--{}'.format(cls.restic_name()), nargs=cls.nargs, action=cls.action)

    def apply(self, profile):
        flag_name = self.restic_name()
        if self.remove and flag_name in profile.flags:
            del profile.flags[flag_name]
            return
        if flag_name in profile.flags:
            profile.flags[flag_name] += self
        else:
            profile.flags[flag_name] = self

    def __str__(self):
        return ','.join(self.args()) if self.values else '{}'.format(self.restic_name())

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

    action = 'append'


class FileFlag(ListFlag):
    """These flags always give file names."""


class PositionalFlag(ListFlag):

    index = 98
    nargs = '*'

    def args(self):
        return self.values

    @classmethod
    def add_as_argument_for(cls, command):
        """Add this flag to the command line parser."""
        command.cmd_parser.add_argument(cls.restic_name(), nargs=cls.nargs)


class ScriptFlag(Flag):

    @classmethod
    def add_as_argument_for(cls, command):
        """Not a real argument."""


class Add(Flag): pass
class Exclude_If_Present(ListFlag): pass
class Exclude(ListFlag): pass
class Files_From(ListFlag): pass
class Group_By(Flag): pass
class Host(Flag): pass
class IExclude(Flag): pass
class IInclude(Flag): pass
class Include(ListFlag): pass

class Inherit(ListFlag):

    def apply(self, profile):
        if self.remove:
            raise Exception('no_{} is not implemented'.format(self.restic_name()))
        for _ in self.values:
            profile.inherit(_)


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
class Password_Command(Flag): pass
class Path(Flag): pass
class Post(ScriptFlag): pass
class Pre(ScriptFlag): pass
class Read_Data_Subset(Flag): pass
class Remove(Flag): pass
class Remove_All(Flag): pass
class Repo(Flag): pass
class Set(Flag): pass
class Snapshot(Flag): pass
class Snapshot_Template(Flag): pass
class Stdin_Filename(Flag): pass
class Tag(ListFlag): pass
class Target(Flag): pass
class Time(Flag): pass
class Tls_Client_Cert(Flag): pass
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
class Show_Pack_Id(BinaryFlag): pass
class Stdin(BinaryFlag): pass
class Tree(BinaryFlag): pass
class Verify(BinaryFlag): pass
class With_Atime(BinaryFlag): pass
class With_Cache(BinaryFlag): pass

class Cacert(FileFlag): pass
class Cache_Dir(FileFlag): pass
class Exclude_File(FileFlag): pass
class Password_File(FileFlag): pass

class Mountpoint(PositionalFlag): pass
class FileDir(PositionalFlag): pass
class SnapshotID(PositionalFlag): pass
class Objects(PositionalFlag): pass
class Pattern(PositionalFlag): pass

class ProfileEntry:

    """Extract info from a file in the profile directory."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.command = None
        self.remove = False
        fparts = os.path.basename(filepath).split('_')
        for cmd in Main.commands.values():
            if len(fparts) > 1 and cmd.restic_name() == fparts[0] and fparts[1] in Main.flags:
                self.command = cmd.restic_name()
                fparts = fparts[1:]  # command split off
                break
        if fparts[0] == 'no':
            self.remove = True
            fparts = fparts[1:]
        self.flag_name = fparts[0]
        self.values = fparts[1:]
        if self.values:
            if os.stat(self.filepath).st_size:
                raise Exception("{}: file must be empty".format(self.filepath))
        else:
            self.values = self.__file_lines()

    def __file_lines(self):
        """Return a list of all stripped lines, empty lines exclude.
        Lines starting with # are also excluded."""
        result = [x.strip() for x in open(self.filepath, encoding='utf-8').readlines()]
        return [x for x in result if x and not x.startswith('#')]

    def flag(self):
        """Create a new flag for self.

        If the profile entry does not apply for Main.command, returns None.

        """
        if self.command is not None and self.command != Main.command:
            return None

        flag_name = self.flag_name
        result = Main.flags[flag_name].__class__()
        result.remove = self.remove
        if not result.remove:
            if isinstance(result, FileFlag):
                if result.values is None:
                    result.values = []
                result.values.insert(0, self.filepath)
            elif isinstance(result, BinaryFlag):
                result.values = self.values
            elif isinstance(result, ListFlag):
                if result.values is None:
                    result.values = []
                result.values = self.values + result.values
            else:
                if result.values or len(self.values) > 1:
                    raise Exception(
                        'must define only one value for {}: {}'.format(result, self))
                result.values = self.values
        return result

    def __str__(self):
        result = 'Entry('
        if self.command:
            result += 'command=' + self.command + ','
        result += 'path=' + str(self.filepath) + ','
        result += 'values=' + ','.join(str(x) for x in self.values) + ')'
        return result


class Profile:

    """
    This holds everything defined in a profile that may apply to command.
    """

    def __init__(self, options):
        self.options = options
        self.flags = dict()   # key: restic_name
        self.use_options()
        self.inherit(options.profile)
        self.inherit('default')

    def command_accepts(self):
        """Returns accepted flag classes."""
        return Main.commands[self.options.subparser_name].accepts_flags + Command.accepts_flags

    def use_options(self):
        """Use options to set up profile flags."""
        opt = self.options.__dict__
        for flag_class in self.command_accepts():
            flagname = flag_class.__name__.lower()
            if flagname in opt:
                if opt[flagname] is not None:
                    flag = flag_class()
                    if isinstance(opt[flagname], list):
                        flag.values = opt[flagname]
                    else:
                        flag.values = [opt[flagname]]
                    self.use_flag(flag)

    def restic_parameters(self):
        """Return all formatted flags applicable to command."""
        for flag in sorted(self.flags.values(), key=lambda x: x.index):
            assert flag.values is not None
            for _ in flag.args():
                yield _

    @classmethod
    def choices(cls):
        result = ['help', ]
        for basedir in (os.path.expanduser('~/.config'), '/etc'):
            dirname = os.path.join(basedir, 'restaround')
            if os.path.isdir(dirname):
                result.extend(os.listdir(dirname))
        return sorted(x for x in set(result) if x != 'default')

    def inherit(self, profile_name):
        """Inherit settings from other profile."""
        for basedir in ('/etc', os.path.expanduser('~/.config')):
            dirname = os.path.join(basedir, 'restaround', profile_name)
            if os.path.isdir(dirname):
                print('loading', dirname)
                for filename in os.listdir(dirname):
                    self.load_from_file(os.path.join(dirname, filename))

    def load_from_file(self, filepath):
        """Load Setting from a file."""
        flag = ProfileEntry(filepath).flag()
        if flag is not None:
            self.use_flag(flag)

    def use_flag(self, flag):
        """Integrate flag into this profile."""
        if flag.__class__ in self.command_accepts():
            flag.apply(self)


class Command:
    # Inherit must be first !
    accepts_flags = (
        Inherit, Pre, Post,
        Cacert, Cache_Dir, Cleanup_Cache,
        Json, Key_Hint, Limit_Download, Limit_Upload,
        No_Cache, No_Lock, Password_Command, Password_File,
        Quiet, Repo, Tls_Client_Cert, Verbose)

    subparsers = None

    def __init__(self):
        self.cmd_parser = None

    def add_subparser(self):
        if self.cmd_parser is None:
            self.cmd_parser = Command.subparsers.add_parser(name=self.restic_name())
        self.add_flags()

    def add_flags(self):
        to_be_added = list(Command.accepts_flags)
        for _ in self.accepts_flags:
            if _ not in to_be_added:
                to_be_added.append(_)
        for _ in to_be_added:
            Main.flags[_.restic_name()].add_as_argument_for(self)

    def run(self, profile, options):
        args = ['restic', self.restic_name()]
        args.extend(profile.restic_parameters())
        print('RUN', ' '.join(args))
        if not options.dry_run:
            call(args)

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


class CmdCache(Command):
    accepts_flags = (Cleanup, Max_Age, No_Size)


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
        Path, Keep_Tag, Tag, Host, Keep_Within,
        Keep_Last, Keep_Hourly, Keep_Daily,
        Keep_Weekly, Keep_Monthly, Keep_Yearly,
        Compact, Group_By, Dry_Run, Prune, SnapshotID)


class CmdInit(Command): pass


class CmdList(Command):
    accepts_flags = (Objects, )


class CmdLs(Command):
    accepts_flags = (Host, Long, Path, Recursive, Tag)


class CmdMount(Command):
    accepts_flags = (
        Allow_Other, Allow_Root, Host,
        No_Default_Permissions,
        Owner_Root, Path, Snapshot_Template,
        Tag, Mountpoint)

class CmdPrune(Command): pass

class CmdRebuild_Index(Command): pass


class CmdRecover(Command): pass


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


class Main:

    commands = dict()
    flags = dict()
    command = None

    def __init__(self):
        Main.commands = {x.restic_name(): x for x in self.find_classes(Command)}
        Main.flags = {x.restic_name(): x for x in self.find_classes(Flag)
                      if x.__class__ not in (ListFlag, FileFlag, BinaryFlag)}
        parser = self.build_parser()
        options = parser.parse_args()
        Main.command = options.subparser_name
        options.profile = options.profile[0]
        if options.selftest:
            self.restic_command_check()
        elif options.profile == 'help':
            if options.subparser_name is None:
                parser.print_help()
            else:
                Command.subparsers._name_parser_map[  # pylint: disable=protected-access
                    Main.commands[options.subparser_name].restic_name()].print_help()
        else:
            profile = Profile(options)
            Main.commands[Main.command].__class__().run(
                profile, options)

    @staticmethod
    def build_parser():
        parser = argparse.ArgumentParser(description="""
          Makes using restic simpler with the help of profiles. Profile 'default' is
          always used.
          """, usage='restaround [-h] [-n] profile command [restic arguments]')
        parser.add_argument(
            '-n', '--dry-run', help="""Only show the restic command to be executed""",
            action='store_true', default=False)
        parser.add_argument(
            '-s', '--selftest', help="""Do some internal tests.""",
            action='store_true', default=False)
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
                        print('cannot instantiate %s' % glob.__name__)
                        raise
                    result.append(instance)
        return result

    @staticmethod
    def restic_command_check():
        """Check if we support all restic commands."""
        will_not_implement_command = (
            'help', 'generate', 'key', 'migrate', 'self-update', 'version')
        will_not_implement_flags = {'option', 'help'}
        commands = Main.parse_general_help()
        for command in commands:
            if command in will_not_implement_command:
                continue
            if command not in Main.commands:
                print('restic {} is not supported'.format(command))
                continue
            restic_flags = set(Command.accepts_flags)
            restic_flags |= set(Main.commands[command].accepts_flags)
            restic_flags = {x.restic_name() for x in restic_flags}
            flags_in_help = Main.parse_command_help(command)
            for unimplemented in flags_in_help - restic_flags - will_not_implement_flags:
                print('WARN: restic {} --{} is not implemented'.format(command, unimplemented))
            for too_much in restic_flags - flags_in_help - {'pre', 'post', 'direct'}:
                print('WARN: {} is not supported by restic'.format(too_much))

    @staticmethod
    def parse_general_help():
        header_section = False
        flags_section = False
        commands = []
        global_flags = []
        help_stdout = run(['restic', 'help'], capture_output=True).stdout
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
        help_command = run(['restic', 'help', command], capture_output=True).stdout
        header_seen = False
        for _ in help_command.split(b'\n'):
            _ = _.decode('utf-8').strip()
            if _ == 'Flags:':
                header_seen = True
                continue
            if header_seen and ' --' in _ or _.startswith('--'):
                flag = _.split('--')[1].split(' ')[0]
                flags_in_help.add(flag)

Main()
