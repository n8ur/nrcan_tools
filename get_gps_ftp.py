#! /usr/bin/env -S python3 -u

############################################################
# get_gps.ftp.py v.20250604.1
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

import os
import sys
import subprocess
import tempfile
import argparse
import datetime as dt
from ftplib import FTP
from ftplib import all_errors as ftp_errors
from gnsscal import *       # pip3 install gnsscal

# functions are included here
from nrcan_tools import *

def options_get_gps_ftp():
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
    parser.add_argument('-y','--year',
        type=int,required=False,default=0,
        help="Year to process")
    parser.add_argument('-d','--day_of_year',
        type=int,required=False,default=0,
        help="Day of year to process")
    parser.add_argument('--start_doy',
        type=int,required=False,default=0,
        help="First day of year to process")
    parser.add_argument('--end_doy',
        type=int,required=False,default=0,
        help="End day of year to process")
    parser.add_argument('-a','--all_new',
        action='store_true',required=False,default=0,
        help="Download all new RINEX files")

    args = parser.parse_args()
    return args

def convert_T00(infile,outfile):
    tmpfile = tempfile.NamedTemporaryFile(suffix='.tgd',delete=False)
    # convert .T00 file into intermediate .tgd file
    args = ['/usr/local/bin/runpkr00', '-g', '-d', '-v',
        infile, tmpfile.name]
    try:
        subprocess.run(args, \
            stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
    except Exception as e:
        print("Couldn't run runpkr00, error:",e)
        return
    tmpfile.flush()
    tmpfile.seek(0)
   
    # convert tgd to RINEX
    with open(outfile,'w') as f:
        args = ['/usr/local/bin/teqc', '+C2', '-R', tmpfile.name]
        try:
            subprocess.run(args, stdout = f, stderr = subprocess.DEVNULL)
        except Exception as e:
            print("Couldn't run teqc, error:",e)
            return
    s = outfile.split('/')
    s = s[len(s)-2] + '/' + s[len(s)-1]
    size = os.path.getsize(outfile)
    tmpfile.close()
    os.unlink(tmpfile.name)
    return True

####################################################################
# main function
# rx_type = the rx type -- "mosaic" or "netrs"
# fqdn = FQDN of rx hostname
# station_ID = station name (used in GPS filenames)
# measurement_path is where files go

def get_gps_ftp(measurement_path, rx_type, fqdn, \
        station, year, doy):
    print("get_gps_ftp.py:")    # id for logging
    os.umask(0o002)        # o-w
    
    # first convert year and doy to gps week and dow

    m = MeasurementFiles(measurement_path, year, doy)

    print("Year, day of year, GPS week, GPS day of week:", \
        year, doy, m.gps_week_str, m.gps_dow_str)
    # don't try to download a future date!
    if m.gps_days_num > m.today_gps_days_num:
        print("Trying to download future day!")
        print("GPS week:",m.gps_week_str,"day of week:",m.gps_dow_str)
        print("Today is:",m.today_gps_week_str,m.today_gps_dow_str)
        sys.exit()

    # receiver-specific variables
    if rx_type == 'mosaic':
        gps_dirname = "DSK1/SSN/GRB0051/" + m.yy_str + m.doy_str + "/"
        gps_filename = station + m.doy_str + "0." + m.yy_str + "o"
        try:
            dnld_file = tempfile.NamedTemporaryFile(suffix='.obs',delete=False)
        except:
            print("Couldn't create tempfile.  Exiting!")
            return
    elif rx_type == 'netrs':
        gps_dirname =  m.yyyy_str + m.mm_str + "/"
        gps_filename = station + m.yyyy_str + m.mm_str + \
            m.dd_str + "0000a.T00"
        try:
            dnld_file = tempfile.NamedTemporaryFile(suffix='.T00',delete=False)
        except:
            print("Couldn't create tempfile.  Exiting!")
            return
    else:
        print("Invalid rx_type.  Specify 'mosaic' or 'netrs'")
        return

    # now get the file
    with FTP(fqdn, 'anonymous') as ftp:
        #print("getting ", gps_dirname, gps_filename,sep='')
        try:
            ftp.cwd(gps_dirname)
        except ftp_errors as e:
            print("Couldn't change remote directory:")
            print(e)
            return
        # we're downloading in binary mode whether ascii or .T00 format
        try:
            response = ftp.retrbinary('RETR ' + gps_filename, \
                dnld_file.write, 1024)
        except ftp_errors as e:
            print("Couldn't download:")
            print(e)
            return
        # rewind tmpfile
        dnld_file.seek(0)
        # Check the response code
        if response.startswith('226'):  # Transfer complete
            if rx_type != "mosaic":
                print("Downloaded",gps_filename)
        else:
            print("Transfer error. File may be incomplete or corrupt.")

    # was there any data downloaded?
    tmpsize = os.path.getsize(dnld_file.name)
    if tmpsize > 0:
        m.make_daily_dnld_dir()
        if rx_type == 'netrs':
            if convert_T00(dnld_file.name, m.daily_dnld_path) == True:
                print("Downloaded",gps_filename,"and converted to RINEX")
            else:
                print("Downloaded",gps_filename,
                    "but couldn't convert to RINEX!")
             
        elif rx_type == 'mosaic':
            print("Downloaded", gps_filename)
            shutil.copy(dnld_file.name,m.daily_dnld_path)
        s = m.daily_dnld_path.split('/')
        s = s[len(s)-2] + '/' + s[len(s)-1]
        size = os.path.getsize(m.daily_dnld_path)
        print("Saved as " + s + " (" + format_filesize(size) + ")")
    else:
        os.remove(dnld_file.name)
        print("Downloaded file was empty.  Exiting:")
        return

    os.remove(dnld_file.name)

    try:
        running_standalone
    except NameError:
        return

if __name__ == '__main__':
    running_standalone = True
    args = options_get_gps_ftp()

    # process all from day after last until today
    if args.all_new == True:
        print("Downloading all new RINEX files")
        # get the last day that's been downloaded
        last_week,last_dow,last_year,last_doy = \
            find_last_daily_rinex(args.measurement_path)
        # so we don't run into the future
        now = datetime.utcnow()
        today_doy = int(now.strftime('%j'))
        for x in range(last_doy + 1,today_doy):
            get_gps_ftp(args.measurement_path, args.rx_type, \
                args.fqdn, args.station, args.year, x)
            # don't go into the future
            if x > today_doy:
                break
    else:       # just get specified date
        if x > day_of_year:
            sys.exit()
        get_gps_ftp(args.measurement_path, args.rx_type, \
            args.fqdn, args.station, args.year, args.day_of_year)
    sys.exit()
