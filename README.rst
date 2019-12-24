What is restaround?
===================

restaround is a wrapper around the backup utility restic_ simplifying its use.

This is done by defining profiles. A profile defines the arguments to be used for restic_.
Profiles can inherit from others.

Quick start
===========

Backing up ``/home`` into ``/backup/restic``:

- create directory ``~/.config/restaround/home`` or ``/etc/restaround/home``
- go into that directory
- edit new file ``repo``. Content is ``backup/restic``
- edit new file ``password-file``, put the password into it
- edit new file ``filedir``. Content is ``/home``
- ``restaround home init`` will initialize the repository
- ``restaround home backup`` will backup
- ``restaround home mount /mnt`` will mount all backups in /mnt


Synopsis
========

Usage: restaround [-h] [-n] [-s] profile command [restic arguments]

  -h, --help      show this help message and exit

  -n, --dry-run   Only show the restic command to be executed


========================== ==============================================================================================
profile                    Use profile. It is first looked for in ``~/.config/restaround/``, then in ``/etc/restaround/``
-------------------------- ----------------------------------------------------------------------------------------------
command                    the restic command to be executed
-------------------------- ----------------------------------------------------------------------------------------------
restic arguments           any additional arguments for restic_
========================== ==============================================================================================



Examples where `main` is the name of a profile:

::

  restaround main backup --with-atime
  restaround --dry-run main snapshots
  restaround main diff --metadata 3a5f latest
  restaround main mount


Profiles
========

Location
--------

Every profile is defined within its own directory. They are searched first
in `~/.config/restaround` and then in `/etc/restaround`. If the same profile
is defined in both places: See Inheriting_.

Arguments passed on the command line build another profile to be applied last.

restic_ can get many arguments in environment variables like ``$RESTIC_PASSWORD_FILE``.
restaround just passes them on.


Definition
----------
A profile is implemented as a directory with files for flags. Those can be
symbolic links, getting flag values from other profiles.

Most files in that directory have the same spelling as the restic_ flag.
In restic_, however the positional flags sometimes have names which do not allow
this like restic backup: ``FILE/DIR [FILE/DIR] ...``.
In that case, say ``restaround help backup`` to see the name restaround wants, in this case ``filedir``.

The full name can be built as follows:

  `[command] [no] [flag] [value] [value] ...`

where the separate parts are joined by underlines. This character is not part
of any restic_ command or argument. If you need _ in a value, do not use
the [value] part. There is an alternative.

- ``command`` is a restic command. The file only applies to that command. If not given, it applies to all commands
- ``no`` will disable something defined in the inherited profiles
- ``flag`` is a restic flag like ``with-atime``. Special flags are ``inherit``, ``pre`` and ``post``
- ``value`` is the value for a flag like in ``repo=value``
- ``more values`` the flag will be repeated for all values

restaround knows which restic commands know which flags, it will only
apply the allowed ones to a specific command.

A profile directory might contain files like

::

  backup_pre
  backup_filedir
  exclude-file
  password-file
  repo
  no_with-atime
  inherit_xxx

Some restic_ flags can be repeated like --tag:
tag can be a file with one or several lines. Each line is extended into --tag linecontent.

The restic_ flags ``cacert``, ``cachedir``, ``exclude-file``, ``include-file``, ``password-file`` are special:
The corresponding file holds the content, so ``exclude-file`` extends to ``--exclude-file=profile/exclude-file``.
As you already know, symbolic links are allowed. So ``cacert`` may be a symbolic link to the certification file.

For flags with just one argument like --repo create profile/repo with one line.

The alternative form ``flag_value1_value2_value3`` is treated like a file with 3 lines.
So ``exclude_a_b_dirc`` would extend into ``--exclude a --exclude b --exclude dirc``
Such a file must be empty. Of course this form can only be used if the resulting file name
is legal for the file system and if no part contains an underline.

``tag`` in restic_ is used as both a command and as an argument, but this should pose no problem.

``tag_tag`` is the "tag" flag applied only to command "tag"
``tag_taga``  is the "tag" flag applied to all commands as ``--tag taga``

If you really want to do ``--tag=tag``, you can define a file named ``tag`` (or ``tag_tag``) with
one line "tag".



Special commands
----------------

Those commands are executed by restaround. Otherwise their usage is the same
regarding inheritance and execution of pre/post scripts.

``cpal`` makes a copy of the repository. All files will be hard linked.
The name of the copy will be that of the repository + 'restaround_cpal'
This can be useful before doing a critical operation you might want to undo.

``rmcpal`` removes such a copy.

Of course you could simply call ``cp -al`` directly. But using restaround has the
advantage that it will execute the pre- and postscripts. If the repository must
first be mounted and the be unmounted, the pre- and postscripts will do that.
Example: `Automatically mounting and unmounting a USB drive`_


Inheriting
----------

The special flag ``inherit`` can be defined just like a normal flag but
it will be executed by restaround instead of passing it to restic. So you can use

- ``--inherit=remote``
- empty file ``backup_inherit_remote``
- file with content ``inherit``

You can inherit from any number of other profiles.
If there is a profile named ``default``, it is always inherited from.

