#!/usr/bin/env python3

import sys
import os
import time
import numpy as np
import matplotlib.pyplot as plt
import scipy.interpolate
import scipy.stats as st

# ppp2xyz.py
# reduce LLH values from NRCan CSRS-PPP results to +/- meters around 
# average value for plotting.  Actual location data is lost in this
# process!

##### NOTE:  Deletes first readings (3 hours if 30 second interval) to 
##### get rid of data convergence.  This is just a test
junk = 360

# argv[1] = input file
# output files created from input file basename with
# _xyz.dat and _xyz95.dat appended at end

# NRCan CSRS-PPP service .csv file fields:
# latitude_decimal_degree, longitude_decimal_degree
# ellipsoidal_height_m, decimal_hour, day_of_year, year,
# ortho_height_m_cgvd28, rcvr_clk_ns

# NRCan CSRS-PPP service .pos file fields:
# direc, frame, stn, doy, yyyy_mm_dd, hr_mn_ssss, nsv, gdop, rmsc_m, rmsp_m,
# dlat_m, dlon_m, dhgt_m, clk_ns, tzd_m, sdlat_95, sdlon_95, sdhgt_95,
# sdclk_95, sdtzd_95, latdd, latmn, latss, londd, lonmn, lonss, hgt_m

# per the calculator at http://www.csgnetwork.com/degreelenllavcalc.html
# at 45N:     1 deg lat = 111131.745m;         1 deg lon = 78846.80572069259m
# at 39.75N:  1 deg lat = 111029.80515286454m; 1 deg lon = 85704.42637043189m
# for now, hard coding 39.75N since that's where I am.

# x = lon, y = lat, z = elevation

m_per_deg_lat = 111029.805
m_per_min_lat = round(m_per_deg_lat / 60, 3)
m_per_sec_lat = round(m_per_deg_lat / 3600, 4)

m_per_deg_lon = 85704.426
m_per_min_lon = round(m_per_deg_lat / 60, 3)
m_per_sec_lon = round(m_per_deg_lat / 3600, 4)

# confidence interval for std dev
conf_int = 0.95

# reads from NRCan .pos file; returns 1e12 for x,y,z if problems.
# NOTE: a major simplifying assumption is at work here.  At my
# location, I am centered within one integer second of both lat
# and lon.  So I read only the seconds field and convert that to
# meters, ignoring the degrees and minutes.  This helps keep the
# numbers within float precision.
def read_xyz(line):
    try:
        ( direc, frame, stn, doy, yyyy_mm_dd, hr_mn_ssss, nsv,
         gdop, rmsc_m, rmsp_m, dlat_m, dlon_m, dhgt_m, clk_ns, 
         tzd_m, sdlat_95, sdlon_95, sdhgt_95, sdclk_95, sdtzd_95, 
         latdd, latmn, latss, londd, lonmn, lonss, hgt_m ) \
            = line.split()

        # makes sure input is numeric; return bignum if not
        try:
            x = float(lonss) * m_per_sec_lon
            y = float(latss) * m_per_sec_lat
            z = abs(float(hgt_m))
        except:
            return(1e12,1e12,1e12)
    except:
        return(1e12,1e12,1e12)
    return(x,y,z)

def find_conf_int(a):
    xd = a
    f,ax = plt.subplots()
    hd = ax.hist(xd,5000,density=True,histtype='step',cumulative=True,label='')
    ifn = scipy.interpolate.interp1d(hd[0],hd[1][:-1])
    conf_lower=ifn(0.023)
    conf_upper=ifn(0.977)
    return(conf_lower,conf_upper)

###########################################################################
inf = sys.argv[1]
basename = os.path.splitext(sys.argv[1])[0]
outf = basename + "_xyz.dat"
outf_sigma = basename + "_xyz95.dat"
xlist = [] 
ylist = [] 
zlist = [] 

