Just a few quick notes about the use of test database.

First, you'll need next packages installed:

1) Python 2.2
2) QMTest for Python 2.2 from http://www.codesourcery.com
3) Kinterbasdb for Python 2.2 from http://sf.net/projects/kinterbasdb

Please, take a look at sample-context.win file. You'll need to create your own context file with adjusted paths etc.

This CVS module contains test database for QMTest. QMtest subdirectory contains extension classes for QMtest used by Firebird tests.

KNOW ISSUES:

- Tests currently works only on Windows due to nasty stdin/stdout redirection bug in extension classes on Linux.

Best regards
Pavel Cisar <pcisar _AT_ users.sourceforge.net>
