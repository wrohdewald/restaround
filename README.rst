What is restaround?
===================

restaround is a wrapper around the backup utility restic_ simplifying its use.

This is done by defining profiles. A profile defines the arguments to be used for restic_.
Profiles can inherit from others.


Synopsis
========

Usage: restaround [-h] [-n] [-s] profile command [restic arguments]

  -h, --help      show this help message and exit

  -n, --dry-run   Only show the restic command to be executed

  -s, --selftest  Check if restaround and restic are compatible


========================== =====================================================================================================
profile                    Use PROFILE. A relative name is first looked for in ~/.config/restaround/, then in /etc/restaround/
-------------------------- -----------------------------------------------------------------------------------------------------
command                    the restic command to be executed
-------------------------- -----------------------------------------------------------------------------------------------------
restic arguments           any additional arguments for restic_
========================== =====================================================================================================



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

TODO:

When loading a profile, the ``no_`` files are executed last. As as example, you can
define ``pre`` and ``no_pre_cache`` where pre mounts an external USB drive. So for
the ``cache`` command, the USB drive will not be mounted.

Until this is implemented, you can do that with inheritance.



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
they are all executed.

Scripts can pass environment variables to the next script. Because there is no
way known to me how to do that on a non linux system, they do that like this:

``echo "VARNAME=VALUE"``

Everything a script writes to stdout must look like that. You must suppress other
output to stdout.

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
repo                       --repo REPONAME where REPONAME stands on the first line of `repo`
restore_no_tag             removes --tag if it was defined in the default profile
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


pre/post for USB disk
---------------------
pre:

::

  #!/bin/bash
  mount | fgrep 'on /backdisk3 ' >/dev/null
  if test $? -eq 0
  then
        echo DISK3_WAS_MOUNTED=1
  else
        echo DISK3_WAS_MOUNTED=0
        mount /backdisk3 >/dev/null
  fi

post:

::

  #!/bin/bash
  test $DISK3_WAS_MOUNTED -eq 0 && umount /backdisk3


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
Simply place the file `restaround` in `/usr/local/bin`



TODO
====
- pip install restaround
- loading profile: do _no_ last. So, for example, I can do pre and no_pre_cache where pre mounts an external USB drive. OTOH I can already do that with inheritance.
- a profile may have filedir and backup_filedir. The general one must come first. Right now, the order is undefined.

.. _restic: https://restic.net

