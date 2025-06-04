#!/usr/bin/env python3

import math
from mpl_toolkits.mplot3d import Axes3D
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy
import astropy.io.ascii
import glob
import argparse

#############################################################################
# Hard-coded config
#############################################################################

# if set, print pdf as well as png
make_pdf = False

# output size in px is figsize (inches) x png_dpi
figsize_x = 6
figsize_y = 6
png_dpi = 300

# size of scatter points
scatter_size = 1

xlabel = 'Longitude, m'
ylabel = 'Latitude, m'
zlabel = 'Height, m'

# Title location
suptitle_x = 0.50
suptitle_y = 0.975
title_x = 0.50
title_y = 1.03

plt.rcParams.update({'font.size': 14})  # change to suit
plt.rcParams.update({'figure.titlesize': 18})  # change to suit
plt.rcParams.update({'axes.titlesize': 14})  # change to suit
plt.rcParams.update({'axes.titlepad': 0})  # change to suit
plt.rcParams.update({'axes.labelsize': 10})  # change to suit
plt.rcParams.update({'xtick.labelsize': 8})  # change to suit
plt.rcParams.update({'ytick.labelsize': 8})  # change to suit
plt.rcParams.update({'legend.fontsize': 8})  # change to suit
plt.rcParams.update({'legend.handlelength': 0})  # change to suit
plt.rcParams.update({'legend.markerscale': 3})  # change to suit

color=('r','g','b','m','y','c','k','gray')
#marker=('o','v','^','<','>','8','s','*')
marker=('o','o','o','o','o','o','o','o')

##############################################################################
# command line options
##############################################################################

