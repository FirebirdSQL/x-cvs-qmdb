########################################################################
#
# File:   firebird.py
# Author: Pavel Cisar
# Date:   2001-10-12
#
# Contents:
#   Common, Test and Resource classes and function for Firebird QA
#
# Copyright (c) 2002 by Pavel Cisar.  All rights reserved. 
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
########################################################################

########################################################################
# imports
########################################################################

import os, errno, string, sys, time, re, difflib, kinterbasdb

import qm.common
import qm.fields
import qm.test.base
from   qm.test.result import *
from   qm.test.test import *
from   qm.test.resource import *
import qm.executable
import qm.web
from   threading import *

########################################################################
# classes
########################################################################

class SubstitutionField(qm.fields.TextField):
    """A rule for performing a text substitution.

    A 'SubstitutionField' consists of a regular expression pattern and a
    corresponding replacement string.  When the substitution is applied
    to a body of text, all substrings that match the pattern are
    replaced with the substitution string.

    The syntax for the regular expression and the substitution string is
    that of the standard Python 're' (regular expression) module."""

    class_name = "qm.test.classes.file.SubstitutionField"

    # The pattern and replacement string are encoded together into a
    # single string, separated by a semicolon.  Semicolons that occur
    # within the pattern and replacement string are escaped with a
    # backslash.
    #
    # Use 'SplitValue' to extract the pattern and replacement string
    # from a value of this field.


    def __init__(self, name, **properties):
        """Create a new 'SubstitutionField'.

        By default, the pattern and replacement string are empty."""

        # Initialize the base class.
        apply(qm.fields.TextField.__init__, (self, name, ";"), properties)


    def SplitValue(self, value):
        """Split a value of this field into the pattern and replacement string.

        'value' -- A value for this field.

        returns -- A pair '(pattern, replacement_string)'."""

        # Be lenient about an empty string.
        if value == "":
            return ("", "")
        # Break it in half.
        elements = string.split(value, ";", 1)
        # Unescape semicolons in both halves.
        elements = map(lambda e: string.replace(e, r"\;", ";"), elements) 
        return elements


    def FormatValueAsHtml(self, server, value, style, name=None):
        pattern, replacement = self.SplitValue(value)
        # Since we're generating HTML, escape special characters.
        pattern = qm.web.escape(pattern)
        replacement = qm.web.escape(replacement)

        if style in ["new", "edit"]:
            result = '''
            <input type="hidden"
                   name="%(name)s"
                   value="%(value)s"/>
            <table border="0" cellpadding="0" cellspacing="4">
             <tr>
              <td>Pattern:</td>
              <td>&nbsp;</td>
              <td><input type="text"
                         size="40"
                         name="pattern"
                         onchange="update_substitution();"
                         value="%(pattern)s"/></td>
             </tr>
             <tr>
              <td>Replacement:</td>
              <td>&nbsp;</td>
              <td><input type="text"
                         size="40"
                         name="substitution"
                         onchange="update_substitution();"
                         value="%(replacement)s"/></td>
             </tr>
            </table>
            <script language="JavaScript">
            function update_substitution()
            {
              var pattern = document.form.pattern.value;
              pattern = pattern.replace(/;/g, "\\;");
              var substitution = document.form.substitution.value;
              substitution = substitution.replace(/;/g, "\\;");
              document.form.%(name)s.value = pattern + ";" + substitution;
            }
            </script>
            ''' % locals()
            return result

        elif style == "full":
            return '''
            <table border="0" cellpadding="2" cellspacing="0">
             <tr valign="top">
              <td>Pattern:</td>
              <td><tt>%s</tt></td>
             </tr>
             <tr valign="top">
              <td>Replacement:</td>
              <td><tt>%s</tt></td>
             </tr>
            </table>
            ''' % (pattern, replacement)

        else:
            # For all other styles, use the base class implementation.
            return qm.fields.TextField.FormatValueAsHtml(
                self, value, style, name)


    def FormatValueAsText(self, value, columns=72):
        # Don't line-wrap or otherwise futz with the value.
        return value


    def GetHelp(self):
        return """
        A substitution consists of a regular expression pattern and a
        substitution string.  When the substitution is applied, all
        subtrings matching the pattern are replaced with the
        substitution string.  The substitution string may reference
        matched groups in the pattern.

        The regular expression and substitution syntax are those of
        Python's standard "'re' regular expression module"

.. "'re' regular expression module" http://www.python.org/doc/1.5.2p2/lib/module-re.html ."""



