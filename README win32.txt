Just a few quick notes about the use of test database.

First, you'll need next packages installed:

1) Python 2.3 (http://www.python.org/download)
2) Python Win32 Extensions (http://starship.python.net/crew/mhammond/win32/Downloads.html)
3) eGenix.com mx Extensions for Python (http://www.egenix.com/files/python/eGenix-mx-Extensions.html#Download-mxBASE)
4) Kinterbasdb for Python 2.2 from (http://sf.net/projects/kinterbasdb)
5) QMTest for Python 2.2 and above (http://www.codesourcery.com)

Please, take a look at sample-context.win file. You'll need to create your own context file with adjusted paths etc.

This CVS module contains test database for QMTest. QMtest subdirectory contains extension classes for QMtest used by Firebird tests.


create a batch-file:
--------------------------------------------------------------------------------
PATH=C:\Python23\Scripts;%PATH%
qmtest.py gui -C sample-context.win
--------------------------------------------------------------------------------


KNOW ISSUES:

- Tests currently works only on Windows due to nasty stdin/stdout redirection bug in extension classes on Linux.
