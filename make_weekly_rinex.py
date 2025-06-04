#!/usr/bin/env -S python3 -u

#################################################
# make_weekly_rinex.py v.20221209.1
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

import os
import sys
import subprocess
from ftplib import FTP
from datetime import datetime, date, timedelta
import glob
import shutil
import zipfile
import argparse

from nrcan_tools import *

def options_make_weekly_rinex():
    parser = argparse.ArgumentParser()

    parser.add_argument('-m','--measurement_path',
        type=str,required=True,
        help="Measurement path")
    parser.add_argument('-z','--make_zip',
        action='store_true',
        help="Make daily and weekly zip files")
    parser.add_argument('-c','--cleanup',
        action='store_true',
        help="Remove files after zipping")
    parser.add_argument('-g','--gps_week',
        type=int,required=False,default=0,
        help="GPS week to process")
    parser.add_argument('-l','--last_gps_week',
        type=int,required=False,default=-999,
        help="Last GPS week to process")

    parser.add_argument('-a','--all_gps_weeks',
        action='store_true',
        help="Process all unprocessed weeks")

    args = parser.parse_args()
    return args


def make_weekly_rinex(measurement_path, gps_week, zip, cleanup):
    print("make_weekly_rinex.py:")

    os.umask(0o002)     # o-w
    m = MeasurementFiles(measurement_path,int(gps_week),0)

    files = glob.glob(m.daily_dnld_dir + '/*', recursive = False)
    # glob doesn't sort files, so do that
    files.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
    if len(files) < 7:
        print("Incomplete week -- {} files; skipping".format(len(files)))
        return

    # now run teqc to concatenate the daily files
    with open(m.weekly_rinex_path,'w') as f:
        args = ['/usr/local/bin/teqc', '+C2', '-R'] + files
        try:
            subprocess.run(args, stdout = f, stderr=subprocess.DEVNULL)
            #subprocess.run(args, stdout = f)
        except Exception as e:
            print("Couldn't run teqc, error:",e)
            sys.exit()
        print("Made weekly RINEX file", m.weekly_rinex_file)

#    if zip == True:
    if True:        # always make zip
        # zip the weekly combined file
        try:
            with zipfile.ZipFile(m.weekly_rinex_zip_path,mode='w', \
                    compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(m.weekly_rinex_path, m.weekly_rinex_file)
            zf.close()
            print("Zipped weekly RINEX file:", m.weekly_rinex_zip)
        except Exception as e:
            print("Couldn't make weekly zip:",e)
            sys.exit()

        # zip up the daily files
        m.make_daily_zip_name()
        try:
            with zipfile.ZipFile(m.daily_dnld_zip_path,mode='w', \
                    compression=zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    zf.write(f, os.path.basename(f))
                zf.close()
            print("Zipped daily RINEX directory:", \
                m.daily_dnld_zip)
        except Exception as e:
            print("Couldn't make daily zip:",e)
            sys.exit()
    # for now, always remove the .obs after making .zip
    try:
        os.remove(m.weekly_rinex_path)
        print("Removed file", m.weekly_rinex_file, "after zipping")
    except:
        print("Couldn't remove", m.weekly_rinex_file)
    # delete daily dir after zipping
    if cleanup == True:
        try:
            shutil.rmtree(m.daily_dnld_dir)
            print("Removed",m.daily_dnld_dir,"after zipping")
        except:
            print("Couldn't remove directory", m.daily_dnld_dir)
    return
if __name__ == '__main__':
    args = options_make_weekly_rinex()
    # measurement_path, gps_week, make-zip, cleanup, [end_gps_week]
    if args.all_gps_weeks == True:
        last_week = find_last_weekly_rinex(args.measurement_path)
        this_week = find_this_gps_week()
        # loop from last_gps_week to to current gps_week
        if last_week == 0:
            last_week = 2190    # beginning of 2022
            print("No weeklys found, so starting with",last_week)
        for x in range(last_week,this_week):
            make_weekly_rinex(args.measurement_path, x, \
            args.make_zip, args.cleanup)
    elif args.last_gps_week < 0:   # just process one week
        make_weekly_rinex(args.measurement_path, args.gps_week, \
            args.make_zip, args.cleanup)
    else:
        # loop from last_gps_week to to current gps_week
        for x in range(args.gps_last_gps_week,args.gps_week):
            make_weekly_rinex(args.measurement_path, x, \
            make_zip, cleanup)
