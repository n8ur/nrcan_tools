#!/bin/env -S python3 -u

#################################################
# make_gps_misc.py v.20250604.1
# copyright 2025 John Ackermann N8UR jra@febo.com
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
# reads directory of NRCan .sum summary files, extracts position
# and clock offset data, and appends to position and offset files
# in the "misc" directory of the measurement path
# Usage: make_gps_misc input_file_path measurement_path
#
# --    'input_file_path' is absolute path of input .sum file(s),
#       wildcards allowed
# --    'measurement_path" is where dirs for final, rapid,
#        ultra will go, with the output files placed appropriately

import os
import sys
import time
import argparse
import datetime
import shutil
import zipfile
import errno
import webbrowser
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from datetime import datetime, date,timedelta
from nrcan_tools import *

def make_gps_misc(sum_file, measurement_path):
    # first, read the summary file
    with open(sum_file,'r') as f:
        ecef = [0,0,0]
        llh = [0,0,0]
        while True:
            line = f.readline()
            if not line:
                break
            if line.startswith('SP3'):
                corr_type = line[:line.index("_")][-3:].strip()
            if line.startswith('NOW'):
                report_date = line[4:].strip()
            if line.startswith('BEG'):
                (data_begin,frac) = line[4:].strip().rsplit('.',1)
            if line.startswith('END'):
                (data_end,frac) = line[4:].strip().rsplit('.',1)
            if line.startswith('INT'):
                data_interval = line[4:].strip()
            if line.startswith('POS   X'):
                ecef[0] = line[49:][:13].strip()
            if line.startswith('POS   Y'):
                ecef[1] = line[49:][:13].strip()
            if line.startswith('POS   Z'):
                ecef[2] = line[49:][:13].strip()
            if line.startswith('POS LAT'):
                llh[0] = line[47:][:16].strip()
            if line.startswith('POS LON'):
                llh[1] = line[47:][:16].strip()
            if line.startswith('POS HGT'):
                llh[2] = line[47:][:16].strip()
            # get clock offset from .sum file:
            # OFF -277.3000 0.1666 ns
            if line.startswith('OFF'):
                (junk,offset1,offset2,scale) = line.split()
        f.close()

    # create the measurement path
    # from the summary file path
    (useful,junk) = sum_file.split('__')
    parts = useful.split('/')
    for count,val in enumerate(parts):
        if val.lower() in ('final','rapid','ultra'):
            measurement_path = '/'.join(parts[:count])
            break

    # get the proper file names
    # date_1, date_2, curr_leapsecond are placeholders
    # as we don't care about specific dates here
    m = MeasurementFiles(measurement_path, 2022,22)
    if corr_type == 'FIN':
        corr_type_string = 'final'
        pos_file = m.pos_file_final
        pos_path = m.pos_path_final
        offset_file = m.offset_file_final
        offset_path = m.offset_path_final

    elif corr_type == 'RAP':
        corr_type_string = 'rapid'
        pos_file = m.pos_file_rapid
        pos_path = m.pos_path_rapid
        offset_file = m.offset_file_rapid
        offset_path = m.offset_path_rapid
    elif corr_type == 'ULT':
        corr_type_string = 'ultra'
        pos_file = m.pos_file_ultra
        pos_path = m.pos_path_ultra
        offset_file = m.offset_file_ultra
        offset_path = m.offset_path_ultra

    print("Adding position data to", pos_file)
    print("Adding offset data to", offset_file)

    os.umask(0o002)     # o-w

    t = time.mktime(datetime.strptime(data_end, \
        "%Y-%m-%d %H:%M:%S").timetuple())
    (timestamp,frac) = str(t).rsplit('.') # get rid of '.0'
    iso_timestamp = datetime.utcfromtimestamp(t).isoformat()

    pos_line = str(timestamp) + ' ' + iso_timestamp + ' ' + \
        ecef[0] + ' ' + ecef[1] + ' ' + ecef[2] + ' ' + \
        llh[0].replace(' ','_')  + ' ' + llh[1].replace(' ','_') + \
        ' ' + llh[2].replace(' ','_') + '\n'
    offset_line = str(timestamp) + ' ' + iso_timestamp + ' ' + \
        offset1 + ' ' + offset2 + ' ' + scale + '\n'


    # now make/append files

    # do they exist?
    if not os.path.exists(pos_path):
        os.mknod(pos_path)
    if not os.path.exists(offset_path):
        os.mknod(offset_path)

################### pos file ##########################
    # now read pos file to see what it has
    with open(pos_path,'r') as f:
        new_pos_file = True
        have_header = False
        last_pos_time = 0
        while True:
            line = f.readline()
            if not line:
                break
            new_pos_file = False       # else we wouldn't be here
            if line.startswith('#'):
                have_header = True      # octothorpe means header
            else:
                last_pos_time = int(line.split()[0])

        f.close()

    if int(timestamp) < last_pos_time:
        print("Later data already in position file.  Exiting...")
        return

    with open(pos_path,'a') as f:
        # create the file header if necessary
        if not have_header:
            buf = '# NRCan PPP pos data (ITRF) for: '
            f.write(buf)
            buf = m.m_name + '\n'
            f.write(buf)
            buf = '# with ' + corr_type_string + \
                ' corrections (file created ' + \
                str(datetime.utcnow().isoformat(timespec='seconds')) + \
                ' UTC)\n'
            f.write(buf)
            buf = \
                "# fields: unix epoch, iso_8601, ecef(x), ecef(y) " + \
                  "ecef(z), lat, lon, height\n"
            f.write(buf)

        f.write(pos_line)
        f.close

################### offset file ##########################
    # now read offset file to see what it has
    with open(offset_path,'r') as f:
        new_offset_file = True
        have_header = False
        last_offset_time = 0
        while True:
            line = f.readline()
            if not line:
                break
            new_offset_file = False       # else we wouldn't be here
            if line.startswith('#'):
                have_header = True      # octothorpe means header
            else:
                last_offset_time = int(line.split()[0])

        f.close()

    if int(timestamp) < last_offset_time:
        print("Later data already in offset file.  Exiting...")
        return

    with open(offset_path,'a') as f:
        # create the file header if necessary
        if not have_header:
            buf = '# NRCan PPP offset data for: '
            f.write(buf)
            buf = m.m_name + '\n'
            f.write(buf)
            buf = '# with ' + corr_type_string + \
                ' corrections (file created ' + \
                str(datetime.utcnow().isoformat(timespec='seconds')) + \
                ' UTC)\n'
            f.write(buf)
            buf = \
                "# fields: unix epoch, iso_8601, offset1, offset2, scale \n"
            f.write(buf)

        f.write(offset_line)
        f.close

    return

if __name__ == '__main__':
    make_gps_misc(sys.argv[1],sys.argv[2])
