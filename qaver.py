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

def build_test_map(root_dir):
    test_map = dict()
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
                td = xml.dom.minidom.parse(testfile)
                fileroot = td.documentElement
                testid = get_test_attribute('test_id',fileroot.childNodes)
                version = get_test_attribute('target_version',fileroot.childNodes)
                if not test_map.has_key(testid):
                    test_map[testid] = dict()
                    test_map[testid][version] = testfile
                else:
                    test_map[testid][version] = testfile
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

# main program

def main():
    parser = OptionParser(version="%prog 1.0")
    parser.add_option("-v","--verbose",action="store_true", default=False,help="more verbose output")
    parser.add_option("-q","--quiet",action="store_true", default=False,help="do not list tests to stdout")
    parser.add_option("-t","--target",help="QA ID of target engine")
    parser.add_option("-s","--source",help="directory with tests to process, default is current directory",default=os.getcwd())
    parser.add_option("-c","--copy",metavar="DIR",help="Copy tests to specified directory")

    options, args = parser.parse_args()
    if options.target == None:
        parser.error("Target engine not specified")
        parser.print_help()
    else:
        if options.verbose and not options.quiet:
            print "QA Target :",options.target
            print "Source    :",os.path.abspath(options.source)
            if options.copy != None:
                print "Copy to   :",os.path.abspath(options.copy)
            print ""
        testmap = build_test_map(options.source)
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

if __name__ == "__main__":
    main()
