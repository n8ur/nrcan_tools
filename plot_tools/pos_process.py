#!/usr/bin/env python3
# coding: utf-8

import sys
import os
import astropy.io.ascii
import scipy
import scipy.interpolate
import pylab
import numpy
import scipy.stats as st

# read position file created by n8ur nrcan_ppp tools
# fields are:
# unix_epoch, iso_8601, ecef_x, ecef_y, ecef_z, lat, lon, height
a = astropy.io.ascii.read(open(sys.argv[1]).readlines())

def make_plots(a,name,loc='upper left'):
    xd = a[name]-numpy.median(a[name])
    (xconf_lower,xconf_upper) = st.t.interval(
        0.95, len(xd) - 1, 0.0, st.sem(xd))
    print((xconf_lower,xconf_upper))

    f,ax = pylab.subplots()
    ax.hist(xd,5000,density=True, histtype='step', \
        cumulative=True, label='Cumulative Normalized %s'%(name))
    ax.legend(loc=loc)
    ax.grid()
    f.savefig('n8ur_%s_cumwide.pdf' % (name))
    
    f,ax = pylab.subplots()
    ax.hist(xd,5000,density=True, histtype='step', \
        cumulative=True, label='Cumulative Normalized %s'%(name))
    ax.set_xlim(2*xconf_lower,2*xconf_upper)
    ax.axvline(xconf_lower, color='r',label='95%% lower [%.4e]'%(xconf_lower))
    ax.axvline(xconf_upper, color='r',label='95%% upper [%.4e]'%(xconf_upper))
    ax.legend(loc=loc)
    ax.grid()
    f.savefig('n8ur_%s_cumnarrow.pdf' % (name))

def find_conf_int(a,name,loc='upper left'):
    xd = a[name]-numpy.median(a[name])
    
    f,ax = pylab.subplots()
    hd = ax.hist(xd,5000,density=True,histtype='step', \
        cumulative=True,label='Cumulative Normalized %s'%(name))
    ifn = scipy.interpolate.interp1d(hd[0],hd[1][:-1])
    xconf_lower=ifn(0.023)
    xconf_upper=ifn(0.977)
    ax.set_xlim(2*xconf_lower,2*xconf_upper)
    ax.axvline(xconf_lower,color='r',label='2.3%% lower [%.4e]'%(xconf_lower))
    ax.axvline(xconf_upper,color='r',label='97.7%% upper [%.4e]'%(xconf_upper))
    ax.legend(loc=loc)
    ax.grid()
    f.savefig('n8ur_%s_histcum.pdf'%(name))

##################################################

for var in ('x','y','z'):
    make_plots(a,var)
    find_conf_int(a,var)
