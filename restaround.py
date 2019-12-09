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
import sys
import argparse
import logging
from subprocess import call, run, PIPE

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
    multi = False

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

    def apply_to(self, profile):
        flag_name = self.restic_name()
        if flag_name not in profile.flags:
            profile.flags[flag_name] = self
        elif self.multi:
            profile.flags[flag_name] += self

    def remove_from(self, profile):
        flag_name = self.restic_name()
        if flag_name in profile.flags:
            del profile.flags[flag_name]

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
    multi = True


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


class ScriptFlag(FileFlag):

    def args(self):
        return []


class Add(Flag):
    multi = True

class Exclude_If_Present(ListFlag): pass
class Exclude(ListFlag): pass
class Files_From(ListFlag): pass
class Group_By(Flag): pass
class Host(Flag): pass
class IExclude(ListFlag): pass
class IInclude(ListFlag): pass
class Include(ListFlag): pass

class Inherit(ListFlag):

    def apply_to(self, profile):
        for _ in self.values:
            profile.inherit(_)

    def remove_from(self, profile):
        logging.error('no_%s is not implemented', self.restic_name())
        sys.exit(2)

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
class Show_Pack_Id(BinaryFlag): pass
class Stdin(BinaryFlag): pass
class Tree(BinaryFlag): pass
class Verify(BinaryFlag): pass
class With_Atime(BinaryFlag): pass
class With_Cache(BinaryFlag): pass

class Cacert(FileFlag):
    multi = False

class Cache_Dir(FileFlag):
    multi = False

class Exclude_File(FileFlag): pass
class Password_File(FileFlag):
    multi = False

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
                logging.error("%s: file must be empty", self.filepath)
                sys.exit(1)
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
                    logging.warning(
                        'ignoring line: must define only one value for %s: %s', result, self)
                else:
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
                    flag.apply_to(self)

    def restic_parameters(self):
        """Return all formatted flags applicable to command."""
        for flag in sorted(self.flags.values(), key=lambda x: x.index):
            assert flag.values is not None
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

    @classmethod
    def choices(cls):
        result = ['help', 'selftest']
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
                for filename in os.listdir(dirname):
                    self.load_from_file(os.path.join(dirname, filename))

    def load_from_file(self, filepath):
        """Load Setting from a file."""
        flag = ProfileEntry(filepath).flag()
        if flag is not None:
            if flag.__class__ in self.command_accepts():
                if flag.remove:
                    flag.remove_from(self)
                else:
                    flag.apply_to(self)


class Command:
    # Inherit must be first !
    accepts_flags = (
        Inherit, Pre, Post,
        Cacert, Cache_Dir, Cleanup_Cache,
        Json, Key_Hint, Limit_Download, Limit_Upload,
        No_Cache, No_Lock, Password_Command, Password_File,
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
    def run_scripts(scripts, env):
        for script in scripts:
            if not os.path.exists(script):
                logging.warning('%s does not exist', script)
            logging.info('RUN %s', script)
            process = run(script, env=env, stdout=PIPE)
            if exit_on_error and process.returncode:
                sys.exit(process.returncode)
            if process.stdout:
                for line in process.stdout.split(b'\n'):
                    if b'=' in line:
                        parts = line.split(b'=')
                        env[parts[0]] = parts[1]
            if process.returncode:
                sys.exit(process.returncode)
        return env

    def run_args(self, profile):
        args = ['restic', self.restic_name()]
        args.extend(profile.restic_parameters())
        return args

    def run(self, profile, options):
        if options.dry_run:
            logging.info('RUN %s', ' '.join(self.run_args(profile)))
            return 0
        env = os.environ.copy()
        for pre_flag in profile.find_flags(Pre):
            env = self.run_scripts(pre_flag.values, env)
        returncode = self.run_command(profile)
        env['RESTIC_EXITCODE'] = str(returncode)
        for post_flag in profile.find_flags(Post):
            self.run_scripts(post_flag.values, env)
        return returncode

    def run_command(self, profile):
        args = self.run_args(profile)
        logging.info('RUN %s', ' '.join(args))
        return call(args)

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
            sys.exit(2)
        return repo_flag.values[0]

    def repo_parent(self, profile):
        return os.path.normpath(os.path.join(self.repo(profile), '..'))

    def copydir(self, profile):
        self.check_same_fs(profile)
        return os.path.join(self.repo_parent(profile), self.repo(profile) + '.restaround_cpal')

    def run_args(self, profile):
        return ['cp', '-al', self.repo(profile), self.copydir(profile)]

    def check_same_fs(self, profile):
        repo = self.repo(profile)
        repo_parent = self.repo_parent(profile)
        repo_dev = os.stat(repo).st_dev
        repo_parent_dev = os.stat(repo_parent).st_dev
        if repo_parent_dev != repo_dev:
            logging.error(
                '%s: %s and %s must be in the same file system',
                Main.command, repo, repo_parent)
            sys.exit(1)

    def run_command(self, profile):
        copydir = self.copydir(profile)
        if os.path.exists(copydir):
            logging.error('cpal: %s already exists', copydir)
            sys.exit(1)
        args = self.run_args(profile)
        logging.info('RUN %s', ' '.join(args))
        return call(args)


class CmdRmcpal(CmdCpal):

    description = """remove the copy made with cpal. See also cpal."""

    def run_args(self, profile):
        return ['rm', '-r', self.copydir(profile)]

    def run_command(self, profile):
        copydir = self.copydir(profile)
        if not os.path.exists(copydir):
            logging.error('rmcpal: %s does not exist', copydir)
            sys.exit(1)
        args = self.run_args(profile)
        logging.info('RUN %s', ' '.join(args))
        return call(args)


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

class CmdSelftest(Command):

    def run(self, profile, options):
        """Check if we support all restic commands."""
        returncode = 0
        will_not_implement_command = (
            'help', 'generate', 'key', 'migrate', 'self-update', 'version')
        will_not_implement_flags = {
            'option', 'help', 'inherit', 'mountpoint', 'pattern',
            'pre', 'post', 'direct', 'snapshotid', 'filedir', 'objects'}
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
        return flags_in_help

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
        if options.dry_run:
            if options.loglevel != 'debug':
                options.loglevel = 'info'
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
        logging.getLogger().setLevel(options.loglevel.upper())
        Main.command = options.subparser_name
        options.profile = options.profile[0]
        if options.profile == 'help':
            if options.subparser_name is None:
                parser.print_help()
            else:
                Command.subparsers._name_parser_map[  # pylint: disable=protected-access
                    Main.commands[options.subparser_name].restic_name()].print_help()
            returncode = 0
        elif options.profile == 'selftest':
            returncode = Main.commands['selftest'].__class__().run(None, options)
        else:
            profile = Profile(options)
            returncode = Main.commands[Main.command].__class__().run(profile, options)
        if returncode and returncode % 256 == 0:
            returncode -= 1
        sys.exit(returncode % 256)

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

Main()