parser = argparse.ArgumentParser(description='Plot GPS data.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('file', type=str, nargs='+', help='Files to plot')
parser.add_argument('-basename', type=str, default='gps', help='Prefix for plot output')
parser.add_argument('-outdir', type=str, default='.', help='Output directory')
parser.add_argument('-lim', type=float, nargs=2, default=[0,0], help='Limits (-/+)')
parser.add_argument('-title',type=str, default='', help = 'Main title for all plots')
parser.add_argument('-xytitle',type=str, default='XY Plane', help = 'Main title for all plots')
parser.add_argument('-xztitle',type=str, default='XZ Plane', help = 'Main title for all plots')
parser.add_argument('-xyztitle',type=str, default='XYZ Plane', help = 'Main title for all plots')
parser.add_argument('-centered', type=bool, default=True, help='Center scale around zero')

args = parser.parse_args()
if len(args.file) > 8:
    raise ValueError('Maximum of 8 files for plotting')

rows = 2
cols = int(1+(len(args.file)-1)/2)
outfile = args.outdir + '/' + args.basename
suptitle = args.title
xytitle = args.xytitle
xztitle = args.xztitle
xyztitle = args.xyztitle
lower = args.lim[0]
upper = args.lim[1]

###############################################################################
# functions
###############################################################################

# get the minimum and maximum values in the data set
# and use those to set "autoscaled" plots
def get_limits(d,files,centered=True):
    xscale_max = yscale_max = zscale_max = -1e12
    xscale_min = yscale_min = zscale_min = 1e12

    for fh in files:
        if d[fh]['x'].min() < xscale_min:
            xscale_min = d[fh]['x'].min()
        if d[fh]['x'].max() > xscale_max:
            xscale_max = d[fh]['x'].max()

        if d[fh]['y'].min() < yscale_min:
            yscale_min = d[fh]['y'].min()
        if d[fh]['x'].max() > xscale_max:
            yscale_max = d[fh]['y'].max()

        if d[fh]['z'].min() < zscale_min:
            zscale_min = d[fh]['z'].min()
        if d[fh]['z'].max() > zscale_max:
            zscale_max = d[fh]['z'].max()

    xylower = roundup(min(xscale_min,yscale_min),1)
    xyupper = roundup(max(xscale_max,yscale_max),1)

    xzlower = roundup(min(xscale_min,zscale_min),1)
    xzupper = roundup(max(xscale_max,zscale_max),1)

    xyzlower = roundup(min(xscale_min,yscale_min,zscale_min),1)
    xyzupper = roundup(max(xscale_max,yscale_max,zscale_max),1)

    if centered:
        xylower = 0.0 - max(abs(xylower),abs(xyupper))
        xyupper = max(abs(xylower),abs(xyupper))
        xzlower = 0.0 - max(abs(xzlower),abs(xzupper))
        xzupper = max(abs(xzlower),abs(xzupper))
        xyzlower = 0.0 - max(abs(xyzlower),abs(xyzupper))
        xyzupper = max(abs(xyzlower),abs(xyzupper))

    return(xylower,xyupper,xzlower,xzupper,xyzlower,xyzupper)

# round up to x decimal places
def roundup(x,places):
    d = 10 ** places
    if x < 0:
        x = math.floor(x * d) / d
    else:
        x = math.ceil(x * d) / d
    return(x)

# xyz individual subplots
def xyz_subplots():
    fig = plt.figure(figsize=(16,9))
    fig.suptitle(suptitle,x=suptitle_x,y=suptitle_y)
    count = 0
    for nm in d.keys():
        ax = fig.add_subplot(rows,cols,count+1, projection='3d')
        ax.view_init(azim=30)  # angle can be 0 - 360 deg
        ax.scatter(d[nm]['x'], d[nm]['y'], d[nm]['z'], c=color[count],
            marker=marker[count], s=scatter_size)
        ax.set_zlim(xyzlower,xyzupper)
        ax.set_xlim(xyzlower,xyzupper)
        ax.set_ylim(xyzlower,xyzupper)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_zlabel(zlabel)
        if make_pdf:
            fig.savefig('%s_xyz_separate.pdf' % outfile)
        fig.savefig('%s_xyz_separate.png' % outfile, dpi=png_dpi)
        count += 1
    return
    
# xyz stacked plots
def xyz_stacked():
    count = 0
    fig = plt.figure(figsize=(figsize_x,figsize_y))
    fig.suptitle(suptitle,x=suptitle_x,y=suptitle_y)
    ax = fig.add_subplot(111,projection='3d')
    ax.set_title(xyztitle,x=title_x, y=title_y + 0.1)
    ax.view_init(azim=30)  # angle can be 0 - 360 deg
    ax.set_zlim(xyzlower,xyzupper)
    ax.set_xlim(xyzlower,xyzupper)
    ax.set_ylim(xyzlower,xyzupper)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_zlabel(zlabel)
    for nm in d.keys():
        ax.scatter(d[nm]['x'], d[nm]['y'], d[nm]['z'], c=color[count],
            marker=marker[count], s=scatter_size, label=nm)
        ax.legend(loc='upper right', borderaxespad=0.)
        if make_pdf:
            fig.savefig('%s_xyz_stacked_plt%i.pdf' % outfile,count)
        fig.savefig('%s_xyz_stacked_plt%i.png' % (outfile,count),
            dpi=png_dpi)
        count += 1
    return

# xy projection only
def xy():
    count = 0
    fig = plt.figure(figsize=(figsize_x,figsize_y))
    fig.suptitle(suptitle,x=suptitle_x,y=suptitle_y)
    ax = fig.add_subplot(111)
    ax.set_title(xytitle,x=title_x, y=title_y)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(xylower,xyupper)
    ax.set_ylim(xylower,xyupper)
    for nm in d.keys():
        ax.scatter(d[nm]['x'], d[nm]['y'], c=color[count],
            marker=marker[count], s=scatter_size, label=nm)
        ax.legend(loc='upper right', borderaxespad=0.)
        if make_pdf:
            fig.savefig('%s_xy_plt%i.pdf' % (outfile,count))
        fig.savefig('%s_xy_plt%i.png' % (outfile,count), dpi=png_dpi)
        count += 1
    return

# xz projection only
def xz():
    count = 0
    fig = plt.figure(figsize=(figsize_x,figsize_y))
    fig.suptitle(suptitle,x=suptitle_x,y=suptitle_y)
    ax = fig.add_subplot(111)
    ax.set_title(xztitle,x=title_x, y=title_y)
    ax.set_xlim(xzlower,xzupper)
    ax.set_ylim(xzlower,xzupper)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(zlabel)
    for nm in d.keys():
        ax.scatter(d[nm]['x'], d[nm]['z'], c=color[count],
            marker=marker[count], s=scatter_size, label=nm)
        ax.legend(loc='upper right', borderaxespad=0.)
        if make_pdf:
            fig.savefig('%s_xz_plt%i.pdf' % (outfile,count))
        fig.savefig('%s_xz_plt%i.png' % (outfile,count), dpi=png_dpi)
        count += 1
    return

############################################################################
# do it
############################################################################

d = {}
for fh in args.file:
    d[fh] = astropy.io.ascii.read(fh, \
        names=('blah1','blah2','x','y','z','lat','lon','height'))

if args.lim[0] == 0 and args.lim[1] == 0:
    (xylower,xyupper,xzlower,xzupper,xyzlower,xyzupper) = \
        get_limits(d,args.file,args.centered)
else:
    xylower = xzlower = xyzlower = args.lim[0]
    xyupper = xzupper = xyzupper = args.lim[1]

print('XY  Scale Limits:',xylower,xyupper)
print('XZ  Scale Limits:',xzlower,xzupper)
print('XYZ Scale Limits:',xyzlower,xyzupper)

# xyz_subplots()
xyz_stacked()
xy()
xz()
