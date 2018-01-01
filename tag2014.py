#!/usr/bin/env python3
# Copyright (c) 2015, EMC Corporation
# Copyright (c) 2017, Standard Performance Evaluation Corporation
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
# ------------------------------------------------------------------------------
# Original Author: Nick Principe, EMC Corporation <nick.principe@emc.com>
# Additional Authors: Nick Principe, Individual <nick@princi.pe>
# Version 1.4
# ------------------------------------------------------------------------------
# Version History:
# ----------------
# 1.0 - Initial release
# 1.1 - Added ability to specify one or more fields that contain timestamp info
#       as parameters
#     - Implemented auto-detection of timestamp fields and separate date and
#       time stamp fields
#     - Renumbered phases so that PRE is 1 instead of 6, other phases shifted
#       appropriately
# 1.2 - Added ability to only print WARMUP, RUN, and/or RUN_TAIL phases
# 1.3 - Enhanced auto timestamp search regex to support some more common power 
#       probe, environmental probe, and sflow collector formats
# 1.4 - Added an optional comma to full timestamp detection field for a
#       particularly interesting edge case

import getopt
import sys
import os.path
import csv
import re
import io
from datetime import *
from dateutil import parser
from dateutil.relativedelta import *

PHASE_LABELS = ['00_PRE_TEST',
                '01_PRE',
                '02_INIT',
                '03_WARMUP',
                '04_RUN',
                '05_RUN_TAIL',
                '06_POST',
                ]


def usage():
    print(
        "USAGE: tag2014.py {-a|-c} [-f ts_col ... ] [-m] [-r] [-n] -i in_file -l sfslog "
        "-o out_file [-t time_shift]")
    print("     -a : Analyzer data (CSV data produced by Unisphere Analyzer)")
    print("     -c : CSV data")
    print()
    print("     -f ts_col : field(s) that contains timestamp information")
    print()
    print("     -m : restrict output, include WARMUP data")
    print("     -r : restrict output, include RUN data")
    print("     -n : restrict output, include RUN_TAIL data")
    print()
    print("     -i in_file  : input data file")
    print("     -l sfslog   : sfslog file")
    print("     -o out_file : output file, omit for STDOUT")
    print()
    print("     -t time_shift : shift the time in the data file by time_shift seconds")


