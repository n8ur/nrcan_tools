#!/bin/bash

# argv[0] = top level directory
# argv[1] = station name
# argv[2] = hostname
# argv[3] = email address
# argv[4] = zip
# argv[5] = cleanup
# argv[6] = year (default none)
# argv[7] = doy (default none)

/usr/local/bin/ppp_runner.py '/data/nrcan/maser_netrs1' 'netrs' \
    'netrs1.febo.com' 'NetRS1' 'jra@febo.com' 'true' 'false'
/usr/local/bin/ppp_runner.py '/data/nrcan/z3805a_netrs2' 'netrs' \
    'netrs2.febo.com' 'NetRS2' 'jra@febo.com' 'true' 'false'
/usr/local/bin/ppp_runner.py '/data/nrcan/maser_mosaic' 'mosaic' \
    'mosaic-t1.febo.com' 'n8ur' 'jra@febo.com' 'true' 'false'

#/usr/local/bin/get_gps_ftp.py 'netrs' 'netrs1.febo.com' 'NetRS1' \
#    '/data/nrcan/maser_netrs1'
#/usr/local/bin/get_gps_ftp.py 'mosaic' 'mosaic-t1.febo.com' 'n8ur' \
#    '/data/nrcan/maser_mosaic'

