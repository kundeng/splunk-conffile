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

# Map location parameter to filesystem path (relative to bin/ directory)
# bin/ is at $SPLUNK_HOME/etc/apps/<app>/bin/
LOCATION_MAP = {
    'deployment-apps': '../../../deployment-apps',
    'apps':            '../../',
    'master-apps':     '../../../master-apps',
    'system':          '../../../system',
    'etc':             '../../../',
}

if PATH not in LOCATION_MAP:
    splunk.Intersplunk.generateErrorResults(
        "Unknown location '%s'. Valid: %s" % (PATH, ', '.join(sorted(LOCATION_MAP))))
    sys.exit(1)

fspath = LOCATION_MAP[PATH]

matches = []
for root, dirnames, filenames in os.walk(fspath):
    for filename in fnmatch.filter(filenames, CONFFILE):
        matches.append(os.path.abspath(os.path.join(root, filename)))

logger.info("Found %d %s files in location=%s", len(matches), CONFFILE, PATH)

results = []

for match in matches:
    logger.info("Parsing %s", match)
    try:
        with open(match) as fp:
            config = ConfigParser()
            config.readfp(fp)
            logger.info("  %d stanzas in %s", len(config.sections()), match)
            for sec in config.sections():
                row = {}
                row["_time"] = os.path.getmtime(match)
                row["source"] = match
                row["stanza"] = sec

                # Extract app name from path (deployment-apps/<app>/... or apps/<app>/...)
                parts = match.replace('\\', '/').split('/')
                for i, p in enumerate(parts):
                    if p in ('deployment-apps', 'master-apps', 'apps', 'system'):
                        if i + 1 < len(parts):
                            row["app"] = parts[i + 1]
                        break

                # For serverclass.conf: extract serverClass and app from stanza name
                # e.g. [serverClass:Windows:app:TA-windows] → server_class=Windows, deploy_app=TA-windows
                if CONFFILE == 'serverclass.conf' and sec.startswith('serverClass:'):
                    sc_parts = sec.split(':')
                    if len(sc_parts) >= 2:
                        row["server_class"] = sc_parts[1]
                    if len(sc_parts) >= 4 and sc_parts[2] == 'app':
                        row["deploy_app"] = sc_parts[3]

                for key, value in config.items(sec):
                    row[key] = value

                results.append(row)
    except Exception as e:
        import traceback
        stack = traceback.format_exc()
        logger.error("Error parsing %s: %s\n%s", match, e, stack)

logger.info("Total results: %d", len(results))
splunk.Intersplunk.outputResults(results)
