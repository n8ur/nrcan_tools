#!/usr/bin/env -S python3 -u

#################################################
# ppp_runner.py v.20221209.1
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
# Parent program to manage files on receiver to NrCan PPP results
#
# Usage: ppp_runner.py measurement_path, rx_type, \
#    fqdn, station, user, zip, cleanup, year, doy

import sys
import subprocess
import time
import argparse
from ftplib import FTP
from datetime import datetime, date, timedelta
from pathlib import Path

from nrcan_tools import *
from get_gps_ftp import *
from get_gps_ppp import *
from make_phase_from_clk import *
from make_pos_file import *
from make_weekly_rinex import *

def options_ppp_runner():
    parser = argparse.ArgumentParser()

    parser.add_argument('-m','--measurement_path',
        type=str,required=True,
        help="Measurement path")
    parser.add_argument('-r','--rx_type',
        type=str,required=True,
        help="GPS Receiver type (mosaic || netrs)")
    parser.add_argument('-f','--fqdn',
        type=str,required=True,
        help="FQDN of receiver")
    parser.add_argument('-s','--station',
        type=str,required=True,
        help="Receiver station name")
    parser.add_argument('-e','--email',
        type=str,required=True,
        help="User email address for NRCan")
    parser.add_argument('-z','--zip',
        action='store_true',
        help="Make daily and weekly zip files")
    parser.add_argument('-c','--cleanup',
        action='store_true',
        help="Remove files after zipping")
    parser.add_argument('-y','--year',
        type=int,required=False,default=0,
        help="Year to process")
    parser.add_argument('-d','--day_of_year',
        type=int,required=False,default=0,
        help="Day of year to process")

    args = parser.parse_args()
    return args

##########################################################
def ppp_runner(measurement_path, rx_type, \
    fqdn, station, user, zip, cleanup, year, doy):


    os.umask(0o002)     # o-w

    # default is to process yesterday's files
    if (year == 0) and (doy == 0):
        print("processing yesterday")
        print("year,day of year",year, doy)
        m = MeasurementFiles(measurement_path, "yesterday")
    else:
        m = MeasurementFiles(measurement_path, year, doy)

    print("ppp_runner.py:")
    print("measurement_path:",measurement_path)
    print("gps week and day to process:",m.gps_week_num,m.gps_dow_str)

    get_gps_ftp(measurement_path, rx_type, fqdn, station,year,doy)
    
    files_this_week = m.get_num_files(m.daily_dnld_dir)

    # Do weekly stuff on Thursday (GPS week day 4)
    # because that should get us the latest final
    # corrections (about 17 days after the end of
    # the GPS week)
    if m.gps_dow_num == 4:
        print("Making weekly RINEX file for gps week",m.gps_week_str)
        make_weekly_rinex(m.m_path, m.gps_week_num, zip, cleanup)

        # upload all the files in the weekly/ directory to NRCan for
        # processing.  This includes the one we just made, as well
        # as any remaining in the directory because we haven't yet
        # gotten final corrections for them.  Once we get finals, the
        # file is moved to weekly/final so it won't be processed again

        rinex_path = m.m_path + "/weekly/*.obs.zip"
        try:
            get_gps_ppp(rinex_path, measurement_path, user)
        except Exception as e:
            print("Couldn't do NRCan processing. Exiting...")
            print("Error:",e)

##########################################################
if __name__ == '__main__':
    args = options_ppp_runner()
    ppp_runner(args.measurement_path,args.rx_type,args.fqdn,
        args.station,args.email,args.zip,args.cleanup,
        args.year,args.day_of_year)