# first pass to get stats
with open(inf,'r') as infile:
    counter = 0
    while True:
        line = infile.readline()
        if not line:
            break
        else:
            (x,y,z) = read_xyz(line)
            # only add if sane values from read_xyz
            if x != 1e12 and y != 1e12 and z != 1e12:
                if counter > junk:   # throw out first readings
                    xlist.append(x)
                    ylist.append(y)
                    zlist.append(z)
                counter += 1
infile.close()

# convert to numpy array
xarray = np.array(xlist, dtype = 'float64')
yarray = np.array(ylist, dtype = 'float64')
zarray = np.array(zlist, dtype = 'float64')

# make and show statistics of original results

xrang = abs(xarray.max() - xarray.min())
yrang = abs(yarray.max() - yarray.min())
zrang = abs(zarray.max() - zarray.min())

(xconf_lower,xconf_upper) = find_conf_int(xarray)
(yconf_lower,yconf_upper) = find_conf_int(yarray)
(zconf_lower,zconf_upper) = find_conf_int(zarray)

print("# x = lon, y = lat, z = elevation")
print(
"#         mean    median       min       max     range     CI(u)     CI(l)")
print("# x: {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f}".\
    format(xarray.mean(),np.median(xarray),xarray.min(),xarray.max(),
    xrang,xconf_lower,xconf_upper))
print("# y: {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f}".\
    format(yarray.mean(),np.median(yarray),yarray.min(),yarray.max(),
    yrang,yconf_lower,yconf_upper))
print("# z: {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f}".\
    format(zarray.mean(),np.median(zarray),zarray.min(),zarray.max(),
    zrang,zconf_lower,zconf_upper))

print()

# subtract mean to make zero-centered
xarray -= xarray.mean()
yarray -= yarray.mean()
zarray -= zarray.mean()

xrang = abs(xarray.max() - xarray.min())
yrang = abs(yarray.max() - yarray.min())
zrang = abs(zarray.max() - zarray.min())

# get 95% confidence interval
(xconf_lower,xconf_upper) = find_conf_int(xarray)
(yconf_lower,yconf_upper) = find_conf_int(yarray)
(zconf_lower,zconf_upper) = find_conf_int(zarray)

print( "# zero-centered values")
print("# x: {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f}".\
    format(xarray.mean(),np.median(xarray),xarray.min(),xarray.max(),
    xrang,xconf_lower,xconf_upper))
print("# y: {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f}".\
    format(yarray.mean(),np.median(yarray),yarray.min(),yarray.max(),
    yrang,yconf_lower,yconf_upper))
print("# z: {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f} {:9.4f}".\
    format(zarray.mean(),np.median(zarray),zarray.min(),zarray.max(),
    zrang,zconf_lower,zconf_upper))
print()

# second pass to process data
try:
    outfile_all = open(outf,'w')
except:
    print("Couldn't open",outf,"!")
    exit(1)

try:
    outfile_sigma = open(outf_sigma,'w')
except:
    print("Couldn't open",outf_sigma,"!")
    exit(1)

count = 0
xcount = ycount = zcount = tot_count = 0

while count < len(xarray):
    x = xarray[count]
    y = yarray[count]
    z = zarray[count]

    result = "{:8.5f}\t{:8.5f}\t{:8.5f}\n".format(x,y,z)
    outfile_all.write(result)

    if xconf_lower <= x:
        if xconf_upper >= x:
            xcount += 1
    if yconf_lower <= y:
        if yconf_upper >= y:
            ycount += 1
    if zconf_lower <= z:
        if zconf_upper >= z:
            zcount += 1

    if (xconf_lower <= x <= xconf_upper) \
        and (yconf_lower <= y <= yconf_upper) \
        and (zconf_lower <= z <= zconf_upper):
            tot_count += 1
            outfile_sigma.write(result)

    count += 1

print("# num obs, num within x, y, z, all  CI:",end=" ")
print(count,xcount,ycount,zcount,tot_count)
outfile_all.close()
outfile_sigma.close()