def tagData(rd, wr):
    reFullTimestamp = re.compile(
        '^\s*\d{1,4}[/\-.]\d{1,4}[/\-.]\d{1,4},?\s+\d{1,2}[:.]\d{1,2}([:.]\d{1,2})?\s*([AP]M)?(.+)$')
    reDatestamp = re.compile('^\s*\d{1,4}[/\-.]\d{1,4}[/\-.]\d{1,4}(.+)$')
    reTimestamp = re.compile(
        '^\s*\d{1,2}[:.]\d{1,2}[:.]\d{1,2}\s*([AP]M)?(.+)$')
    datestampsFound = 0
    timestampsFound = 0
    foundFullTimestamp = 0
    # handle the header
    header = next(rd)
    header.insert(0, "Phase")
    header.insert(0, "Run")
    wr.writerow(header)
    # index of current phase...
    phaseIdx = 0
    # keep track of current object for analyzer data, so we know
    # when to start over run numbering, since we reached a new object
    curobj = None
    for row in rd:
        ts = None
        if (fileType == "c" and len(tsCols) == 0):
            # we need to find the ts column(s)
            for i in range(0, len(row)):
                if reFullTimestamp.match(row[i]):
                    tsCols.append(i)
                    print("Discovered a timestamp field at index {0}".format(
                        i), file=sys.stderr)
                    foundFullTimestamp = 1
                    break  # only discover one full timestamp
                elif datestampsFound == 0 and reDatestamp.match(row[i]):
                    tsCols.append(i)
                    print(
                        "Discovered a date-only timestamp field at index {0}".format(i), file=sys.stderr)
                    datestampsFound += 1
                elif timestampsFound == 0 and reTimestamp.match(row[i]):
                    tsCols.append(i)
                    print(
                        "Discovered a time-only timestamp field at index {0}".format(i), file=sys.stderr)
                    timestampsFound += 1
        if ((foundFullTimestamp == 0) and
                (not (timestampsFound == 1 and datestampsFound == 1))):
            timestampsFound = 0
            datestampsFound = 0
            del tsCols[:]
            print("Couldn't find a full timestamp, skipping row...",
                    file=sys.stderr)
        try:
            if fileType == "a":
                if curobj == None:
                    curobj = row[ana_obj_col]
                else:
                    if curobj != row[ana_obj_col]:
                        phaseIdx = 0
                        curobj = row[ana_obj_col]
                ts = parser.parse(row[ana_ts_col])
            elif fileType == "c":
                timestampText = ""
                for field in tsCols:
                    timestampText += row[field]
                    timestampText += " "
                ts = parser.parse(timestampText)
            else:
                assert False, "unhandled file type"
        except ValueError:
            continue  # skip where there is an invalid timestamp
        except TypeError:
            continue  # skip... but this is indicative of bad data format

        # This is where we hack time like Kung Fury
        if timeShift != None:
            ts += timeShift

        iter_run = -1
        iter_phase = "error"
        # Now we have the current timestamp of the data.
        # Sync to the start (skip phases that aren't in the data)
        while ((phaseIdx < (len(times) - 1)) and
               (ts > times[phaseIdx + 1])):
            phaseIdx += 1
        # The end will run on, but it will be tagged as POST for runs
        # that finish normally

        # Pull the run number and labels for each phase from the arrays
        iter_run = runNum[phaseIdx]
        iter_phase = labels[phaseIdx]

        # Add the tag info
        row.insert(0, iter_phase)
        row.insert(0, iter_run)

        # Write out the line
        if restrictedOutput:
            if printWarmup and iter_phase == PHASE_LABELS[3]:
                wr.writerow(row)
            if printRun and iter_phase == PHASE_LABELS[4]:
                wr.writerow(row)
            if printRunTail and iter_phase == PHASE_LABELS[5]:
                wr.writerow(row)
        else:
            wr.writerow(row)

# Globals
dataFile = None
sfslogFile = None
outputFile = None
fileType = None
timeShift = None
# analyzer columns
ana_ts_col = 1
ana_obj_col = 0
restrictedOutput = False
printWarmup = False
printRun = False
printRunTail = False

tsCols = list()

labels = list()
runNum = list()
times = list()

# Getopt and argument parsing
try:
    opts, args = getopt.getopt(sys.argv[1:], "acf:i:l:o:t:wrn")
except getopt.GetoptError as err:
    print(err)
    usage()
    sys.exit(2)

for o, a in opts:
    if o == "-a":
        if fileType:
            print("Can only specify one file format type")
            usage()
            sys.exit(2)
        else:
            fileType = "a"
    elif o == "-c":
        if fileType:
            print("Can only specify one file format type")
            usage()
            sys.exit(2)
        else:
            fileType = "c"
    elif o == "-i":
        if os.path.isfile(a):
            dataFile = a
        else:
            print('Input file "%s" does not exist' % a)
            sys.exit(2)
    elif o == "-l":
        if os.path.isfile(a):
            sfslogFile = a
        else:
            print('sfslog file "%s" does not exist' % a)
            sys.exit(2)
    elif o == "-f":
        try:
            tsCols.append(int(a))
        except ValueError as err:
            print("Unable to parse timestamp field string: ", err)
            sys.exit(3)
    elif o == "-o":
        outputFile = a
    elif o == "-t":
        timeShift = a
    elif o == "-w":
        restrictedOutput = True
        printWarmup = True
    elif o == "-r":
        restrictedOutput = True
        printRun = True
    elif o == "-n":
        restrictedOutput = True
        printRunTail = True
    else:
        assert False, "unhandled option"

if dataFile == None:
    print("Must specify an input file")
    usage()
    sys.exit(2)
if sfslogFile == None:
    print("Must specify an sfslog file")
    usage()
    sys.exit(2)
if fileType == None:
    print("Must specify a file type (-a or -c)")
    usage()
    sys.exit(2)
if timeShift != None:
    try:
        newts = relativedelta(seconds=int(timeShift))
        timeShift = newts
    except ValueError as err:
        print("Unable to parse time shift string: ", err)
        sys.exit(3)

