#!/usr/bin/python
# encoding: utf-8

from __future__ import print_function
import fnmatch
import os
import splunk.Intersplunk
import sys
from io import open
import csv
#from six.moves.configparser import ConfigParser
import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s %(message)s',
    filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','inputconf.log'),
    filemode='a')
from tabconfigparser import TABConfigParser as ConfigParser


"""
specify the pattern for the .conf files to gather
"""
try:
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
    CONFFILE = options.get('conffile','inputs.conf')
    PATH = options.get('location','deployment-apps')
except Exception as e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))

if PATH == 'deployment-apps':
    fspath = '../../../deployment-apps'
if PATH == 'apps':
    fspath = '../../'
if PATH == 'master-apps':
    fspath = '../../../master-apps'

matches = []
for root, dirnames, filenames in os.walk(fspath):
#for root, dirnames, filenames in os.walk('/opt/splunk/etc/deployment-apps/FA-sonarqube/default'):
    for filename in fnmatch.filter(filenames, CONFFILE):
        matches.append(os.path.abspath(os.path.join(root, filename)))

#print matches
print("we have " + str(len(matches)) + " conf files to loop over", file=sys.stderr)

ini = ConfigParser()


#Find all keys in the INI file to build a row template and
#include a "section" field to store the section name.
rowTemplate = {"section":""}

results = []

for match in matches:
    print("handle " + match + " ...", file=sys.stderr)
    try:
        #for each .conf file
        with open(match) as fp:
            config = ConfigParser()
            config.readfp(fp)
            #for each stanza
            print("  we have " + str(len(config.sections())) + " stanzas to loop over", file=sys.stderr)
            for sec in config.sections():
                print("    handle stanza " + sec + " in " + match, file=sys.stderr)
                row = {}
                # for each key=value
                row["_time"] = os.path.getmtime(match)  #modification timestamp
                for key,value in config.items(sec):
                    print("        key " + key + " and value " + value + " in " + match, file=sys.stderr)
                    tmp_key = key
                    tmp_value = value
                    row[tmp_key] = tmp_value
                    row["source"] = match
                    row["stanza"] = sec
                results.append(row)
                print("      row " + str(row), file=sys.stderr)
    except Exception as e:
        #results.append( {"source":match,"status":"error"}
        #pass
        #"""
        import traceback
        stack =  traceback.format_exc()
        #splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
        print("Error : Traceback: '%s'. %s" % (e, stack), file=sys.stderr)
        logger.error("Error : Traceback: '%s'. %s" % (e, stack))
        #"""

print(results, file=sys.stderr)
splunk.Intersplunk.outputResults( results )
