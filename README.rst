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


Definition
----------
A profile is implemented as a directory. Most files in that directory correspond to
a restic_ flag - same spelling. In restic_, however the positional flags sometimes have
names which do not allow this like restic backup: ``FILE/DIR [FILE/DIR] ...``.
In that case, say ``restaround help backup`` to see the name restaround wants, in this case ``filedir``.

The full name can be built as follows:

  `[command] [no] [flag] [value] [value] ...`

where the separate parts are joined by underlines. This character is not part
of any restic_ command or argument. If you need _ in a value, do not use
the [value] part. There is an alternative.

- ``command`` is a restic command. The file only applies to that command. If not given, it applies to all commands
- ``no`` will disable something defined in the inherited profiles
- ``flag`` is a restic flag like ``with-atime``. Special flags are ``inherit``, ``pre`` and ``post``
- ``value`` is the value for a flag likei in ``repo=value``
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

The restic_ flags cacert, cachedir, exclude-file, include-file, password-file are special:
The corresponding file holds the content, so exclude-file extends to --exclude-file=profile/exclude-file
Of course symbolic links are allowed. So cacert may be a symbolic link to the certification file.

For flags with just one argument like --repo create profile/repo with one line.

The alternative form flag_value1_value2_value3 is treated like a file with 3 lines.
So 'exclude_a_b_dirc' would extend into --exclude a --exclude b --exclude dirc
Such a file must be empty. Of course this form can only be used if the resulting file name
is legal for the file system and if no part contains an underline.

`tag` in restic_ is used as both a command and as an argument, but this should pose no problem.

tag_tag is the "tag" flag applied only to command "tag"
tag_taga  is the "tag" flag applied to all commands as --tag taga

If you really want to do --tag=tag, you can define a file named tag (or tag_tag) with
one line "tag".


Special flags
-------------

In addition to the restic_ flags, there are the special flags ``inherit``, see
Inheriting_, and ``pre`` / ``post``, see `Pre- and Postscripts`_.



Inheriting
----------

You can always use symbolic links for all files pointing to another profile. But there is
another way: The special flag ``inherit``. It can be defined just like a normal flag but
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
do pre and no_pre_cache where pre mounts an external USB drive. So only for
the ``cache`` command, the USB drive will not be mounted.

Until this is implemented, you can do that with inheritance.



Pre- and Postscripts
--------------------

To be implemented.

The special flag ``pre`` defines a script to be executed before the restic_ command. If the
exit code is not 0, restaround aborts.

The special flag ``post`` defines a script to be executed after the restic_ command. It
gets the exit code of the restic_ command in the shell variable ``RESTIC_RESULT``.

This also allows defining chains like backup, check, forget, prune. Just be careful
not to define endless loops.



Examples
--------

=========================  ==============================================================
file name                  meaning
=========================  ==============================================================
backup_tag_taga_tagb       backup --tag taga --tag tagb
repo                       --repo REPONAME where REPONAME stands on the first line of `repo`
restore_no_tag             removes --tag if it was defined in the default profile
=========================  ==============================================================



Installation
============
Simply place the file `restaround` in `/usr/local/bin`



TODO
====
- pip install restaround
- more user friendly error messages
- pre and post scripts
- check should exit 1 for failure, restic does not
- restaround cpal will use cp -al and create something like repodir/../repodir.before_prune.YYYY-MM-DDThh:mm:ss
- restaround rmcpal removes it


.. _restic: https://restic.net

