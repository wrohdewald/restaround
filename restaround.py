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
import argparse
import logging
from subprocess import call, run, PIPE

try:
    import argcomplete
    # pylint: disable=unused-import
except ImportError:
    pass


# PATHS defines directories for looking up profile definitions.
# This is without the 'restaround' part.
# If a profile is found in more than one path, apply them in the order found.

PATHS = (PyPath('/etc'), PyPath.home() / '.config')

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

class Exclude_File(FileFlag): pass
class Password_File(FileFlag): multi = False

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

    def __init__(self, options):
        self.options = options
        self.flags = dict()   # key: restic_name
        self.inherit('default')
        self.inherit(options.profile)
        self.use_options()

    def command_accepts(self):
        """Returns accepted flag classes."""
        return Main.commands[self.options.subparser_name].accepts_flags + Command.accepts_flags

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

    def restic_parameters(self):
        """Return all formatted flags applicable to command."""
        for flag in sorted(self.flags.values(), key=lambda x: (isinstance(x, PositionalFlag), x.restic_name())):
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
            if process.returncode:
                return env, process.returncode
        return env, 0

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
            env, returncode = self.run_scripts(pre_flag.values, env)
            if returncode:
                return returncode
        returncode = self.run_command(profile)
        env['RESTIC_EXITCODE'] = str(returncode)
        for post_flag in profile.find_flags(Post):
            self.run_scripts(post_flag.values, env)
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
        return ['cp', '-al', self.repo(profile), self.copydir(profile)]

    def check_same_fs(self, profile):
        repo = self.repo(profile)
        if repo.is_mount():
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

    description = """remove the copy made with cpal. See also cpal."""

    def run_args(self, profile):
        return ['rm', '-r', self.copydir(profile)]

    def run_command(self, profile):
        copydir = self.copydir(profile)
        if not copydir.exists():
            logging.error('rmcpal: %s does not exist', copydir)
            return 2
        return Command.run_command(self, profile)


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
    accepts_flags = (Host, Long, Path, Recursive, Tag, SingleSnapshotID, Dir)


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
    run_history = []  # tuple: RUN-Command, returncode, returned variables (by Pre)

    def __init__(self, argv):
        self.init_globals()
        parser = self.build_parser()
        options = parser.parse_args(argv[1:])
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

if __name__ == '__main__':
    main_instance = Main(sys.argv)
    sys.exit(main_instance.returncode)