class RunServicesBase:
    """A base class for Firebird QA services.

    An 'RunServicesBase' runs a program and checks its standard error output,
    and exit code with expected values.  The program may be provided with
    command-line arguments and/or standard input.

    The run passes if the standard error is empty, and exit code is zero."""


    def MakeEnvironment(self, context):
        """Construct the environment for executing the target program."""

        # Start with any environment variables that are already present
        # in the environment.
        environment = os.environ.copy()
        # Copy context variables into the environment.
        for key, value in context.items():
            name = "QMV_" + key
            environment[name] = value
        return environment


    def RunProgram(self, program, arguments, stdin, context, result):
        """Run the 'program'.

        'program' -- The path to the program to run.

        'arguments' -- A list of the arguments to the program.  This
        list must contain a first argument corresponding to 'argv[0]'.

        'stdin' -- Content of standard input for the program.

        'context' -- A 'Context' giving run-time parameters to the
        test.

        'result' -- A 'Result' object.  The outcome will be
        'Result.PASS' when this method is called.  The 'result' may be
        modified by this method to indicate outcomes other than
        'Result.PASS' or to add annotations."""

        # Construct the environment.
        environment = self.MakeEnvironment(context)
        e_stdin = stdin
        c = {}
        for pair in context.items():
            c[pair[0]] = pair[1]
            for substitution in c.keys():
                pattern = "$("+substitution.upper()+")"
                replacement = context[substitution]
                e_stdin = e_stdin.replace(pattern, replacement)
        basename   = os.path.split(arguments[0])[-1]
        qm_exec    = qm.executable.Filter(e_stdin, -2)

        try:
            exit_status= qm_exec.Run(arguments, environment)
            stdout = qm_exec.stdout
            stderr = qm_exec.stderr
            causes = []

            if not (sys.platform == "win32" or os.WIFEXITED(exit_status)):
                causes.append("exit_code")
                result["RunProgram.exit_code"] = str(exit_status)

            elif os.WIFSIGNALED(exit_status):
                self.__cause= "Process %s terminated by signal %d." % (basename, os.WTERMSIG(exit_status))

            elif os.WIFSTOPPED(exit_status):
                self.__cause= "Process %s stopped by signal %d." % (basename, os.WSTOPSIG(exit_status))

            else:
                self.__cause= "Process %s terminated abnormally." % basename

            # Check to see that the standard error matches.
            if stderr:
                causes.append("standard error")
                result["RunProgram.stderr"] = "'''" + stderr + "'''"
            # If anything went wrong, the test failed.
            if causes:
                result.Fail("Unexpected %s." % string.join(causes, ", "))
        except:
            result.NoteException()



class FirebirdService(RunServicesBase):
    """Class for Firebird QA services.

    This class is used by Resource and Test classes to perform various tasks
    on Firebird server or database."""

    def __init__(self, context):
        """Initialization parameters

        'context' -- A 'Context' giving run-time parameters to the
        test."""