# If we got this far, we might as well compile matching RegEx
# for sfslog parsing
rePreToInit = re.compile('^\s*Waiting to finish initialization\. (.+)$')
reInitToWarmup = re.compile('^\s*(.+) Starting WARM phase.*$')
reWarmupToRun = re.compile('^\s*(.+) Starting RUN phase.*$')
reRunToRunTail = re.compile('^\s*(.+) Run 90 percent complete.*$')
reRunTailToPost = re.compile('^\s*Tests finished: (.+)$')
rePostToPre = re.compile('^<<< (.+): Starting.*$')

# initialize the run label and run number lists with values
labels.append(PHASE_LABELS[0])  # 00_PRE_TEST
runNum.append(0)

# parse the sfslog to extract transition timestamps
with open(sfslogFile, mode="r", newline='') as sfslog:
    lastline = ""
    lasttime = ""
    run = 0
    for logline in sfslog:
        lastline = logline
        linematch = rePreToInit.match(logline)
        if linematch:
            try:
                date = parser.parse(linematch.group(1))
                times.append(date)
                labels.append(PHASE_LABELS[2])  # 02_INIT
                runNum.append(run)
            except ValueError:
                print('Bad date: %s' % linematch.group(1))
        linematch = reInitToWarmup.match(logline)
        if linematch:
            try:
                date = parser.parse(linematch.group(1))
                times.append(date)
                labels.append(PHASE_LABELS[3])  # 03_WARMUP
                runNum.append(run)
            except ValueError:
                print('Bad date: %s' % linematch.group(1))
        linematch = reWarmupToRun.match(logline)
        if linematch:
            try:
                date = parser.parse(linematch.group(1))
                times.append(date)
                labels.append(PHASE_LABELS[4])  # 04_RUN
                runNum.append(run)
            except ValueError:
                print('Bad date: %s' % linematch.group(1))
        linematch = reRunToRunTail.match(logline)
        if linematch:
            try:
                date = parser.parse(linematch.group(1))
                times.append(date)
                labels.append(PHASE_LABELS[5])  # 05_RUN_TAIL
                runNum.append(run)
            except ValueError:
                print('Bad date: %s' % linematch.group(1))
        linematch = reRunTailToPost.match(logline)
        if linematch:
            try:
                date = parser.parse(linematch.group(1))
                times.append(date)
                labels.append(PHASE_LABELS[6])  # 06_POST
                runNum.append(run)
            except ValueError:
                print('Bad date: %s' % linematch.group(1))
        linematch = rePostToPre.match(logline)
        if linematch:
            try:
                date = parser.parse(linematch.group(1))
                run += 1  # increment run number
                times.append(date)
                labels.append(PHASE_LABELS[1])  # 01_PRE
                runNum.append(run)
            except ValueError:
                print('Bad date: %s' % linematch.group(1))

# duplicate the first time value to satisfy the tagging algorithm
times.insert(0, times[0])

# setup for and commence tagging the data
if (outputFile == None):
    # we're writing to STDOUT so no need to open the output
    with open(dataFile, mode="r", newline='') as infile:
        rdr = None
        wrt = None
        if (fileType == "a") or (fileType == "c"):
            rdr = csv.reader(infile, delimiter=',', quotechar='"')
        assert rdr != None, "Unhandled file type"
        wrt = csv.writer(sys.stdout, delimiter=',',
                         quotechar='"', quoting=csv.QUOTE_MINIMAL)
        assert wrt != None, "Error opening csv writer"
        tagData(rdr, wrt)
else:
    # we're writing to a file, so we open both files in a single with
    with open(dataFile, mode="r", newline='') as infile, \
            open(outputFile, mode="w", newline='') as outfile:
        rdr = None
        wrt = None
        if (fileType == "a") or (fileType == "c"):
            rdr = csv.reader(infile, delimiter=',', quotechar='"')
        assert rdr != None, "Unhandled file type"
        wrt = csv.writer(outfile, delimiter=',', quotechar='"',
                         quoting=csv.QUOTE_MINIMAL)
        assert wrt != None, "Error opening csv writer"
        tagData(rdr, wrt)
