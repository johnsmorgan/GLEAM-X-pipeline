#!/usr/bin/env python

"""Manage basic obsid operations from a set of obsids
"""

import os
import numpy as np
import pandas as pd
from gleam_x.db import mysql_db as gxdb
from argparse import ArgumentParser


def clean_obsids(obsids):
    """Ensure a consistency to the provided set of obsids in terms of datatypes and format

    Args:
        obsids (Iterable): Obsids to process
    """
    obsids = [int(obsid) for obsid in obsids]

    return obsids


def read_obsids_file(path):
    """Simple file reader for a line delimited obsid set, typical within the GLEAM-X pipeline

    Args:
        path (str): File path to a list of obsids
    
    Returns:
        list[int]: List of ints that describe the GLEAM-X observation IDs
    """
    obsids = np.loadtxt(path)
    obsids = clean_obsids(obsids)

    return obsids


def write_obsids_file(obsids, path, clobber=True, *args, **kwargs):
    """Write a new-line delimited file of obsids

    Args:
        obsids (Iterable): Obsids to write out
        path (str): Path to write obsids to

    Keyword Args:
        clobber (bool): Overwrite existing file if it exists
    """
    obsids = clean_obsids(obsids)

    if not clobber and os.path.exists(path):
        raise FileExistsError(f"Output file {path} already exists")

    with open(path, "w") as outfile:
        print(f"Writing {path} with {len(obsids)} obsids")
        for obsid in obsids:
            print(obsid, file=outfile)


def obsids_from_db(obsids):
    """Obtain the observation details from the gleam-x database

    Args:
        obsids (Iterable): List of observations ids to obtain
    
    Returns:
        pandas.DataFrame: Constructed properties based on GLEAM-X observations table
    """
    dbconn = gxdb.connect()

    cursor = dbconn.cursor()
    cursor.execute(
        f"SELECT * FROM observation WHERE obs_id IN ({', '.join(['%s' for _ in obsids])})",
        (*obsids,),
    )

    columns = [c[0] for c in cursor.description]
    df = pd.DataFrame(cursor.fetchall(), columns=columns)

    return df


def split(path, column="cenchan", *args, **kwargs):
    """Spilt obsids up based on some characteristic from a column of the constructed dataframe

    Properties are constructed / extracted from the GLEAM-X meta-data database

    Args:
        path (str): Path to line-delimited obsid file 
    
    Keywprd Args:
        column (str): Column name of the constructed dataframe. 
    """
    obsids = read_obsids_file(path)
    obsids_df = obsids_from_db(obsids)

    for idx, sub_df in obsids_df.groupby(by=column):
        sub_obsids = clean_obsids(sub_df["obs_id"])

        name, ext = os.path.splitext(path)
        out_path = f"{name}_{column}_{idx}{ext}"

        write_obsids_file(sub_obsids, out_path, *args, **kwargs)


if __name__ == "__main__":
    parser = ArgumentParser(description="Basic operations on sets of obsids")

    parser.add_argument(
        "obsids", type=str, help="Path to new-line delimited set of obsids"
    )

    subparsers = parser.add_subparsers(dest="mode")

    split_parser = subparsers.add_parser(
        "split", help="Split a set of obsids up based on their cenchan propert"
    )
    split_parser.add_argument(
        "-c",
        "--clobber",
        default=True,
        action="store_false",
        help="Overwrite existing output file if it already exists",
    )

    args = parser.parse_args()

    if args.mode == "split":
        print("Split mode")
        split(args.obsids, clobber=args.clobber)
    else:
        print(f"Directive mode {args.mode} not present. ")