#        RunServiceBase.__init__()
        self.__context = context

    def RestoreDatabase(self, database, backupfile, arguments, result):
        """Restore a database from a backup file.

        'database' -- A database specification.

        'backupfile' -- A backup file name.

        'arguments' -- A list of the arguments to the GBAK without backup file name
        and database location.

        'result' -- A 'Result' object.  The outcome will be
        'Result.PASS' when this method is called.  The 'result' may be
        modified by this method to indicate outcomes other than
        'Result.PASS' or to add annotations."""

        self.RunProgram("\""+self.__context["gbak_path"]+"\"",
                        [ self.__context["gbak_path"] ] + [ "-C ", backupfile ]
                        + arguments + [ database ],
                        "", self.__context, result)

    def RunScript(self, database, script, arguments, result):
        """Run an ISQL script.

        'database' -- A database specification.

        'script' -- An ISQL script.

        'arguments' -- A list of the arguments to the ISQL without database location.

        'result' -- A 'Result' object.  The outcome will be
        'Result.PASS' when this method is called.  The 'result' may be
        modified by this method to indicate outcomes other than
        'Result.PASS' or to add annotations."""

        self.RunProgram("\""+self.__context["isql_path"]+"\"",
                        [ self.__context["isql_path"] ] + [ database ] + arguments,
                        script, self.__context, result)

    def RunGsec(self, script, arguments, result):
        """Run an ISQL script.

        'script' -- An (optional) GSEC script.

        'arguments' -- A list of the arguments to the GSEC without ISC4 database location and
        sysdba username and password.

        'result' -- A 'Result' object.  The outcome will be
        'Result.PASS' when this method is called.  The 'result' may be
        modified by this method to indicate outcomes other than
        'Result.PASS' or to add annotations."""
        try:
            self.RunProgram("\""+self.__context["gsec_path"]+"\"",
                        [ self.__context["gsec_path"], "-database", self.__context["server_location"]+ self.__context["isc4_path"], "-user", "SYSDBA", "-password", "masterkey" ]+arguments,
                        script, self.__context, result)
        except:
           result.NoteException()



class FirebirdDatabaseResource(Resource):
    """Resource class to manage a Firebird Database.

    An instance of this resource creates a Firebird database during
    setup, and deletes it during cleanup.  The full path to the
    database is available to tests via a context property.

    This class needs some context properties set to work properly.
    These properties are server_location, database_location,
    gbak_path and isql_path. Please refer to the Firebird QA documentation 
    for details about these properties."""

    arguments = [
        qm.fields.TextField(
            name="database_path_property",
            title="Database Path Property Name",
            description="The name of the context property which is "
            "set to the path to the database.",
            default_value="database_path"
            ),
        qm.fields.TextField(
            name="database_name",
            title="Database Name",
            description="""The Database name. 

            This value is concatenated with server and database location from
            context.""",
            default_value="database_name"
            ),
        qm.fields.TextField(
            name="user_name",
            title="User Name",
            description="The name of the user / owner for created database.",
            default_value="SYSDBA"
            ),
        qm.fields.TextField(
            name="user_password",
            title="User Password",
            description="The password of the user / owner for created database.",
            default_value="masterkey"
            ),
        qm.fields.EnumerationField(
            name="character_set",
            title="Character set",
            description="Default character set for database",
            enumerals = ["NONE","ASCII","BIG_5","CYRL","DOS437","DOS850","DOS852",
                "DOS857","DOS860","DOS861","DOS863","DOS865","EUCJ_0208","GB_2312",
                "ISO8859_1","KSC_5601","NEXT","OCTETS","SJIS_0208","UNICODE_FSS",
                "WIN1250","WIN1251","WIN1252","WIN1253","WIN1254","LATIN2"],
            default_value="NONE",
            ),
        qm.fields.EnumerationField(
            name="page_size",
            title="Page size",
            description="Page size for new database (defaults to 4096).",
            enumerals = ["1024","2048","4096","8192","16384"],
            default_value="4096",
            ),
        qm.fields.EnumerationField(
            name="sql_dialect",
            title="SQL dialect",
            description="The SQL dialect under which to execute the statement "
            "(defaults to 3).",
            enumerals = ["1","2","3"],
            default_value="3",
            ),
        qm.fields.TextField(
            name="backup_file",
            title="Backup File",
            description="""The full path to a backup file.

            If specified, new database is restored from this backup file.""",
            ),
        qm.fields.TextField(
            name="init_script",
            title="Database Initialization Script",
            description="""The contents of the database initialization SQL script.

            This script is executed by isql to initialize new database resource.
            Leave it empty if you don't need to create objects in new database or
            when you use backup file to create it.""",
            verbatim="true",
            multiline="true"
            ),
        ]

    def SetUp(self, context, result):
        # Generate a database.
        self.__FirebirdServices = FirebirdService(context)
        self.__database_path = "".join((context["server_location"], \
            context["database_location"],self.database_name))
        context["user_name"] = self.user_name
        context["user_password"] = self.user_password
        if self.backup_file:
            try:
                self.__FirebirdServices.RestoreDatabase(context["database_location"]+self.database_name,
                self.backup_file,
                ["-P",self.page_size,"-user",self.user_name,"-password",self.user_password],
                result)
            except:
                result.NoteException()

            else:
                # Setup succeeded.  Store the path to the database where
                # tests can get at it.
                context[self.database_path_property] = self.__database_path
              
        else:
            self.__sql_statement = "CREATE DATABASE '"+self.__database_path + \
              "' USER '"+self.user_name+"' PASSWORD '"+self.user_password + \
              "' PAGE_SIZE "+self.page_size+" DEFAULT CHARACTER SET " + \
              self.character_set
