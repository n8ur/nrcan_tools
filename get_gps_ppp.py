#!/bin/env -S python3 -u

#################################################
# get_gps.ppp.py v.20250604.1
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
# Uploads 'weekly' RINEX files to NRCan PPP service and 
# processes results.
#
# Note that despite comment in the csrs_ppp_auto.py not
# listing .zip as an allowed file upload type, we can in fact
# upload zip files.
#
# Usage: get_gps_ppp.py input_file_path measurement_path email_addr
 
import os
import signal
import sys
import time
import shutil
import glob
import zipfile
import errno
import webbrowser
import requests
import tempfile
from requests_toolbelt.multipart.encoder import MultipartEncoder
from make_gps_misc import *
from nrcan_tools import *

def options_get_gps_ppp():
    parser = argparse.ArgumentParser()

    parser.add_argument('-m','--measurement_path',
        type=str,required=True,
        help="Measurement path")
    parser.add_argument('-i','--input_path',
        type=str,required=True,
        help="Path of input RINEX files")
    parser.add_argument('-e','--email',
        type=str,required=True,
        help="User email address for NRCan")

    args = parser.parse_args()
    return args

def handler(signum, frame):
    res = input("Ctrl-c was pressed. Do you really want to exit? y/n ")
    if res == 'y':
        exit(1)

def get_gps_ppp(input_file_path, measurement_path,user_name):
    print("get_gps_ppp:")
#    signal.signal(signal.SIGINT, handler)

    os.umask(0o002)    # o-w


    # some default upload parameters
    # that probably don't need to be changed
    lang = 'en'
    process_type = 'Static'
    ref = 'NAD83'
    nad83_epoch = 'CURR'
    vdatum = 'cgvd2013'
    email = 'dummy_email'
    output_pdf = 'lite'
    get_max = 1800
    ppp_access = 'nobrowser_status'  # default starting 2013-09-30

#    changes to CSRS domain; was
#    base_url = 'https://webapp.geod.nrcan.gc.ca/CSRS-PPP/service/results/'
#    post_url = 'https://webapp.geod.nrcan.gc.ca/CSRS-PPP/service/submit'
#    browser_name = 'CSRS-PPP access via Python Browser Emulator'
    domain = 'https://webapp.csrs-scrs.nrcan-rncan.gc.ca'
    url_to_post_to = '{0:s}/CSRS-PPP/service/submit'.format(domain)
    browser_name = 'CSRS-PPP access via Python Browser Emulator'
    
    error = 0
    sleepsec = 10
    num_files = 0

    # process input file path and measurement path

    input_file_path = os.path.abspath(input_file_path)
    if not os.path.isfile(input_file_path):
        print("Input file:",input_file_path,"not found! Exiting...")
        return

    input_file_name = os.path.basename(input_file_path)
    final_file_path = measurement_path + "/weekly/final/" + input_file_name

    measurement_base = input_file_name.split(os.extsep)[0]
    print("Measurement base name:",measurement_base)

    if not os.path.isdir(measurement_path):
        print("Measurement path:",measurement_path,"not found! Exiting...")
        sys.exit()
    measurement_path = os.path.abspath(measurement_path) + "/"
    print("Measurement path:",measurement_path)

    # note: date_1 and date_2 params are just placeholders
    # as we only care about directory names
    m = MeasurementFiles(measurement_path, 2020,22)

    try:
        m.make_output_dirs()
#        print("Made output dirs...")
    except Exception as e:
        print("Couldn't find/make output dirs",e,"!  Exiting...")
        sys.exit()

    try:
        tmp_dir = tempfile.mkdtemp() + '/'
#        print("Made tmpdir...")
    except Exception as e:
        print("Couldn't make temporary directory:",e)
        sys.exit()

