import os
import sys
from astropy.coordinates import SkyCoord
from astropy import wcs
from astropy.io import fits
from astropy.time import Time
import astropy.units as u
import json
import sqlite3
import numpy as np
from populate_sources_table import Source
from check_src_fov import check_coords
from beam_value_at_radec import beam_value

__author__ = "Natasha Hurley-Walker"

dbfile = os.environ['DBFILE']

def insert_app(obs_id, source, appflux, infov, cur):
    cur.execute(""" INSERT OR REPLACE INTO calapparent
                (obs_id, source, appflux, infov)
                VALUES (?, ?, ?, ?); """,
                (obs_id, source, appflux, infov))
    return

def get_srcs(cur):
    srciter = cur.execute("""
    SELECT source, ra, dec, flux, alpha, beta
    FROM sources""")
    return srciter

# NB: Currently selects all observations; may want to finesse this later
def get_obs(cur, obs_id = None):
    
    if obs_id is None:
        obsiter = cur.execute("""
        SELECT obs_id, ra_pointing, dec_pointing, cenchan, starttime, delays
        FROM observation """)
    
    else:
        obsiter = cur.execute("""
        SELECT obs_id, ra_pointing, dec_pointing, cenchan, starttime, delays
        FROM observation WHERE obs_id == ? """, (obs_id, ))
    
    return obsiter

def create_wcs(ra, dec, cenchan):
    pixscale = 0.5 / float(cenchan)
    w = wcs.WCS(naxis=2)
    w.wcs.crpix = [4000,4000]
    w.wcs.cdelt = np.array([-pixscale,pixscale])
    w.wcs.crval = [ra, dec]
    w.wcs.ctype = ["RA---SIN", "DEC--SIN"]
    w.wcs.cunit = ["deg","deg"]
    w._naxis1 = 8000
    w._naxis2 = 8000
    return w

if __name__ == "__main__":
    print 'Connecting to ', dbfile
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()

    srclist = []
    for row in get_srcs(cur):
        srclist.append(Source(row[0],SkyCoord(row[1],row[2],unit=u.deg),row[3],row[4],row[5]))

    # Figure out where obsids are coming from
    # TODO: Add a proper argument parser
    if len(sys.argv) == 1:
        print 'Getting all obsids from the user database'
        obsids = get_obs(cur)
    else:
        print 'Reading obsids from ' + sys.argv[1]
        obsids = [i.strip() for i in open(sys.argv[1], 'r')]

        # This could be done with one call with a change to the SQL WHERE
        obsids = [list(get_obs(cur, obs_id=i))[0] for i in obsids]


    for row in obsids:
        print row

        w = create_wcs(row[1],row[2],row[3])
        t = Time(int(row[4]), format='gps')
        freq = 1.28 * row[3]
        for src in srclist:
            # Delays are stored as a string by json
            xx, yy = beam_value(src.pos.ra.deg, src.pos.dec.deg, t, json.loads(row[5]), freq*1.e6)
            # Ignoring spectral curvature parameter for now
            appflux = src.flux * ( (freq / 150.)**(src.alpha) ) * (xx+yy)/2.
            if np.isnan(appflux):
                appflux = 0.0
            print row[0], src.name, appflux, check_coords(w, src.pos)
            insert_app(row[0], src.name, appflux, check_coords(w, src.pos), cur)
    conn.commit()
    conn.close()