#            print self.__sql_statement
            try:
                # Create the database.
                self.__con = kinterbasdb.create_database(self.__sql_statement,int(self.sql_dialect))
                self.__con.close()
#                print "Database created !"
                if self.init_script:
                    try:
                        self.__FirebirdServices.RunScript(context["database_location"]+self.database_name,
                        self.init_script,
                        ["-user",self.user_name,"-password",self.user_password],
                        result)
                    except:
                        result.NoteException()
            except Exception, error:
                # Setup failed.
                cause = "Database creation failed.  %s" % str(error)
                result.Fail(cause)
            else:
                # Setup succeeded.  Store the path to the database where
                # tests can get at it.
                context[self.database_path_property] = self.__database_path

    def CleanUp(self, result):
        # Drop a database.
        try:
            self.__con = kinterbasdb.connect(dsn=str(self.__database_path), \
                user=str(self.user_name), password=str(self.user_password))
            self.__con.drop_database()
        except Exception, error:
            # Cleanup failed.
            cause = "Database deletion failed.  %s" % str(error)
            result.Fail(cause)
#        else:
#            pass


class FirebirdInitScriptResource(Resource):
    """Resource class to initialize a Firebird Database by given ISQL script.

    An instance of this resource must have a Firebird database resource
    as prerequisite resource. An ISQL script is run on this database to
    provide additional, test-specific initialization for database resource.
    Any changes made to the database will persist, and it's not deleted 
    during cleanup.

    This class needs some context properties set to work properly.
    These properties are server_location, database_path (provided by Database resource)
    and isql_path. Please refer to the Firebird QA documentation for 
    details about these properties."""

    arguments = [
        qm.fields.TextField(
            name="database_path_property",
            title="Database Path Property Name",
            description="The name of the context property which is "
            "set to the path to the database by Database Resource.",
            default_value="database_path"
            ),
        qm.fields.EnumerationField(
            name="sql_dialect",
            title="SQL dialect",
            description="The SQL dialect under which to execute the statement "
            "(defaults to 3).",
            enumerals = ["1","2","3"],
            default_value="3",
            ),
        qm.fields.TextField(
            name="init_script",
            title="Database Initialization Script",
            description="""The contents of the database initialization SQL script.

            This script is executed by isql to initialize new database resource.
            Leave it empty if you don't need to create objects in new database or
            when you use backup file to create it.""",
            verbatim="true",
            multiline="true"
            ),
        ]

    def SetUp(self, context, result):
        # Run a script.
        self.__FirebirdServices = FirebirdService(context)
        try:
            self.__FirebirdServices.RunScript(context[self.database_path_property],
            self.init_script,
            ["-user",self.user_name,"-password",self.user_password],
            result)
        except:
            result.NoteException()

    def CleanUp(self, result):
        # Drop a script ?
        pass


