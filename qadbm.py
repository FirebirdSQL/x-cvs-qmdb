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

########################################################################
# program
########################################################################

def get_test_attribute(tname,nodelist):
  for a in nodelist:
    if a.getAttribute('name') == tname:
      c = a.firstChild
      if len(c.childNodes) == 0:
        return ''
      if len(c.childNodes) == 1:
        return c.childNodes[0].data

def make_test_dict(testfile):
  tdict = dict()
  tdoc = xml.dom.minidom.parse(testfile)
  fileroot = tdoc.documentElement
  tdict[FILE] = testfile
  tdict[ID] = get_test_attribute('test_id',fileroot.childNodes)
  tdict[TARGET_VERSION] = get_test_attribute('target_version',fileroot.childNodes)
  tdict[TARGET_PLATFORM] = get_test_attribute('target_platform',fileroot.childNodes)
  tdict[TITLE] = get_test_attribute('title',fileroot.childNodes)
  tdict[POPULATE_METHOD] = get_test_attribute('populate_method',fileroot.childNodes)
  tdict[DB_NAME] = get_test_attribute('db_name',fileroot.childNodes)
  tdict[STATEMENT_TYPE] = get_test_attribute('statement_type_and_result',fileroot.childNodes)
  tdict[CREATE_DB_METHOD] = get_test_attribute('create_db_method',fileroot.childNodes)
  tdict[AUTHOR] = get_test_attribute('author',fileroot.childNodes)
  return tdict


def build_test_list(root_dir):
  test_list = list()
  w = os.walk(root_dir)
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
        test_list.append(make_test_dict(testfile))
  return test_list

def test_filter(testrec):
  # Check for platform
  # print testrec
  if (options.platform != None) and (options.platform != "All") and (testrec[TARGET_PLATFORM] != "All"):
    if (testrec[TARGET_PLATFORM].find(options.platform) < 0):
      return False
  # Check for author
  if (options.author != None):
    if (testrec[AUTHOR].find(options.author) < 0):
      return False
  return True

def build_test_map(test_list):
  test_map = dict()
  for test in test_list:
    testid = test[ID]
    if not test_map.has_key(testid):
      test_map[testid] = dict()
      test_map[testid][test[TARGET_VERSION]] = test[FILE]
    else:
      test_map[testid][test[TARGET_VERSION]] = test[FILE]
  return test_map

def compare_versions(lver, rver):
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

def cmpByID(l,r):
  return cmp(l[ID],r[ID])

# main program

def main():
  if options.verbose and not options.quiet:
    print "FB version :",options.target
    print "Platform   :",options.platform
    print "Author     :",options.author
    print "Source     :",os.path.abspath(options.source)
    if (options.copy != None) and (options.target != None):
      print "Copy to    :",os.path.abspath(options.copy)
    if options.target == None:
      print "List       :",options.info
    print ""
  testlist = build_test_list(options.source)

  testlist = filter(test_filter,testlist)
  if (options.target != None):
    testmap = build_test_map(testlist)
    for key, test in testmap.iteritems():
      candidate = "0"
      for testid in test.iterkeys():
        if compare_versions(options.target,testid) >= 0:
          if compare_versions(candidate,testid) < 0:
            candidate = testid
      if candidate != "0":
        if not options.quiet:
          if options.verbose:
            print "Test:",key.ljust(20),"Target:",candidate.ljust(5),test[candidate]
          else:
            print test[candidate]
        if options.copy != None:
          shutil.copy(test[candidate],options.copy)
  else:
    testlist.sort(cmpByID)
    for t in testlist:
      s = ""
      if ("I" in options.info):
        s = s + t[ID].ljust(20)
      if ("V" in options.info):
        s = s + t[TARGET_VERSION].ljust(10)
      if ("P" in options.info):
        s = s + t[TARGET_PLATFORM].ljust(25)
      if ("T" in options.info):
        s = s + t[TITLE].ljust(25)
      if ("F" in options.info):
        s = s + t[FILE]
      print s

if __name__ == "__main__":
  FILE             = 0
  ID               = 1
  TARGET_VERSION   = 2
  TARGET_PLATFORM  = 3
  TITLE            = 4
  AUTHOR           = 5
  DB_NAME          = 6
  CREATE_DB_METHOD = 7
  POPULATE_METHOD  = 8
  STATEMENT_TYPE   = 9

  parser = OptionParser(version="%prog 1.0")
  parser.add_option("-v","--verbose",action="store_true", default=False,help="more verbose output")
  parser.add_option("-q","--quiet",action="store_true", default=False,help="do not list tests to stdout")
  parser.add_option("-t","--target",help="FILTER. Target engine version")
  parser.add_option("-p","--platform",help="FILTER. Target platform. Could be: All, Windows, Linux, HP-UX, FreeBSD, Solaris or Sinix-Z")
  parser.add_option("-a","--author",help="FILTER. Test author")
  parser.add_option("-s","--source",help="directory with tests to process, default is current directory",default=os.getcwd())
  parser.add_option("-c","--copy",metavar="DIR",help="Copy tests to specified directory")
  parser.add_option("-i","--info",default="IVPF", help="print information about test. F=file, I=id, V=version, P=platform, T=title")

  options, args = parser.parse_args()

  main()
