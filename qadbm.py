#!/usr/bin/python
########################################################################
#
# File:   qaver.py
# Date:   14.06.2004
#
# Contents:
#   Tool for Firebird QA to list and optionally copy tests for specified
#   version of Firebird engine. 
#
#   It depends on new test classes (fbqa.py) with target_version attribute!
#
# Contributors: Pavel Cisar
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

import os
import xml.dom
import xml.dom.minidom
import shutil
from optparse import OptionParser
import cmd

########################################################################
# constants
########################################################################

FILE = 0
ID = 1
TARGET_VERSION = 2
TARGET_PLATFORM = 3
TITLE = 4
AUTHOR = 5
DB_NAME = 6
CREATE_DB_METHOD = 7
POPULATE_METHOD = 8
STATEMENT_TYPE = 9

########################################################################
# classes
########################################################################

class qacmd(cmd.Cmd,object):
  # variables
  prompt = "QADBM>"
  options = {
    "database":"",
    "target":"",
    "platform":"",
    "author":"",
    "lines":20
  }
  testlist = None
  testmap = None
  filtered_testlist = None
  
  def __init__(self,options,**args):
    super(qacmd,self).__init__(**args)
    for k in self.options.keys():
      if hasattr(options,k):
        self.options[k]=getattr(options,k)
  
  def preloop(self):
    """Custom command loop initialization."""
    super(qacmd,self).preloop()
    print """
  QADBM - Firebird QA Database Manager
  Written by Pavel Cisar (c) 2004
  Distributed under IDPL license v1.0
  """
    self.__build_test_list()
    self.__filter_testlist()
    self.__print_db_info()
    print
    print "Type help for list of all commands."
  
  # helper functions
  
  def __get_test_attribute(self,tname,nodelist):
    """Get test attribute value from test XML file.
        tname     Attribute name.
        nodelist   List of XML nodes."""
    for a in nodelist:
      if a.getAttribute('name') == tname:
        c = a.firstChild
        if len(c.childNodes) == 0:
          return ''
        if len(c.childNodes) == 1:
          return c.childNodes[0].data

  def __compare_versions(self,lver, rver):
    """ Compare two versions, returns:
        0 for lver = rver
        -1 for lver < rver
        1 for lver > rver"""
    if lver == None:
      lver = "0"
    if rver == None:
      rver = "0"
    lverlist = lver.split(".")
    rverlist = rver.split(".")
    if len(rverlist) < len(lverlist):
      for i in range(len(lverlist)-len(rverlist)):
        rverlist.append("0")
    if len(rverlist) > len(lverlist):
      for i in range(len(rverlist)-len(lverlist)):
        lverlist.append("0")
    for i in range(len(rverlist)):
      if (int(rverlist[i]) > int(lverlist[i])):
        return -1
      if (int(rverlist[i]) < int(lverlist[i])):
        return 1
    return 0
  
  def __make_test_dict(self,testfile):
    """Returns a dictionary with test attributes from XML test file.
        testfile  XML test filename."""
    tdict = dict()
    tdoc = xml.dom.minidom.parse(testfile)
    fileroot = tdoc.documentElement
    tdict[FILE] = testfile[len(self.options["database"])+1:]
    tdict[ID] = self.__get_test_attribute('test_id',fileroot.childNodes)
    tdict[TARGET_VERSION] = self.__get_test_attribute('target_version',fileroot.childNodes)
    tdict[TARGET_PLATFORM] = self.__get_test_attribute('target_platform',fileroot.childNodes)
    tdict[TITLE] = self.__get_test_attribute('title',fileroot.childNodes)
    tdict[POPULATE_METHOD] = self.__get_test_attribute('populate_method',fileroot.childNodes)
    tdict[DB_NAME] = self.__get_test_attribute('db_name',fileroot.childNodes)
    tdict[STATEMENT_TYPE] = self.__get_test_attribute('statement_type_and_result',fileroot.childNodes)
    tdict[CREATE_DB_METHOD] = self.__get_test_attribute('create_db_method',fileroot.childNodes)
    tdict[AUTHOR] = self.__get_test_attribute('author',fileroot.childNodes)
    return tdict

  def __filter_testlist(self):
    """Create or empty self.filtered_testlist according to defined filter rules."""
    if (self.options["author"] != None ) or \
        (self.options["target"] != None) or \
        (self.options["platform"] != None):
      self.filtered_testlist = filter(self.__test_filter,self.testlist)
      # Engine version filter needs special handling
      if (self.options["target"] != None):
        self.testmap = self.__build_testmap(self.filtered_testlist)
        self.filtered_testlist = filter(self.__map_filter,self.filtered_testlist)
    else:
      self.filtered_testlist = None

  def __map_filter(self,testrec):
    """Filter function for engine version filter. Uses test map."""
    # Check for target version
    test = dict()
    test = self.testmap[testrec[ID]]
    candidate = "0"
    for testversion in test.iterkeys():
      if self.__compare_versions(self.options["target"],testversion) >= 0:
        if self.__compare_versions(candidate,testversion) < 0:
          candidate = testversion
    if (candidate != "0") and (test[candidate][FILE]  != testrec[FILE]):
      return False
    return True
    
  def __build_test_list(self):
    """Builds list of tests from current working test database."""
    print "Scanning test database, please wait..."
    self.testlist = list()
    w = os.walk(self.options["database"])
    for root, dirs, files in w:
      # prune directories that are not test suites
      for dir in dirs:
        dirbase, dirext = os.path.splitext(dir)
        if dirext != '.qms':
          dirs.remove(dir)
      # prune files that are not test files
      for file in files:
        filebase, fileext = os.path.splitext(file)
        if fileext != '.qmt':
          files.remove(file)
        else:
          testfile = os.path.join(root,file)
          self.testlist.append(self.__make_test_dict(testfile))
    #print "%i tests found" % len(self.testlist)

  def __build_testmap(self,testlist):
    """Builds map of test versions from specified list of tests."""
    testmap = dict()
    for test in testlist:
      testid = test[ID]
      if not testmap.has_key(testid):
        testmap[testid] = dict()
        testmap[testid][test[TARGET_VERSION]] = test
      else:
        testmap[testid][test[TARGET_VERSION]] = test
    return testmap

  def __test_filter(self,testrec):
    """Primary test filter function."""
    # Check for valid test format
    if (testrec[TARGET_PLATFORM] == None) or (testrec[TARGET_VERSION] == None) or \
         (testrec[AUTHOR] == None):
      return False
    # Check for platform
    if (self.options["platform"] != None) and \
        (self.options["platform"] != "All") and \
        (testrec[TARGET_PLATFORM] != "All"):
      if (testrec[TARGET_PLATFORM].find(self.options["platform"]) < 0):
        return False
    # Check for author
    if (self.options["author"] != None):
      if (testrec[AUTHOR].find(self.options["author"]) < 0):
        return False
    return True

  def __cmpByID(self,l,r):
    """Copare two test IDs. Used to sort lists of test info record by test ID."""
    return cmp(l[ID],r[ID])

  def __print_db_info(self):
    """Prints information about current working test database."""
    print "Database %s contains %d tests" % (self.options["database"],len(self.testlist))
    if self.filtered_testlist != None:
      print "%d tests respects current filter" % len(self.filtered_testlist)

  def do_shell(self, s):
    """SHELL command."""
    os.system(s) 
  def help_shell(self): 
    print """
    Execute shell commands."""

  def can_exit(self): 
    return True 
  def do_exit(self, s):
    """EXIT command."""
    return True
  def help_exit(self): 
    print """
    Exit the QADBM.
    You can also use the Ctrl-D shortcut.""" 
 
  def do_env(self,s):
    """ENV command."""
    for k in self.options.keys():
      print "%s: %s" % (k,self.options[k])
    print
    self.__print_db_info()
  def help_env(self):
    print """
    Lists QADBM enviroment settings."""
  
  def do_db(self,s):
    """DB/DATABASE command."""
    if s == "":
      self.__print_db_info()
    else:
      if os.path.exists(s):
        self.options["database"] = s
        self.__build_test_list()
        self.__filter_testlist()
        self.__print_db_info()
      else:
        print "Path %s doesn't exists" % s
  def help_db(self):
    print """
    Display or set the directory with test database.
    usage: DB | DATABASE [<directory>]
    
    Without argument, it will display the current settings,
    otherwise it sets working test database to specified directory."""
  
  do_database = do_db
  help_database = help_db

  def do_platform(self,s):
    """PLATFORM command."""
    if s == "":
      print "Target platform: %s" % self.options["platform"]
    else:
      self.options["platform"] = s
      self.__filter_testlist()
    self.__print_db_info()
  def help_platform(self):
    print """
    Display or set the target platform.
    usage: PLATFORM [<plaform_name>[:<platform_name>...]]
    
    Without argument, it will display the current setting,
    otherwise it sets target platform to specified value.
    Use only next values: Windows, Linux, Solaris, HP-UX, FreeBSD, 
    Darwin and Sinix-Z
    Multiple values could be specified separated by colon.
    
    This value is used together with TARGET and COPY to create test 
    database for given platform. """

  def do_target(self,s):
    """TARGET command."""
    if s == "":
      print "Target engine version: %s" % self.options["target"]
    else:
      self.options["target"] = s
      self.__filter_testlist()
    self.__print_db_info()
  def help_target(self):
    print """
    Display or set the target platform.
    usage: TARGET [<version>]
    
    Without argument, it will display the current setting,
    otherwise it sets target engine version to specified value.
    
    Each Firebird (final) release has an unique Version Number 
    assigned by Project. This version number is constructed as 
    a dot-separated release version number, where first number
    represents major Firebird version, second number represents 
    a minor version, third number represents an update number, 
    and last, fourth number represents a build number.
    
    This value is used together with PLATFORM and COPY to create 
    test database for given target version. """

  def do_list(self,s):
    """LIST command."""
    if (self.filtered_testlist != None) and (s.upper() != "ALL"):
      testlist = self.filtered_testlist
    else:
      testlist = self.testlist
    testlist.sort(self.__cmpByID)
    line = 1
    for t in testlist:
      for k in t.keys():
        if t[k] == None:
          t[k] = "Unknown"
      print "%-20s %-10s %-42s %-35s %-s" %(t[ID],t[TARGET_VERSION],t[TARGET_PLATFORM],t[TITLE],t[FILE])
      line = line+1
      if line == self.options["lines"]:
        key = raw_input("Press enter to continue or q to abort...")
        if key == "q":
          break
        line = 1
  def help_list(self):
    print """
    List tests from test database.
    usage: LIST [ALL]
    
    This command lists all tests selected for processing, 
    or all tests in database.
    
    If any filter is set (use ENV command to check for current filters), 
    then only selected tests are listed. The ALL clause forces to list all 
    tests in database even if any filter is defined."""

  def do_copy(self,s):
    """COPY command."""
    if self.filtered_testlist != None:
      testlist = self.filtered_testlist
    else:
      testlist = self.testlist
    for t in testlist:
      tf = os.path.join(s,t[FILE])
      td = os.path.dirname(tf)
      if not os.path.isdir(td):
        os.makedirs(td)
      shutil.copy(t[FILE],tf)
  def help_copy(self):
    print """
    Copy selected tests to target directory.
    usage: COPY <directory>
    
    This command will copy selected (or all if no filter rule is defined) tests 
    from current working test database to specified directory. The original 
    subdirectory (test suites) structure is preserved. Any test file that already 
    exists at target location is replaced with one from test database.
    
    Any test file or suite that exists in target location and doesn't exists 
    in test database is left intact!
    
    This command is used together with PLATFORM and TARGET to create test 
    database for specific platform and target engine version. """

  # create command
  def do_create(self,s):
    """CREATE command."""
    if s == "":
      print "Target directory required. See HELP CREATE for details."
    if os.path.isdir(s):
      shutil.rmtree(s)
    os.mkdir(s)
    shutil.copytree(os.path.join(self.options["database"],"QMTest"),os.path.join(s,"QMTest"))
    shutil.copytree(os.path.join(self.options["database"],"resources.qms"),os.path.join(s,"resources.qms"))
  def help_create(self):
    print """
    Create new QMTest test database from current one.
    usage: CREATE <directory>
    
    This command will create a target directory with copy of QMTest 
    (i.e. QMTest extensions) and resources.qms directory from current 
    working database to target directory.
    
    IMPORTANT: If the target directory already exists, it's removed 
    including all subdirectories and files!
    
    This command is used together with COPY to create test database 
    for specific platform and target engine version. """