class FirebirdUserResource(Resource):
    """Resource class to manage a Firebird User.

    An instance of this resource creates a Firebird user during
    setup, and deletes it during cleanup.

    This class needs some context properties set to work properly.
    These properties are server_location, gsec_path and isc4_path. 
    Please refer to the Firebird QA documentation for details about these properties."""

    arguments = [
        qm.fields.TextField(
            name="user_name",
            title="User Name",
            description="The name of the user.",
            default_value="USER1"
            ),
        qm.fields.TextField(
            name="user_password",
            title="User Password",
            description="The password of the user.",
            default_value="firebirdqa"
            ),
        qm.fields.IntegerField(
            name="uid",
            title="User ID",
            description="",
            ),
        qm.fields.IntegerField(
            name="gid",
            title="Group ID",
            description="",
            ),
        ]

    def SetUp(self, context, result):
        # Create a user.
        self.__FirebirdServices = FirebirdService(context)
        try:
            self.__FirebirdServices.RunGsec("", [ "-add",str(self.user_name),"-pw",str(self.user_password),
            "-uid",str(self.uid),"-gid",str(self.gid) ], 
            result)

        except:
            result.NoteException()

    def CleanUp(self, result):
        # Drop a user.
        try:
            self.__FirebirdServices.RunGsec("", [ "-delete",self.user_name], result)
        except:
            result.NoteException()



class FirebirdTestBase(Test):
    """A base class for Firebird tests.

    An 'FirebirdTestBase' introduce common attributes and functionality for Firebird tests.
    """

    arguments = [
        qm.fields.TextField(
            name="test_id",
            title="Test ID",
            not_empty_text=1,
            description="""An unique ID assigned to test.

            The ID is usualy constructed as author's name and sequence number.
            For example: skopalik_0001"""
            ),
        qm.fields.TextField(
            name="author",
            title="Author",
            not_empty_text=1,
            description="""Author's nickname.

            Use the nickname listed in AUTHORS.TXT. For new test authors, don't forget
            to add appropriate record (nickname and e-mail) in this file!"""
            ),
        qm.fields.TextField(
            name="bug_id",
            title="Bug identifier",
            description="""Bug Identifier

            If this test covers a bug, it should have a bug tracker entry.
            Enter the ID from bug tracker here (usualy a number)."""
            ),
        qm.fields.EnumerationField(
            name="test_type",
            title="Type of test",
            description="""Test could be positive or negative (defaults to POSITIVE).

            Positive test checks if something pass without error, 
            while negative test checks if something fail.""",
            enumerals = ["Positive","Negative"],
            default_value="Positive",
            ),
        qm.fields.TextField(
            name="title",
            title="Title",
            not_empty_text=1,
            description="""Short descriptive title.

            This is a short, descriptive name for test. Should describe what's tested.
            For example: ALTER DATABASE ADD FILE"""
            ),
        qm.fields.TextField(
            name="description",
            title="Description",
            verbatim="true",
            multiline="true",
            description="""Full test description.

            Please describe how the test is supposed to work, what's tested and how,
            possible points of failure etc."""
            )
        ]


