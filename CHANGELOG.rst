Changelog
=========

0.1.4 release 2020-x-x
------------------------

 * update for restic 0.12.1
 * support Windows
 * backport to Python3.4 for an important client of mine
 * introduce environment variable RESTAROUND_COMMAND for use in pre/post scripts
 * read config files as UTF-8


0.1.3 release 2019-12-24
------------------------

 * --exclude-file is allowed more than once
 * restaround cache is no more - it makes no sense because it is profile agnostic
 * pre scripts may now modify flags in the profile directories


0.1.0 release 2019-11-21
------------------------

  * initial version
