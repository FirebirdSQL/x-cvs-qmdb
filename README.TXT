Firebird QA Test Suite
======================

Installation
============

First, you'll need next packages installed:

   1. Firebird, as running tests without it doesn't make sense :).
      http://firebird.sourceforge.net/index.php?op=files&id=engine
   2. Python 2.3
      http://www.python.org/
      If you're using Windows, you may prefer Python from ActiveState.
      http://www.activestate.com/Products/Download/Register.plex?id=ActivePython
   3. eGenix.com MX BASE Extensions for Python.
      http://www.egenix.com/files/python/eGenix-mx-Extensions.html#Download-mxBASE
   4. KinterbasDB for Python 2.3.
      http://sf.net/projects/kinterbasdb
      There are two different versions of KintebasDB for Firebird 1.0 and 1.5 !
   5. QMTest.
      http://www.qmtest.com/
   6. QADBM.
      It's our QA DataBase Manager written in Python. You may get it with your web
      browser from next URL:
      http://firebird.sourceforge.net/qa/qadbm.py
      Save it as qadbm.py

All software listed here is open source. Installation of these packages is straightforward, 
and shouldn't cause you any trouble.

Next you would need the test suite for Firebird, that's created as QMTest test database. A test 
database stores tests, test suites, resources and QMTest extensions. QMTest stores a test database 
in a single directory, which may include many files and subdirectories.

You may have and use many QMTest Test Databases (see below), but only one Test Database is primary, 
and contains all our tests, extensions etc. This main database is called Test Repository. This Repository 
is located on our website at SourceForge, and the qadbm tool is used to pull its content to your private 
Local Repository.

The qadbm (QA DataBase Manager) is a multipurpose utility written in Python. It's a CLI utility with 
it's own command interpreter and integrated help. To list all qadbm commands, use the help command. 
You can get command specific help with help command-name. All qadbm commands are case sensitive !

To get (or update) your Local Test Repository from main, remote one, follow next steps:

   1. Start the qadbm utility.
   2. If you have not started qadbm from directory where your Local Test Repository (should) reside, 
      use REPOSITORY command to specify  its directory.
      For example: repository /home/fbqa
   3. Use UPDATE command to get all Repository content, that isn't or is different in your Local replica.
      For example: update

You can find more information about QADBM tool in README.qadbm file.


Building "runnable" test suite
==============================

Firebird test database contains tests that are designed to run only on specific platform or 
against specified engine versions, and also some tests have different implementations that 
depend on platform or engine version. Running those tests on wrong platform or engine will 
lead to their failure, that would spoil the test run results. So before you can run any test, 
you'll need to build test suite for your platform and engine version.

The Firebird QA toolbox contains a multipurpose utility written in Python called qadbm 
(QA DataBase Manager). It's a CLI utility with it's own command interpreter and integrated help. 
To list all qadbm commands, use the help command. You can get command specific help with help 
command-name. All qadbm commands are case sensitive !

To build platform/engine specific test suite, follow next steps:

   1. Start the qadbm utility.
   2. If you have not started qadbm from directory where Firebird test database resides, use 
      REPOSITORY command to specify main test database directory.
      For example: repository /home/fbqa
   3. Set the desired platform with PLATFORM command. Supported values are "Windows, Linux, 
      HP-UX, FreeBSD, Solaris and Sinix-Z".
      For example: platform Windows
   4. Set the target engine version.
      For example: target 1.5.2
   5. Initialize a new QMTest test database with CREATE command.
      For example: create /home/fbtests
   6. Copy all tests for specified platform and engine version into new QMTest test database 
      with COPY command.
      For example: copy /home/fbtests


Configuration
=============

The last step is definition of context variables. Context variables (usually defined in text file) 
are like environment variables for QMTest, and they define values used by tests that depend on your 
setup (machine names, paths to Firebird tools etc.). Firebird test suite now uses next context 
variables:

    * temp_directory : Directory for temporary files
    * isc4_path : Path to security database, including filename
    * server_location : Hostname where Firebird is located
    * gsec_path : Path to gsec, including filename
    * user_password : Firebird password for user_name user
    * isql_path : Path to isql, including filename
    * gstat_path : Path to gstat, including filename
    * gbak_path : Path to gbak, including filename
    * gfix_path : Path to gfix, including filename
    * user_name : Firebird user used by tests to connect/create database
    * gpre_path : Path to gpre, including filename
    * database_location : Directory where test databases are created

Read the README.context file for any changes in context variables!

Sample context setup for Firebird 1.5 on Linux:

temp_directory=/var/tmp/
isc4_path=/opt/firebird/security.fdb
server_location=localhost:
gsec_path=/opt/firebird/bin/gsec
user_password=masterkey
isql_path=/opt/firebird/bin/isql
gstat_path=/opt/firebird/bin/gstat
gbak_path=/opt/firebird/bin/gbak
gfix_path=/opt/firebird/bin/gfix
user_name=SYSDBA
gpre_path=/opt/firebird/bin/gpre
database_location=/var/tmp/ 


Running tests
=============

All QMTest functionality is available using the qmtest command. On Linux (or any 
other POSIX platform), you can type it straght in shell command-line, as QMTest 
installer should put it in your search path and set it's executable flag (qmtest 
is in fact a Python script). If it doesn't work (because you're on Windows, for 
example), you must type the full path to it, or invoke it through Python interpreter.

It's convenient for Windows users to create a simple .BAT file with next command:

c:\Python23\python c:\python23\scripts\qmtest.py %1 %2 %3 %4 %5 %6 %7 %8 %9

The qmtest command has next structure:

qmtest [ option ...] command [ command-option ...] [ argument ...]

Options
-------

These options can be used with any QMTest command, and must precede the command 
name on the command line.

All options are available in a "long form" prefixed with "--" (two hyphens). Some 
options also may be specified in a "short form" consisting of a single hyphen and 
an one-letter abbreviation. Short-form options may be combined; for example, -abc 
is equivalent to -a -b -c.

-D path, --tdb path

Use the test database located in the directory given by path. This flag overrides the 
value of the environment variable QMTEST_DB_PATH. If neither this flag nor the environment 
variable is specified, QMTest assumes that the current directory should be used as the database.

-h, --help

Display help information, listing commands and general options for the qmtest command.

--version

Describe the version of QMTest in use.

Additional options are available for specific commands; these are presented with each 
command. Options specific to a command must follow the command on the command line. 
Specify the --help (-h) option after the command for a description of the command and 
a list of of available options for that command.

Note:
Because Firebird test suite is stored in QMTest database, you must either run qmtest 
from directory where it's stored, or use the -D or --tdb option.

Commands
--------

There are many qmtest commands (read QMTest documentation for complete list of supported 
commands), but only next three might interest you:

gui command
-----------

Start the graphical user interface.

qmtest gui [ option ...]

The qmtest gui starts the graphical user interface. The graphical user interface is 
accessed through a web browser. You must have a web browser that supports JavaScript to 
use the graphical interface. QMTest has been tested with recent versions of Internet 
Explorer and Mozilla. Other web browsers may or may nor work with QMTest.

The gui command accepts these options:

-A address, --address address

Bind the server to the indicated internet address, which should be a dotted quad. By default, 
the server binds itself to the address 127.0.0.1, which is the address of the local machine. 
If you specify another address, the server will be accessible to users on other machines. 
QMTest does not perform any authentication of remote users, so you should not use this option 
unless you have a firewall in place that blocks all untrusted users.

-c name=value, --context name=value

For details about this option, see the description of the qmtest run command.

-C file, --load-context file

For details about this option, see the description of the qmtest run command.

--daemon

Run the QMTest GUI as a daemon. In this mode, QMTest will detach from the controlling 
terminal and run in the background until explicitly shutdown.

-j count, --concurrency count

For details about this option, see the description of the qmtest run command.

--no-browser

Do not attempt to start a web browser when starting the GUI. QMTest will still print out 
the URL at which the server can be accessed. You can then connect to this URL manually using 
the browser of your choice.

-O file, --outcomes file

For details about this option, see the description of the qmtest run command.

--pid-file path

Specify the path to which the QMTest GUI will write its process ID. This option is useful 
if you want to run QMTest as a daemon. If this option is not provided, no PID file is written. 
If you specify this option, but path is the empty string, QMTest will check the .qmrc configuration 
file for a pid-file entry. If there is no such entry, QMTest will use an appropriate 
platform-specific default value.

--port port

Specify the port on which the QMTest GUI will listen for connections. If this option is not 
provided, QMTest will select an available port automatically.

-T file, --targets file

For details about this option, see the description of the qmtest run command.

Note:
The qmtest gui is the most comfortable way to run tests and to analyze the results, and to perform 
many test-suite related tasks (analyze stored run results, edit or create new tests, set test 
expectations, set context values etc.). You don't need to use any additional options, but using 
-C option to load prepared context values and -P option to set specific port number instead random 
one come very handy.

run command
-----------

Run tests or test suites.

qmtest run [ option ...] [test-name | suite-name...]

The qmtest run command runs tests and displays the results. If no test or suite names are specified, 
QMTest runs all of the tests in the test database. If test or suite names are specified, only those 
tests or suites are run. Tests listed more than once (directly or by inclusion in a test suite) are 
run only once.

The run command accepts these options:

-c name=value, --context name=value

Add a property to the test execution context. The name of the property is name, and its value is set 
to the string value. This option may be specified multiple times.