########################################################################
# program
########################################################################

def main(options, args):
  cmd = qacmd(options)
  cmd.cmdloop()
##~   if options.verbose and not options.quiet:
##~     print "FB version :",options.target
##~     print "Platform   :",options.platform
##~     print "Author     :",options.author
##~     print "Source     :",os.path.abspath(options.source)
##~     if (options.copy != None) and (options.target != None):
##~       print "Copy to    :",os.path.abspath(options.copy)
##~     if options.target == None:
##~       print "List       :",options.info
##~     print ""
##~   testlist = build_test_list(options.source)
##~ 
##~   testlist = filter(test_filter,testlist)
##~   if (options.target != None):
##~     testmap = build_test_map(testlist)
##~     for key, test in testmap.iteritems():
##~       candidate = "0"
##~       for testid in test.iterkeys():
##~         if compare_versions(options.target,testid) >= 0:
##~           if compare_versions(candidate,testid) < 0:
##~             candidate = testid
##~       if candidate != "0":
##~         if not options.quiet:
##~           if options.verbose:
##~             print "Test:",key.ljust(20),"Target:",candidate.ljust(5),test[candidate]
##~           else:
##~             print test[candidate]
##~         if options.copy != None:
##~           shutil.copy(test[candidate],options.copy)
##~   else:
##~     testlist.sort(cmpByID)
##~     for t in testlist:
##~       s = ""
##~       if ("I" in options.info):
##~         s = s + t[ID].ljust(20)
##~       if ("V" in options.info):
##~         s = s + t[TARGET_VERSION].ljust(10)
##~       if ("P" in options.info):
##~         s = s + t[TARGET_PLATFORM].ljust(25)
##~       if ("T" in options.info):
##~         s = s + t[TITLE].ljust(25)
##~       if ("F" in options.info):
##~         s = s + t[FILE]
##~       print s

if __name__ == "__main__":

  parser = OptionParser(version="%prog 1.0")
  parser.add_option("-t","--target",help="FILTER. Target engine version")
  parser.add_option("-p","--platform",help="FILTER. Target platform. Could be: All, Windows, Linux, HP-UX, FreeBSD, Solaris or Sinix-Z",default="All")
  parser.add_option("-a","--author",help="FILTER. Test author")
  parser.add_option("-d","--database",help="Directory with tests, default is current directory",default=os.getcwd())
  parser.add_option("-l","--lines",help="Numeber of lines displayed by LIST command at once",default=20,type="int")
#  parser.add_option("-i","--info",default="IVPF", help="FILTER. Print information about test. F=file, I=id, V=version, P=platform, T=title")

  options, args = parser.parse_args()

  main(options, args)
