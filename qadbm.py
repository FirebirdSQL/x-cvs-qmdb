#!/usr/bin/python
########################################################################
#
# File:   qadbm.py
# Date:   14.06.2004
#
# Contents:
#   Multipurpose tool for Firebird QA to manage QA Test Database. 
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
import md5
import base64
import StringIO
import xml.dom
import xml.dom.minidom
import shutil
import xml
import urllib
from optparse import OptionParser
import cmd

########################################################################
# constants
########################################################################

QADBM_VERSION = "1.1"

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

DIR_CREATE    = "create"
DIR_REMOVE    = "remove"
FILE_CREATE   = "get"
FILE_UPDATE   = "update"
FILE_REMOVE   = "delete"

OPT_LOCAL     = "local"
OPT_REMOTE    = "remote"
OPT_TARGET    = "target"
OPT_PLATFORM  = "platform"
OPT_AUTHOR    = "author"
OPT_DISPLAY   = "display"

########################################################################
# classes
########################################################################

class qacmd(cmd.Cmd,object):
  # variables
  prompt = "QADBM>"
  options = {
    OPT_LOCAL:"",
    OPT_REMOTE:"",
    OPT_TARGET:"",
    OPT_PLATFORM:"",
    OPT_AUTHOR:"",
    OPT_DISPLAY:20
  }
  testlist = None
  testmap = None
  filtered_testlist = None
  localRepository = None
  remoteRepository = None
  action_list = dict()
  
  def __init__(self,options,**args):
    super(qacmd,self).__init__(**args)
    for k in self.options.keys():
      if hasattr(options,k):
        self.options[k]=getattr(options,k)
  
  def preloop(self):
    """Custom command loop initialization."""
    super(qacmd,self).preloop()
    print """
  QADBM - Firebird QA Database Manager v%s
  Written by Pavel Cisar (c) 2004
  Distributed under IDPL license v1.0
  """ % QADBM_VERSION
    self.__build_test_list()
    self.localRepository = self.__buildRepositoryDefinition(self.options[OPT_LOCAL])
    self.__filter_testlist()
    self.__print_db_info()
    print
    print "Type help for list of all commands."
  