###########################################################
# get status
    def get_status(tmp_dir,keyid):
        # get status
        r = requests.get('{0:s}/CSRS-PPP/service/results/status?id={1:s}"' \
            .format(domain, keyid), timeout=5)
        try:
            status = r.content.decode(encoding='utf-8', errors='strict')
        except UnicodeError:
            sys.exit('ERROR: Problem with status! Try again!')
        except Execption as e:
            print("Error getting status; exiting")
            print("Error:",e)
            sys.exit()

        if 'processing' in str(status).lower():
            procstat = 'processing'
            sleepmore = 1
        elif 'done' in str(status).lower():
            procstat = 'done'
            sleepmore = 0
        elif 'error' in str(status).lower():
            procstat = 'error'
            sleepmore = 1
        else:
            procstat = 'Unknown'
            print('*ERR*[{0:d}] ... log content follows ...'.format(get_num))
            print('{0:s}'.format(status))
            sleepmore = 1
        return procstat

###########################################################

# -------------------------------------------------
# Create the browser that will post the information
# -------------------------------------------------
    # The information to POST to the program
    content = {
        'return_email': email,
        'cmd_process_type': 'std',
        'ppp_access': ppp_access,
        'language': lang,
        'user_name': user_name,
        'process_type': process_type,
        'sysref': ref,
        'nad83_epoch': nad83_epoch,
        'v_datum': vdatum,
        'rfile_upload': (measurement_base, \
            open(input_file_path,'rb'),'text/plain'),
        'output_pdf': output_pdf
    }
    mtp_data = MultipartEncoder(fields=content)

    # Insert the browser name, if specified
    header = {'User-Agent': browser_name, \
        'Content-Type': mtp_data.content_type, 'Accept': 'text/plain'}

    # upload RINEX file and get transaction key
    keyid = None
    got_key = False
    while got_key == False:
        try:
            req = requests.post(url_to_post_to, data=mtp_data, \
                headers=header)
        except requests.exceptions.RequestException as e:
            print("Couldn't get key so exiting")
            print("Error:",e)
            raise SystemExit(e)

        keyid = str(req.text)  # The keyid required for the job
        if req.text:
            keyid = req.text
            if 'DOCTYPE' in keyid:
                print("keyid =",keyid)
                print('keyid has a weird value! [{0:s}]'. \
                    format(input_file_name))
            if keyid == 'ERROR [002]':
                print('NOTICE:\nTemporarily blocked from using CSRS-PPP')
                sys.exit()
            # key OKAY!
            got_key = True
            #print('keyid: {0:s}'.format(keyid))
            break
        else:
            print('=> NO results! An error occurred while processing!!!')
            print('=> RNX: {0:s} [keyid: {1:s}]'. \
                format(input_file_name, keyid))
            error = 1

    # wait for results
    get_num = 0
    status = ''
    print("Processing", input_file_name)
    while status != 'done' and error != 1:
        print('.',end='')
        status = get_status(tmp_dir,keyid)
        get_num += 1
        # Check get_max
        if get_num > get_max:
            print('=> Taking too long!')
            print('=> Next file ...')
            error = 1
            sys.exit(error)

        time.sleep(sleepsec)
    print(" (time: ~", get_num * 10,"seconds)")

    # Get full_output.zip
    
    tmp_zip_path = tmp_dir + measurement_base + '.zip'
    tmp_sum_path = tmp_dir + measurement_base + '.sum'
    tmp_clk_path = tmp_dir + measurement_base + '.clk'

    try:
        r = requests.get('{0:s}/CSRS-PPP/service/results/file?id={1:s}' \
            .format(domain, keyid), timeout=5)
    except requests.exceptions.RequestException as e:
        print("request error:",e,"so exiting!")
        raise SystemExit(e)

    with open(tmp_zip_path, 'wb') as f:
        f.write(r.content)
        if os.path.isfile(tmp_zip_path):
            print('Got file',os.path.basename(tmp_zip_path))
        else:
            print(tmp_zip_path,'not a file! Exiting...')
            sys.exit()
        # Check zip integrity
        try:
            zip_ref = zipfile.ZipFile(tmp_zip_path).testzip()
        except zipfile.BadZipFile as e:
            print('ERROR: Bad ZIP file')
            sys.exit()

    # extract the files we need -- .sum and .clk
    with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
        print('Extracting', measurement_base + '.sum')
        zip_ref.extract(measurement_base + '.sum',tmp_dir)
        print('Extracting', measurement_base + '.clk')
        zip_ref.extract(measurement_base + '.clk',tmp_dir)
        clktmp = tmp_dir + '/' + measurement_base + '.clk'
        #print("temp clock file:",tmp_dir + '/' + measurement_base + '.clk',
        #        "size:", \
        #        os.path.getsize(clktmp),"bytes")

    # get correction type from summary file
    # NOTE: as of 27 Nov 2022 the format of the summary file has
    # changed, and that changed how to determine the correction
    # type.  The SP3 lines now begin EMR0DC[A|B]FIN_* where the
    # last three characters before the underscore are the correction
    # type:  FIN, RAP, ULT
    with open(tmp_sum_path,'r') as f:
        while True:
            line = f.readline()
            if not line:
                break
            if line.startswith('SP3'):
                corr_type = line[:line.index("_")][-3:].strip()
                break

    if corr_type == 'ULT':
        corr_type_string = "ultra-rapid"
        corr_dir = 'ultra/'
        print("Correction type: ultra-rapid")
    elif corr_type == 'RAP':
        corr_type_string = "rapid"
        corr_dir = 'rapid/'
        print("Correction type: rapid")
    elif corr_type == 'FIN':
        corr_type_string = "final"
        corr_dir = 'final/'
        print("Correction type: final")

    zip_file_path = measurement_path + corr_dir + \
        'zip/' + measurement_base + '_' + corr_type_string + '.zip'
    sum_file_path = measurement_path + corr_dir + \
        'sum/' + measurement_base + '_' + corr_type_string + '.sum'
    clk_file_path = measurement_path + corr_dir + \
        'clk/' + measurement_base + '_' + corr_type_string + '.clk'

    #print("measurement_base:",measurement_base)
    #print("clk_file_path:",clk_file_path)

    # Move outputs to desired path and name
    try:
        #print("zip_file_path:",zip_file_path)
        shutil.move(tmp_zip_path,zip_file_path)
        if not os.path.isfile(zip_file_path):
            print("zip_file_path:",zip_file_path,"not found! Exiting...")
        shutil.move(tmp_sum_path,sum_file_path)
        if not os.path.isfile(sum_file_path):
            print("sum_file_path:",sum_file_path,"not found! Exiting...")
        shutil.move(tmp_clk_path,clk_file_path)
        if not os.path.isfile(clk_file_path):
            print("clk_file_path:",clk_file_path,"not found! Exiting...")
        #else:
            #print("clock file:",clk_file_path,"size:", \
                #os.path.getsize(clk_file_path),"bytes")
    except Exception as e:
        print("Couldn't move files from tmp to output directory:",e)
        sys.exit()  # don't delete tmp_dir since we may want to inspect
    shutil.rmtree(tmp_dir)
    #print("Moved files from tmp to output directory")

    # if we got final results, move the input file to "weekly/final/"
    if corr_type == "FIN":
        try:
            shutil.move(input_file_path,final_file_path)
        except Exception as e:
            print("Couldn't move file to weekly/final directory")
            print("Error:",e)
            print("input_file_path:")
            print(input_file_path)
            print("final_file_path:")
            print(final_file_path)
    
    # call make_gps_misc.py
    try:
        make_gps_misc(sum_file_path,measurement_path)
        print("Added data to position, offset, and maybe other files")
    except Exception as e:
        print("Couldn't make miscellaneous files, error:")
        print(e)
    print("get_gps_ppp.py:  Finished")

    return

if __name__ == '__main__':
    # this allows processing multiple files in one go
    args = options_get_gps_ppp()
    files = glob.glob(args.input_path)
    files.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
    for x in files:
        get_gps_ppp(x,args.measurement_path,args.email)

