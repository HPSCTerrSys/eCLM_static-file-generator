#!/usr/bin/env python3
"""
Rename entries in the pftname char array of a eCLM parameter file.

Usage:
    set_pftname.py INPUT.nc OUTPUT.nc IDX NAME [IDX NAME ...]

Example:
    set_pftname.py base.nc out.nc 77 covercrop_1 78 covercrop_2
"""

import sys
import shutil
import numpy as np
import netCDF4 as nc


def set_pftnames(src_path: str, dst_path: str, renames: dict) -> None:
    """Copy src to dst and apply {index: name} renames to pftname."""
    shutil.copy2(src_path, dst_path)
    with nc.Dataset(dst_path, "r+") as ds:
        slen = ds.dimensions["string_length"].size
        for idx, name in renames.items():
            padded = name.ljust(slen)[:slen]
            ds["pftname"][idx] = np.array(
                [c.encode("utf-8") for c in padded], dtype="S1"
            )


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 4 or (len(args) - 2) % 2 != 0:
        print(f"Usage: {sys.argv[0]} INPUT.nc OUTPUT.nc IDX NAME [IDX NAME ...]",
              file=sys.stderr)
        sys.exit(1)

    src, dst = args[0], args[1]
    pairs = args[2:]
    renames = {}
    for i in range(0, len(pairs), 2):
        try:
            renames[int(pairs[i])] = pairs[i + 1]
        except ValueError:
            print(f"Error: '{pairs[i]}' is not a valid integer index", file=sys.stderr)
            sys.exit(1)

    set_pftnames(src, dst, renames)
    print(f"Done: {dst}")


if __name__ == "__main__":
    main()