-C file, --load-context file

Read properties for the test execution context from the file file.

The file should be a text file with one context property on each line, in the format name=value. 
Leading and trailing whitespace on each line are ignored. Also, blank lines and lines that begin 
with "#" (a hash mark) are ignored as comments.

This option may be specified more than once, and used in conjunction with the --context option. 
All of the context properties specified are added to the eventual context. If a property is set 
more than once, the last value provided is the one used.

If this option is not specified, but a file named context exists in the current directory, that file 
is read. The properties specified in this file are processed first; the values in this file can be 
overridden by subsequent uses of the --context option on the command line.

-f format, --format format

Control the format used when displaying results. The format specified must be one of full, brief, 
stats, batch, or none. The brief format is the default if QMTest was invoked interactively; the batch 
format is the default otherwise. In the full format, QMTest displays any annotations provided in test 
results. In the brief mode only the causes of failures are shown; detailed annotations are not shown. 
In the stats format, no details about failing tests are displayed; only statistics showing the number 
of passing and failing tests are displayed. In the batch mode, the summary is displayed first, followed 
by detailed results for tests with unexpected outcomes. In the none mode, no results are displayed, but 
a results file is still created, unless the --no-output option is also provided.

-j count, --concurrency count

Run tests in multiple count concurrent processes on the local computer. On multiprocessor machines, 
the processes may be scheduled to run in parallel on different processors. QMTest automatically collects 
results from the processes and presents combines test results and summary. By default, one process is used.

This option may not be combined with the --targets (-T) option.

--no-output

Do not produce a test results file.

-o file, --output file

Write full test results to file. Specify "-" (a hyphen) to write results to standard output. If neither 
this option nor --no-output is specified, the results are written to the file named results.qmr in 
the current directory.

-O file, --outcomes file

Treat file as a set of expected outcomes. The file must have be a results file created either by qmtest 
run, or by saving results in the graphical user interface. QMTest will expect the results of the current 
test run to match those specified in the file and will highlight differences from those results.

--random

Run the tests in a random order.

This option can be used to find hidden dependencies between tests in the testsuite. (You may not notice 
the dependencies if you always run the tests in the same order.)

--rerun file

Rerun only those tests that had unexpected outcomes.

The tests run are determined as follows. QMTest starts with all of the tests specified on the command line, 
or, if no tests are explicitly specified, all of the tests in the database. If no expectations file is 
specified (see the description of the --outcomes option), then all tests that passed in the results file 
indicated by the --rerun option are removed form the set of eligible tests. If an expectations file is 
specified, then the tests removed are tests whose outcome in the results file indicated by the --rerun 
option is the same as in the expectations file.

The --rerun provides a simple way of rerunning failing tests. If you run your tests and notice failures, 
you might try to fix those failing tests. Then, you can rerun the failing tests to see if you succeeded 
by using the --rerun option.

--result-stream descriptor

Specify an additional output result stream. The descriptor is in the format described in Section 3.4.2.

--seed integer

If the --random is used, QMTest randomizes the order in which tests are run, subject to the constraints 
described QMTest documentation. By default, the random number generator is seeded using the system time.

For debugging purposes, it is sometimes necessary to obtain a reproducible sequence of tests. Use the --seed 
option to specify the seed for the random number generator.

Note that even with the same random number seed, if tests are run in parallel, scheduling uncertainty may 
still produce variation in the order in which tests are run.

-T file, --targets file

Use targets specified in target specification file file. If this option is not present, the QMTest/targets 
in the test database directory will be used. If that file is not present, the tests will be run in serial 
on the local machine.

Notes:

    * Because Firebird test suite depends on context values, if a file named context doesn't exists in 
      the current directory, you must specify the context file with -C option.
    * Each invocation of the qmtest run command is a single test run, and produces a single set of test 
      results and statistics. Specify as arguments the names of tests and test suites to run. Even if you 
      specify a test more than once, either directly or by incorporation in a test suite, QMTest runs it 
      only once.

      If you wish to run all tests in the test database, use the implicit test suite . (a single period; 
      see QMTest documentation), or omit all IDs from the command line. 

summarize command
-----------------

The qmtest summarize displays information stored in a results file.

qmtest summarize [ option  ...] [test-name | suite-name...]

The qmtest summarize extracts information stored in a results file and displays this information on the console. 
The information is formatted just as if the tests had just been run, but QMTest does not actually run the tests.

The summarize command accepts the following options:

-f format, --format format

For details about this option, see the description of the qmtest run command.

-O file, --outcomes file

For details about this option, see the description of the qmtest run command.

--result-stream descriptor

Specify an additional output result stream. The descriptor is in the format described in QMTest documentation. 

Best regards
Pavel Cisar <pcisar _AT_ users.sourceforge.net>