class FirebirdISQLTestBase(FirebirdTestBase):
    """Check a program's output and exit code.

    An 'FirebirdExecTestBase' runs a program and compares its standard output,
    standard error, and exit code with expected values.  The program
    may be provided with command-line arguments and/or standard
    input.

    The test passes if the standard output, standard error, and
    exit code are identical to the expected values."""

    arguments = [
        qm.fields.TextField(
            name="stdin",
            title="Standard Input",
            verbatim="true",
            multiline="true",
            description="""The contents of the standard input stream.

            If this field is left blank, the standard input stream will
            contain no data."""
            ),

        qm.fields.SetField(qm.fields.TextField(
            name="environment",
            title="Environment",
            description="""Additional environment variables.

            By default, QMTest runs tests with the same environment that
            QMTest is running in.  If you run tests in parallel, or
            using a remote machine, the environment variables available
            will be dependent on the context in which the remote test
            is executing.

            You may add variables to the environment.  Each entry must
            be of the form 'VAR=VAL'.  The program will be run in an
            environment where the environment variable 'VAR' has the
            value 'VAL'.  If 'VAR' already had a value in the
            environment, it will be replaced with 'VAL'.

            In addition, QMTest automatically adds an environment
            variable corresponding to each context property.  The name
            of the environment variable is the name of the context
            property, prefixed with 'QMV_'.  For example, if the value
            of the context property named 'target' is available in the
            environment variable 'QMV_target'.""" )),
        
        qm.fields.IntegerField(
            name="exit_code",
            title="Exit Code",
            description="""The expected exit code.

            Most programs use a zero exit code to indicate success and a
            non-zero exit code to indicate failure.  Under Windows,
            QMTest does not accurately report the exit code of the
            program; all programs are treated as if they exited with
            code zero."""
            ),

        qm.fields.TextField(
            name="stdout",
            title="Standard Output",
            verbatim="true",
            multiline="true",
            description="""The expected contents of the standard output stream.

            If the output written by the program does not match this
            value, the test will fail."""
            ),
        
        qm.fields.TextField(
            name="stderr",
            title="Standard Error",
            verbatim="true",
            multiline="true",
            description="""The expected contents of the standard error stream.

            If the output written by the program does not match this
            value, the test will fail."""
            ), 
        qm.fields.SetField(SubstitutionField(
            name="substitutions",
            title="Substitutions",
            description="""Regular expression substitutions.

            Each substitution will be applied to both the expected and
            actual stdout of the ISQl.  The comparison will be
            performed after the substitutions have been performed.

            You can use substitutions to ignore insignificant
            differences between the expected and autual ISQL output."""))
        ]


    def MakeEnvironment(self, context):
        """Construct the environment for executing the target program."""

        # Start with any environment variables that are already present
        # in the environment.
        environment = os.environ.copy()
        # Copy context variables into the environment.
        for key, value in context.items():
            name = "QMV_" + key
            environment[name] = value
        # Extract additional environment variable assignments from the
        # 'Environment' field.
        for assignment in self.environment:
            if "=" in assignment:
                # Break the assignment at the first equals sign.
                variable, value = string.split(assignment, "=", 1)
                environment[variable] = value
            else:
                raise ValueError, \
                      qm.error("invalid environment assignment",
                               assignment=assignment)
        return environment


    def RunProgram(self, program, arguments, context, result):
        """Run the 'program'.

        'program' -- The path to the program to run.

        'arguments' -- A list of the arguments to the program.  This
        list must contain a first argument corresponding to 'argv[0]'.

        'context' -- A 'Context' giving run-time parameters to the
        test.

        'result' -- A 'Result' object.  The outcome will be
        'Result.PASS' when this method is called.  The 'result' may be
        modified by this method to indicate outcomes other than
        'Result.PASS' or to add annotations."""

        # Construct the environment.
        environment = self.MakeEnvironment(context)
        e_stdin = self.stdin
        c = {}
        for pair in context.items():
            c[pair[0]] = pair[1]
            for substitution in c.keys():
                pattern = "$("+substitution.upper()+")"
                replacement = context[substitution]
                e_stdin = e_stdin.replace(pattern, replacement)

        basename   = os.path.split(arguments[0])[-1]
        qm_exec    = qm.executable.Filter(e_stdin, -2)

        try:
            exit_status= qm_exec.Run(arguments, environment)
            stdout = qm_exec.stdout
            stderr = qm_exec.stderr
            causes = []

            if not (sys.platform == "win32" or os.WIFEXITED(exit_status)):
                causes.append("exit_code")
                result["RunProgram.exit_code"] = str(exit_status)

            elif os.WIFSIGNALED(exit_status):
                self.__cause= "Process %s terminated by signal %d." % (basename, os.WTERMSIG(exit_status))

            elif os.WIFSTOPPED(exit_status):
                self.__cause= "Process %s stopped by signal %d." % (basename, os.WSTOPSIG(exit_status))

            else:
                self.__cause= "Process %s terminated abnormally." % basename

            # Check to see if the standard output matches.
            # First strip out ISQL junk
            stdout_stripped = re.sub("Database:.*\n","",stdout)
            stdout_stripped = re.sub("SQL>\s*","",stdout_stripped)
            stdout_stripped = re.sub("CON>\s*","",stdout_stripped)
            stdout_stripped = re.sub("-->\s*","",stdout_stripped)
            stdout_stripped = self.__PerformSubstitutions(stdout_stripped)
            stdout_stripped = re.compile("^\s+",re.I+re.M).sub("",stdout_stripped)
            stdout_stripped = re.compile("\s+$",re.I+re.M).sub("",stdout_stripped)

            self.stdout_stripped = re.sub("Database:.*\n","",self.stdout)
            self.stdout_stripped = re.sub("SQL>\s*","",self.stdout_stripped)
            self.stdout_stripped = re.sub("CON>\s*","",self.stdout_stripped)
            self.stdout_stripped = re.sub("-->\s*","",self.stdout_stripped)
            self.stdout_stripped = self.__PerformSubstitutions(self.stdout_stripped)
            self.stdout_stripped = re.compile("^\s+",re.I+re.M).sub("",self.stdout_stripped)
            self.stdout_stripped = re.compile("\s+$",re.I+re.M).sub("",self.stdout_stripped)

            if stdout_stripped != self.stdout_stripped:
                causes.append("standard output")
                result["ExecTest.stdin"] = "<pre>" + e_stdin + "</pre>"
                result["ExecTest.stdout_expected"] = "<pre>" + self.stdout + "</pre>"
                result["ExecTest.stdout"] = "<pre>" + stdout + "</pre>"
                result["ExecTest.stdout_stripped"] = "<pre>" + stdout_stripped + "</pre>"
                result["ExecTest.stdout_stripped_expected"] = "<pre>" + self.stdout_stripped + "</pre>"
                result["ExecTest.stripped_diff"] = "<pre>"+'\n'.join(difflib.ndiff(stdout_stripped.splitlines(0),self.stdout_stripped.splitlines(0)))+"</pre>"
            # Check to see that the standard error matches.
            stderr_stripped = re.sub("Use CONNECT or CREATE DATABASE to specify a database.*\n","",stderr)
            if stderr_stripped != self.stderr:
                causes.append("standard error")
                result["ExecTest.stdin"] = "<pre>" + e_stdin + "</pre>"
                result["ExecTest.stderr"] = "<pre>" + stderr + "</pre>"
                result["ExecTest.expected_stderr"] = "<pre>" + self.stderr + "</pre>"
            # If anything went wrong, the test failed.
            if causes:
                result.Fail("Unexpected %s." % string.join(causes, ", "))
        except:
            result.NoteException()


    def SplitValue(self, value):
        """Split a value of this field into the pattern and replacement string.

        'value' -- A value for this field.

        returns -- A pair '(pattern, replacement_string)'."""

        # Be lenient about an empty string.
        if value == "":
            return ("", "")
        # Break it in half.
        elements = string.split(value, ";", 1)
        # Unescape semicolons in both halves.
        elements = map(lambda e: string.replace(e, r"\;", ";"), elements) 
        return elements

    def __PerformSubstitutions(self, text):
        """Perform substitutions on a body of text.

        returns -- The string 'text', processed with the substitutions
        configured for this test instance."""

        for substitution in self.substitutions:
            pattern, replacement = self.SplitValue(substitution)
            text = re.compile(pattern,re.M).sub(replacement, text)
        return text
        
    
class FirebirdISQLTest(FirebirdISQLTestBase):
    """Check a program's output and exit code.

    An 'FirebirdISQLTest' runs ISQL by using the 'exec' system call."""

    def Run(self, context, result):
        """Run the test.

        'context' -- A 'Context' giving run-time parameters to the
        test.

        'result' -- A 'Result' object.  The outcome will be
        'Result.PASS' when this method is called.  The 'result' may be
        modified by this method to indicate outcomes other than
        'Result.PASS' or to add annotations."""

        # Was the program not specified?

        self.program = context["isql_path"]

        if context.has_key("database_path"):
            database = context["database_path"]
        else:
            database = ""
        self.RunProgram(self.program,
			[ self.program , database ,
                        "-user", context["user_name"], "-password", context["user_password"] ],
                        context, result)





########################################################################
# Local Variables:
# mode: python
# indent-tabs-mode: nil
# fill-column: 72
# End:
