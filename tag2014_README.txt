tag2014.py README

tag2014.py is a Python script that correlates CSV data from independent sources
with the iteration and benchmark phase of a SPEC SFS(tm) 2014 benchmark run. The
motivation is to assist with manual and automated statistical analysis of
performance data from various components of the Solution Under Test.

Prerequisites:
- Python 3
- python-dateutil (see http://dateutil.readthedocs.org/)

Original Author:
- Nick Principe, EMC Corporation <nick.principe@emc.com>

Additional Authors:
- Nick Principe, Individual <nick@princi.pe>

Version: 1.5
Version History:
    1.0 - Initial release
    1.1 - Added ability to specify one or more fields that contain timestamp info
          as parameters
        - Implemented auto-detection of timestamp fields and separate date and
          time stamp fields
        - Renumbered phases so that PRE is 1 instead of 6, other phases shifted
          appropriately
    1.2 - Added ability to only print WARMUP, RUN, and/or RUN_TAIL phases
    1.3 - Enhanced auto timestamp search regex to support some more common 
          power probe, environmental probe, and sflow collector formats
    1.4 - Added an optional comma after the date in search pattern for combined
          datetime field to cover a particularly interesting edge case
    1.5 - Added -s support for sflowtool data that includes an ISO 8601-ish
          timestamp as I have proposed in github.com/sflow/sflowtool/pull/16
        - The fork branch for this PR can be downloaded/cloned from:
          github.com/powernap/sflowtool/tree/csv-timestamp/
        - In -s mode, appropriate sflow columns are converted to rates
        - Note that in -s mode, only CNTR data is processed. FLOW data is discarded
        - Added -e mode to combine RUN and RUN_TAIL phases into a single RUN phase

USAGE: tag2014.py {-a|-c|-s} [-f ts_col ... ] [-m] [-r] [-n] [-e] -i in_file -l sfslog -o out_file [-t time_shift]
     -a : Analyzer data (CSV data produced by Unisphere Analyzer)
     -c : CSV data
     -s : Sflowtool data

     -f ts_col : field(s) that contains timestamp information

     -m : restrict output, include WARMUP data
     -r : restrict output, include RUN data
     -n : restrict output, include RUN_TAIL data

     -e : combine RUN and RUN_TAIL into RUN

     -i in_file  : input data file
     -l sfslog   : sfslog file
     -o out_file : output file, omit for STDOUT

     -t time_shift : shift the time in the data file by time_shift seconds

Helpful hints:
- All components in the Solution Under Test should have their times synced
- For when the times cannot be, or were not, synced, use the -t option
- This script is only useful with data logged in conjunction with a SPEC SFS(tm)
  2014 benchmark run. For more info about SPEC SFS(tm) 2014, see
  http://www.spec.org/sfs2014/

Notes:
- As of version 1.5, the -s support could use some more testing. Please report
  any issues to Nick Principe at nick@princi.pe or via github at 
  https://github.com/powernap/tag2014

License:
This script is licensed under the terms of the ISC license.
See the source code for full Copyright and License terms.
