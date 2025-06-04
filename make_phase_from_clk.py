#!/usr/bin/env python3
#####################################################################
# make_phase_from_clk.py v.20220815.1
# copyright 2022 John Ackermann N8UR jra@febo.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# Takes '.clk' clock data files processed by the NRCan CSRS
# Precise Point Positioning service* and creates file with
# clock offset (phase) data and timetags.
#
# Usage: make_phase.py infile outfile [first_doy]
#
# -- infile is the .clk file or files to be processed.  It
#    can be a directory with wildcards, or a single file name
#
# -- outfile is the file in which the combined phase data
#    will be returned
#
# -- first_doy is optional.  If specified, will skip processing
#    until specified day of year is encountered.
#
#####################################################################
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
import glob
import os
import random
import shutil
import subprocess
import sys
from tempfile import NamedTemporaryFile
import zipfile

from nrcan_tools import *

# return day of year as string from .clk AR line
def make_doy_from_clk(instring):
    dt = make_dt_from_clk(instring)
    return make_doy_from_dt(dt)

# return dt of first epoch
def get_first_epoch_from_clk(files):
    global first_epoch
    first_epoch= datetime.min
    with open(files[0],'r') as f:
        count = 0
        for line in f:
            line = f.readline()
            if line.startswith('AR'):
                if count == 0:
                    first_epoch = make_dt_from_clk(line)
                    break
        return first_epoch

# return dt of last epoch
def get_final_epoch_from_clk(files):
    final_epoch = datetime.min
    with open(files[len(files)-1],'r') as f:
        for line in f:
            pass
    final_epoch = make_dt_from_clk(line)
    return final_epoch

# return total number of epochs
def get_epoch_count_from_clk(files):
    with open(files[0],'r') as f:
        count = 0
        for line in f:
            line = f.readline()
            if line.startswith('AR'):
                count = count + 1
        return count

# get tau from first two epochs in first file
def get_tau_from_clk(files):
    tau = 0
    start = datetime.min
    this_epoch = datetime.min
    count = 0
    # only need to look at the first file
    with open(files[0],'r') as f:
        for line in f:
            if line.startswith('AR'):
                if count == 0:
                    first_epoch = make_dt_from_clk(line)
                if count == 1:
                    this_epoch = make_dt_from_clk(line)
                    tau = get_delta_seconds(this_epoch,first_epoch)
                    break
                count += 1
    return tau

########################################################################
# read .clk files into a combined file with offset,
# iso_epoch, doy_str and return epoch count
def make_phase_file(infile,outfile):
    print("make_phase_from_clk.py:",infile,outfile)   # ID for log

    ##### set Test to False for normal operation
    Test = True

    ##### number of decimal places for offset values
    #     (hint: 12 = 1 picosecond
    places = 12

    # set mode of all created files to -rwxrwxr-xr
    os.umask(0o002) 

    first_epoch = datetime.min
    this_epoch = datetime.min
    this_epoch_iso = ""
    final_epoch = datetime.min
    count = 0
    header = []

    infile = os.path.abspath(infile)
    try:
        os.path.isfile(infile)
    except:
        print("Couldn't open",infile,"!")
        sys.exit()

    outfile = os.path.abspath(outfile)
    try:
        f = open(outfile,'w')
        f.close()
    except:
        print("Couldn't create",outfile,"!")
        sys.exit()

    try:
        tmpfile1 = NamedTemporaryFile(mode='w+t',delete=False)
    except:
        print("Couldnt' create tmpfile",tmpfile1.name,"!")
        sys.exit()

    with open(tmpfile1.name,'w') as outp:
        # get list of .clk files
        infile = os.path.abspath(infile)
        files = sorted( filter( os.path.isfile, glob.glob(infile) ) )
        for f in files: 
            with open(f,'r') as inp:
                for line in inp:
                    if line.startswith('#'):
                        continue
                    if not line.startswith('AR'):
                        continue
                    parts = line.split()
                    this_epoch_iso = make_iso_from_clk(line)
                    if not iso_valid(this_epoch_iso):
                        print("bad line:",line)
                        continue
                    this_epoch = make_dt_from_iso(this_epoch_iso)
                    this_epoch_doy = make_doy_from_dt(this_epoch)
                    offset = float(line.split()[9])
                    result = format_dec(offset,places) + " " + \
                        this_epoch_iso + " " + this_epoch_doy + "\n"
                    outp.write(result)
                    # capture first epoch
                    if count == 0:
                        first_epoch = make_dt_from_iso(this_epoch_iso)
                    count = count + 1
    outp.close

    # capture final epoch
    final_epoch = make_dt_from_iso(this_epoch_iso)
    duration = get_delta_seconds(final_epoch, first_epoch)
    tau = int(duration / count)
    should_be = int(duration / tau) + 1
    missing = should_be - count

    # add the basic info to the header list
    time_now = datetime.utcnow().isoformat('T','seconds') + " UTC"
    header.append("# --> make_phase_from_clk.py\n")
    header.append("# Output file: " + os.path.basename(outfile) + "\n")
    header.append("# Created " +  time_now + "\n")
    header.append("# Generated from " + \
        os.path.dirname(files[0]) + "/:\n")
    for f in files:
        header.append("#     " + os.path.basename(f) + '\n')
    header.append("# Start: " + make_iso_from_dt(first_epoch) + "\n")
    header.append("# End:   " + make_iso_from_dt(final_epoch) + "\n")
    header.append("# Tau: " + str(tau) + " seconds\n")
    header.append("# Duration: " + \
        make_DDHHMMSS_from_seconds(duration) + \
        " (" + str(duration) + " seconds)\n")
    header.append("# Wrote " + str(count) + " lines of data; there should\n")
    header.append("# be " + str(should_be) + " epochs, so " + \
        str(missing) + " epochs are missing\n")
    header.append('#\n')
    with open(outfile,'w') as outp:
        for lines in header:
            outp.write(lines)
        with open(tmpfile1.name) as inp:
                for lines in inp:
                    outp.write(lines)
    outp.close()
    tmpfile1.close()
    os.remove(tmpfile1.name)
    return count
    
if __name__ == '__main__':
    infile = sys.argv[1]     # can be path/wildcard, or single file
    outfile = sys.argv[2]
    make_phase_file(infile, outfile)