Most flags can be passed multiple times to restic. For those, restaround will follow
the inheritance tree from the top (the ``default`` profile) to the bottom (the profile
passed to restaround on the command line). Lastly, the arguments passed directly as
command line arguments are appended.

the most general first (from the default profile), followed by descend



Order of execution
------------------

Profiles are used top-down where top is the ``default`` profile and down is
the profile passed on the command line. Command line arguments are applied last.

Multiple ``inherit`` command files in a profile are executed in alphabetical order.

When loading a profile, the ``no_`` files are executed last. As as example, you can
define ``pre`` and ``no_pre_cache`` where pre mounts an external USB drive. So for
the ``cache`` command, the USB drive will not be mounted.

If both a general and a command specific flag are defined within a profile, the
general flag is applied first.


Pre- and Postscripts
--------------------

The special flag ``pre`` defines a script to be executed before the restic_ command.

The special flag ``post`` defines a script to be executed after the restic_ command. It
gets the exit code of the restic_ command in the shell variable ``RESTIC_RESULT``.

Those flags can be defined analog to ``cacert``, see above.

Just like with any flag, inheritance means that several ``pre`` or ``post`` scripts might be
defined. They are executed in the order as defined for normal flags: ``default``
profile first, command line arguments last. As soon as an exit code from a ``pre`` script
is not 0, restaround aborts with that exit code. This is not true for ``post`` scripts:
after the main restic command finishes, all post scripts are always executed.

The scripts will get some environment variables:

=========================  ==============================================================
Environment variable       meaning
=========================  ==============================================================
RESTAROUND_PID             the process id of the calling restaround
RESTAROUND_PROFILE         the name of the profile restaround was called with
RESTAROUND_DRY_RUN         1 if --dry-run was given, 0 else
RESTAROUND_LOGLEVEL        the given --loglevel: error, warning, info, debug
=========================  ==============================================================

Scripts can pass environment variables to the next script. Because there is no
way known to me how to do that on a non linux system, they do that like this:

``echo "VARNAME=VALUE"``

Everything a script writes to stdout must look like that. You must suppress other
output to stdout.

Pre scripts are executed before the main restic command. They are allowed to
modify  the flags in the profile directory, the profile is rescanned after
every pre script.

Those scripts also allows setting up chains like backup, check, forget, prune.
Just be careful not to go into endless loops.



Examples
========

Directory structure
-------------------

=========================  ==============================================================
file name                  meaning
=========================  ==============================================================
backup_tag_taga_tagb       backup --tag taga --tag tagb
repo                       --repo REPONAME where REPONAME stands on the first line of ``repo``
restore_no_tag             for restore only, removes --tag if it was defined in an inherited profile
=========================  ==============================================================


Define separate profiles for the source and the repository and then combine them:

=============================== =========================================================
Directory                       Files
=============================== =========================================================
/etc/restaround/default         exclude-caches mountpoint
/etc/restaround/local           password-file repo
/etc/restaround/remote          password-file repo
/etc/restaround/mydata          exclude-file filedir
/etc/restaround/mydata_local    inherit_local inherit_mydata
/etc/restaround/mydata_remote   inherit_remote inherit_mydata
=============================== =========================================================


Backup mydata on a remote repository and list all snapshots on that repository:

::

  restaround mydata_remote backup
  restaround remote snapshots


Automatically mounting and unmounting a USB drive
-------------------------------------------------
pre:

::

  #!/bin/bash

  # This is reentrant. A pre or post script might call restaround

  mount | fgrep 'on /backdisk3 ' >/dev/null
  if test $? -eq 0
  then
        echo DISK3_WAS_MOUNTED_BY=0
  else
        mount /backdisk3 >/dev/null
        if test x${DISK3_WAS_MOUNTED_BY} == x
        then
                echo DISK3_WAS_MOUNTED_BY=$RESTAROUND_PID
                # else somebody else may have unmounted
        fi
  fi


post:

::

  #!/bin/bash

  # only umount if we are called by the restaround instance which mounted

  test $DISK3_WAS_MOUNTED_BY -eq $RESTAROUND_PID && umount /backdisk3


Show diff after backup
----------------------
This expects at least two snaphots in the repository. Better would be to
check whether $snap2 really holds exactly 2 values.

backup_post:

::

  #!/bin/bash

  snap2=$(restaround --loglevel error "$RESTAROUND_PROFILE" snapshots --json | jq -r '.[-2:][].id')

  restaround "$RESTAROUND_PROFILE" diff $snap2 >&2


Installation
============

Get it from https://pypi.org/project/restaround/

You can do

pip3 install restaround

If you want bash command line argument completion, put this into your .bashrc:
  ``eval "$(register-python-argcomplete restaround)"``

or see https://argcomplete.readthedocs.io/en/latest/
You may have to install a python package. On Debian, it would be ``python3-argcomplete``.

If you want to use ``restaround selftest``, please install pytest, see https://docs.pytest.org:
  ``pip install -U pytest``

For parallel test execution see the comment in the source: search for run_pytest.


TODO
====
- maybe lockrepo and unlockrepo: https://forum.restic.net/t/is-it-possible-to-decrypt-restic-files-from-the-command-line/2363/7
- maybe restaround --ionice, also as profile/ionice_c3

.. _restic: https://restic.net

