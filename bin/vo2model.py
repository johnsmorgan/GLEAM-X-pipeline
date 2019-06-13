#!/usr/bin/env python

# Convert fits and VO catalogues to Andre's sky model format

import os, sys
from string import replace

import numpy as np
#tables and votables
import astropy.io.fits as fits
from astropy.io.votable import parse_single_table
from astropy.coordinates import SkyCoord
import astropy.units as u

from optparse import OptionParser

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--catalogue',type="string", dest="catalogue",
                    help="The filename of the catalogue you want to read in.", default=None)
parser.add_option('--output',type="string", dest="output",
                    help="The filename of the output (default=test.txt).", default="test.txt")
parser.add_option('--namecol',type="string", dest="namecol",
                    help="The name of the Name column (no default).", default="Name")
parser.add_option('--racol',type="string", dest="racol",
                    help="The name of the RA column (default=ra_str).", default="ra_str")
parser.add_option('--decol',type="string", dest="decol",
                    help="The name of the Dec column (default=dec_str).", default="dec_str")
parser.add_option('--acol',type="string", dest="acol",
                    help="The name of the major axis column (default=a_wide).", default="a_wide")
parser.add_option('--bcol',type="string", dest="bcol",
                    help="The name of the minor axis column (default=b_wide).", default="b_wide")
parser.add_option('--pacol',type="string", dest="pacol",
                    help="The name of the position angle column (default=pa_wide).", default="pa_wide")
parser.add_option('--fluxcol',type="string", dest="fluxcol",
                    help="The name of the flux density column (default=int_flux_wide).", default="int_flux_wide")
parser.add_option('--freq',type=float, dest="freq",
                    help="The frequency at which the flux density measurements are made, in MHz (default=200).", default=200.)
parser.add_option('--alphacol',type="string", dest="alphacol",
                    help="The name of the spectral index alpha-term column (default=alpha).", default="alpha")
parser.add_option('--betacol',type="string", dest="betacol",
                    help="The name of the spectral index curvature beta-term column (default=beta).", default="beta")
parser.add_option('--alpha',type=float, dest="alpha",
                    help="The value of alpha to use if there is no alpha column (default = -0.83)", default=-0.83)
parser.add_option('--beta',type=float, dest="beta",
                    help="The value of beta to use if there is no beta column (default = 0.0).", default=0.0)
parser.add_option('--point', dest='point', action='store_true' ,
                    help="Output unresolved sources as point sources instead of Gaussians (default=False). Need to specify resolution, and both int and peak flux columns for this to work, or have blank major/minor axis columns to indicate unresolved sources.", default=False)
parser.add_option('--resolution',type=float, dest="resolution",
                    help="The int/peak value below which a source is considered unresolved (default=1.2).", default=1.2)
parser.add_option('--intflux',type="string", dest="intflux",
                    help="Int flux column (default=int_flux_wide).", default="int_flux_wide")
parser.add_option('--peakflux',type="string", dest="peakflux",
                    help="Peak flux column (default=peak_flux_wide).", default="peak_flux_wide")
#parser.add_option('--betacol',type="string", dest="betacol",
#                    help="The name of the spectral index beta-term column (default=beta).", default="beta")
(options, args) = parser.parse_args()

if options.output is None:
    output="test.txt"
else:
    output=options.output

if options.catalogue is None:
    print "must specify input catalogue"
    sys.exit(1)
else:
    filename, file_extension = os.path.splitext(options.catalogue)
    if file_extension == ".fits":
        temp = fits.open(options.catalogue)
        data = temp[1].data
    elif file_extension == ".vot":
        temp = parse_single_table(options.catalogue)
        data = temp.array

if options.fluxcol is None:
    print "Must have a valid flux density column"
    sys.exit(1)
try:
    names = data[options.namecol]
except KeyError:
    names = np.array(["J"+(data[options.racol][i][:-3]+data[options.decol][i][:-3]).replace(':','') for i in range(len(data[options.racol]))])
try: 
    alpha = data[options.alphacol]
except KeyError:
    alpha = options.alpha*np.ones(shape=data[options.fluxcol].shape)
try:
    beta = data[options.betacol]
except KeyError:
    beta = options.beta*np.ones(shape=data[options.fluxcol].shape)

if type(data[options.racol][0]) == str:
    rastr = True
else:
    rastr = False

# Generate an output in Andre's sky model format
#formatter="source {{\n  name \"{Name:s}\"\n  component {{\n    type gaussian\n    position {RA:s} {Dec:s}\n    shape {a:s} {b:s} {pa:s}\n    sed {{\n      frequency {freq:3.0f} MHz\n      fluxdensity Jy {flux:s} 0 0 0\n      spectral-index {{ {alpha:s} {beta:2.2f} }}\n    }}\n  }}\n}}\n"
gformatter="source {{\n  name \"{Name:s}\"\n  component {{\n    type {shape:s}\n    position {RA:s} {Dec:s}\n    shape {a:2.1f} {b:2.1f} {pa:4.1f}\n    sed {{\n      frequency {freq:3.0f} MHz\n      fluxdensity Jy {flux:4.7f} 0 0 0\n      spectral-index {{ {alpha:2.2f} {beta:2.2f} }}\n    }}\n  }}\n}}\n"
pformatter="source {{\n  name \"{Name:s}\"\n  component {{\n    type {shape:s}\n    position {RA:s} {Dec:s}\n    sed {{\n      frequency {freq:3.0f} MHz\n      fluxdensity Jy {flux:4.7f} 0 0 0\n      spectral-index {{ {alpha:2.2f} {beta:2.2f} }}\n    }}\n  }}\n}}\n"

shape = np.empty(shape=data[options.fluxcol].shape,dtype="S8")
shape.fill("gaussian")

if options.point:
   try:
       srcsize = data[options.intflux]/data[options.peakflux]
       indices = np.where(srcsize<options.resolution)
   except KeyError:
       indices = np.where(np.isnan(data[options.acol]))
   shape[indices] = "point"

bigzip=zip(names,data[options.racol],data[options.decol],data[options.acol],data[options.bcol],data[options.pacol],data[options.fluxcol],alpha,beta,shape)

f = open(options.output,"w")
f.write("skymodel fileformat 1.1\n")
f.close()

with open(options.output,"a") as f:
    for Name,RA,Dec,a,b,pa,flux,alpha,beta,shape in bigzip:
        if RAstr:
            coords = SkyCoord(RA, Dec, frame="fk5", unit=(u.hour, u.deg))
        else:
            coords = SkyCoord(RA, Dec, frame="fk5", unit=(u.deg, u.deg))
#            RA = replace(RA,":","h",1)
#            RA = replace(RA,":","m",1)
#            RA = RA+"s"
#            Dec = replace(Dec,":","d",1)
#            Dec = replace(Dec,":","m",1)
#            Dec = Dec+"s"
        RA = coords.ra.to_string(u.hour)
        Dec = coords.dec.to_string(u.deg)
        if shape=="gaussian":
            f.write(gformatter.format(Name=Name,RA=RA,Dec=Dec,a=a,b=b,pa=pa,flux=flux,alpha=alpha,beta=beta,freq=options.freq,shape=shape))
        elif shape=="point":
            f.write(pformatter.format(Name=Name,RA=RA,Dec=Dec,flux=flux,alpha=alpha,beta=beta,freq=options.freq,shape=shape))