# helper functions
  
  def __buildRepositoryDefinition(self, repositoryDir):
    doc = minidom.getDOMImplementation().createDocument(None,"fbqa-repository",None)
    rn = doc.documentElement
    a = doc.createAttribute("format")
    a.nodeValue = "1.0"
    rn.setAttributeNode(a)
    dirnodes = dict()
    first = True

    w = os.walk(repositoryDir)
    for root, dirs, files in w:
      if first:
        n = rn
        first = False
      else:
        n = doc.createElement("directory")
        a = doc.createAttribute("name")
        path,name = os.path.split(root)
        a.nodeValue = name
        n.setAttributeNode(a)
        dirnodes[root] = n
        if dirnodes.has_key(path):
            dirnodes[path].appendChild(n)
        else:
            rn.appendChild(n)
      for file in files:
        if file != "fbqa-repository.xml":
          fn = doc.createElement("file")

          a = doc.createAttribute("name")
          a.nodeValue = file
          fn.setAttributeNode(a)

          a = doc.createAttribute("md5")
          md = md5.new()
          fi = open(os.path.join(root,file),"r")
          fo = StringIO.StringIO()
          base64.encode(fi,fo)
          fi.close()
          fo.pos = 0
          for line in fo:
              md.update(line)
          fo.close()
          a.nodeValue = md.hexdigest()
          fn.setAttributeNode(a)
          n.appendChild(fn)
    return doc
  def __readRepositoryDefinition(self, file):
    doc = minidom.parse(file)
    return doc
  def __buildRepositoryMap(self, map, path, dirNode):
    for n in dirNode.childNodes:
      if n.nodeType == xml.dom.Node.ELEMENT_NODE:
        map[os.path.join(path,n.getAttribute("name"))] = n.getAttribute("md5") 
        if n.nodeName == "directory":
          self.__buildRepositoryMap(map,os.path.join(path,n.getAttribute("name")),n)
  def __compareRepositoryDefinitions(self, localRepository, remoteRepository):
    localRoot = localRepository.getElementsByTagName("fbqa-repository")
    remoteRoot = remoteRepository.getElementsByTagName("fbqa-repository")
    lmap = dict()
    rmap = dict()
    actions = list()
    self.__buildRepositoryMap(lmap,"",localRoot[0])
    self.__buildRepositoryMap(rmap,"",remoteRoot[0])
    for k in lmap.keys():
      if k in rmap:
        if lmap[k] != rmap[k]:
          actions.append((FILE_UPDATE,k))
      else:
        if lmap[k] == "":
          actions.append((DIR_REMOVE,k))
        else:
          actions.append((FILE_REMOVE,k))
    for k in rmap.keys():
      if k not in lmap:
        if rmap[k] == "":
          actions.append((DIR_CREATE,k))
        else:
          actions.append((FILE_CREATE,k))
    return actions

  def __buildSyncActionList(self, ignoredActions):
    action_list = list()
    try:
      print "connecting to %s..." % self.options[OPT_REMOTE],
      remoteFile = urllib.urlopen(os.path.join(self.options[OPT_REMOTE],"fbqa-repository.xml"))
      print "done"
      try:
        print "retreiving repository spec file...",
        self.remoteRepository = self.__readRepositoryDefinition(remoteFile)
        print "done"
      except Exception, e:
        print "Cannot parse the remote repository spec file"
    except Exception, e:
      print "Cannot open the remote repository"
    print "building action list...",
    action_list = self.__compareRepositoryDefinitions(self.localRepository,self.remoteRepository)
    action_list.sort()
    action_list = [i for i in action_list if i[0] not in ignoredActions]
    print "done"
    return action_list
  def __runUpdateActions(self, action_list):
    for action, subject in action_list:
      if action == FILE_REMOVE:
        s = os.path.join(self.options[OPT_LOCAL],subject)
        try:
          print "Removing file %s" % s
          os.remove(s)
        except:
          print "Cannot remove file %s" % s
      elif action == DIR_REMOVE:
        s = os.path.join(self.options[OPT_LOCAL],subject)
        try:
          print "Removing directory %s" % s
          os.rmdir(s)
        except:
          print "Cannot remove directory %s" % s
      elif action == DIR_CREATE:
        s = os.path.join(self.options[OPT_LOCAL],subject)
        try:
          print "Creating directory %s" % s
          os.mkdir(s)
        except:
          print "Cannot create directory %s" % s
      elif (action == FILE_CREATE) or (action == FILE_UPDATE):
        s = os.path.join(self.options[OPT_LOCAL],subject)
        rs = os.path.join(self.options[OPT_REMOTE],subject).replace("\\","/")
        try:
          if action == FILE_CREATE:
            print "Getting file %s" % s
          else:
            print "Updating file %s" % s
          urllib.urlretrieve(rs,s)
        except:
          print rs
          print "Cannot get file %s" % s
    self.localRepository = self.__buildRepositoryDefinition(self.options[OPT_LOCAL])
    f = file(os.path.join(self.options[OPT_LOCAL],"fbqa-repository.xml"),"w")
    f.writelines(self.localRepository.toprettyxml())
    f.close()
    
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
    tdict[FILE] = testfile[len(self.options["local"])+1:]
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
    if (self.options[OPT_AUTHOR] != None ) or \
        (self.options[OPT_TARGET] != None) or \
        (self.options[OPT_PLATFORM] != None):
      self.filtered_testlist = filter(self.__test_filter,self.testlist)
      # Engine version filter needs special handling
      if (self.options[OPT_TARGET] != None):
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
      if self.__compare_versions(self.options[OPT_TARGET],testversion) >= 0:
        if self.__compare_versions(candidate,testversion) < 0:
          candidate = testversion
    if (candidate != "0") and (test[candidate][FILE]  != testrec[FILE]):
      return False
    return True
    
  def __build_test_list(self):
    """Builds list of tests from local test repository."""
    print "Scanning local test repository, please wait..."
    self.testlist = list()
    w = os.walk(self.options["local"])
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
    if (self.options[OPT_PLATFORM] != None) and \
        (self.options[OPT_PLATFORM] != "All") and \
        (testrec[TARGET_PLATFORM] != "All"):
      if (testrec[TARGET_PLATFORM].find(self.options[OPT_PLATFORM]) < 0):
        return False
    # Check for author
    if (self.options[OPT_AUTHOR] != None):
      if (testrec[AUTHOR].find(self.options[OPT_AUTHOR]) < 0):
        return False
    return True

  def __cmpByID(self,l,r):
    """Copare two test IDs. Used to sort lists of test info record by test ID."""
    return cmp(l[ID],r[ID])

  def __print_db_info(self):
    """Prints information about local test repository."""
    print "Local repository %s contains %d tests" % (self.options["local"],len(self.testlist))
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
  
  def do_repository(self,s):
    """REPOSITORY command."""
    if s == "":
      self.__print_db_info()
    else:
      if os.path.exists(s):
        self.options["local"] = s
        self.__build_test_list()
        self.__filter_testlist()
        self.__print_db_info()
      else:
        print "Path %s doesn't exists" % s
  def help_repository(self):
    print """
    Display or set the directory with local test repository.
    usage: REPOSITORY [<directory>]
    
    Without argument, it will display the current settings,
    otherwise it sets local test repository to specified directory."""
  
  def do_platform(self,s):
    """PLATFORM command."""
    if s == "":
      print "Target platform: %s" % self.options[OPT_PLATFORM]
    else:
      self.options[OPT_PLATFORM] = s
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
    suite for given platform. """

  def do_target(self,s):
    """TARGET command."""
    if s == "":
      print "Target engine version: %s" % self.options[OPT_TARGET]
    else:
      self.options[OPT_TARGET] = s
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
    test suite for given target version. """

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
      if line == self.options[OPT_DISPLAY]:
        key = raw_input("Press enter to continue or q to abort...")
        if key == "q":
          break
        line = 1
  def help_list(self):
    print """
    List tests from local test repository.
    usage: LIST [ALL]
    
    This command lists all tests selected for processing, 
    or all tests in local repository.
    
    If any filter is set (use ENV command to check for current filters), 
    then only selected tests are listed. The ALL clause forces to list all 
    tests in local repository even if any filter is defined."""

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
    from local test repository to specified directory. The original subdirectory
    (test suites) structure is preserved. Any test file that already 
    exists at target location is replaced with one from local test repository.
    
    Any test file or suite that exists in target location and doesn't exists 
    in local test repository is left intact!
    
    This command is used together with PLATFORM and TARGET to create test 
    suite for specific platform and target engine version. """

  def do_create(self,s):
    """CREATE command."""
    if s == "":
      print "Target directory required. See HELP CREATE for details."
    if os.path.isdir(s):
      shutil.rmtree(s)
    os.mkdir(s)
    shutil.copytree(os.path.join(self.options["local"],"QMTest"),os.path.join(s,"QMTest"))
    shutil.copytree(os.path.join(self.options["local"],"resources.qms"),os.path.join(s,"resources.qms"))
  def help_create(self):
    print """
    Create new QMTest test suite from local test repository.
    usage: CREATE <directory>
    
    This command will create a target directory with copy of QMTest 
    (i.e. QMTest extensions) and resources.qms directory from local 
    test repository to target directory.
    
    IMPORTANT: If the target directory already exists, it's removed 
    including all subdirectories and files!
    
    This command is used together with COPY to create test suite 
    for specific platform and target engine version. """
  def do_update(self,s):
    """UPDATE command."""
    action_list = self.__buildSyncActionList((DIR_REMOVE,FILE_REMOVE))
    print len(action_list), "actions needed to synchronize local repository:"
    self.__runUpdateActions(action_list)
  def help_update(self):
    print """
    Performs update to local test repository from remote repository.
    usage: UPDATE
    
    This command will compare contents of local and remote repositories,  
    and downloads new or updated tests from remote repository.
    
    IMPORTANT: Files and directories that are in local repository only are
    not deleted! It's intentional to preserve tests you may wrote, but which
    weren't uploaded yet to remote repository. To delete all files and directories
    from local repository that are not also present in remote one, use the
    CLEAN command.
    """
  def do_clean(self,s):
    """CLEAN command."""
    action_list = self.__buildSyncActionList((DIR_CREATE,FILE_CREATE,FILE_UPDATE))
    print len(action_list), "actions needed to cleanup local repository:"
    self.__runUpdateActions(action_list)
  def help_clean(self):
    print """
    Performs cleanup of local test repository.
    usage: CLEAN
    
    This command will compare contents of local and remote repositories,  
    and delete all files and directories from local repository that don't
    exists in remote repository.
    
    IMPORTANT: Files and directories that exists in both repositories are
    not deleted, even if their content differ! Use UPDATE command to update
    local repository from remote one.
    """



########################################################################
# program
########################################################################
    
def main(options, args):
  cmd = qacmd(options)
  cmd.cmdloop()

if __name__ == "__main__":

  parser = OptionParser(version="%prog 1.0")
  parser.add_option("-t","--target",help="FILTER. Target engine version")
  parser.add_option("-p","--platform",help="FILTER. Target platform. Could be: All, Windows, Linux, HP-UX, FreeBSD, Solaris or Sinix-Z",default="All")
  parser.add_option("-a","--author",help="FILTER. Test author")
  parser.add_option("-l","--local",help="Directory with local test repository, default is current directory",default=os.getcwd())
  parser.add_option("-r","--remote",help="URL to remote test repository, default is http://firebirdsql.sf.net/qa/",default="http://localhost/fb-local/qa/")
  parser.add_option("-d","--display",help="Numeber of lines displayed by LIST command at once",default=20,type="int")

  options, args = parser.parse_args()

  main(options, args)
