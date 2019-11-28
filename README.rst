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

- ``command`` is a restic command. The file only applies to that command.
- ``no`` will disable something defined in the default profile
- ``flag`` is a restic flag like ``with-atime``
- ``value`` is the value for a flag likei in ``repo=value``
- ``more values`` the flag will be repeated for all values.

restaround knows which restic commands know which flags, it will only
apply the allowed ones to a specific command.

A profile directory might contain files like

::

  backup_direct
  exclude-file
  password-file
  repo
  no_with-atime
  inherit_xxx

A file applies either to all restic_ commands or only to ``command``. 

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

Examples
--------

=========================  ==============================================================
file name                  meaning
=========================  ==============================================================
backup_tag_taga_tagb       backup --tag taga --tag tagb
repo                       --repo REPONAME where REPONAME stands on the first line of `repo`
restore_no_tag             removes --tag if it was defined in the default profile
=========================  ==============================================================
  


Inheriting
----------
You have two possibilities:

- You can always use symbolic links for all files pointing to another profile.
- A file like inherit_xxxx inherits settings from profile xxxx. You can inherit from any number of other profiles.
  If there is a profile named `default`, it is always inherited from.

One possibility would be to define separate profiles for the source and the repository and then combine them:

=============================== =========================================================
Directory                       Files
=============================== =========================================================
/etc/restaround/default         exclude-caches mountpoint
/etc/restaround/local           password-file repo
/etc/restaround/remote          password-file repo
/etc/restaround/mydata          exclude-file filedir
/etc/restaround/mydata_local    inherit_local inherit_mydata
/etc/restaround/mydata_remote   inherit_asterix inherit_mydata
=============================== =========================================================


Backup mydata on a remote repository and list all snapshots on that repository:

::

  restaround mydata_remote backup
  restaround remote snapshots


Installation
============
Simply place the file `restaround` in `/usr/local/bin`
 
TODO
====
- pip install restaround
- bash auto completion
- more user friendly error messages
- pre and post scripts
 
.. _restic: https://restic.net

