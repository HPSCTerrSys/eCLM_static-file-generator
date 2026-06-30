#!/usr/bin/env python3
"""
Add 16 new PFT-dimensioned variables to a eCLM parameter file.

By default variables are initialised to their fill value (np.nan for
floats, 2147483647 for integers) so that unset indices are
unambiguously missing.

Pass --zero-fill to use 0 / 0.0 as fill value instead, which matches
the original Selhausen parameter file.

Usage:
    setup_new_vars.py INPUT.nc OUTPUT.nc
    setup_new_vars.py INPUT.nc OUTPUT.nc --zero-fill
"""

import sys
import argparse
import shutil
import numpy as np
import netCDF4 as nc


# Fill-value sentinels
_FV_F8      = np.nan                      # float missing  (default)
_FV_I4      = nc.default_fillvals["i4"]  # = 2147483647   (default)
_FV_F8_ZERO = 0.0                         # --zero-fill
_FV_I4_ZERO = np.int32(0)                # --zero-fill

# ---------------------------------------------------------------------------
# New-variable definitions:  (name, dtype, attrs_dict)
# All are (pft,)-dimensioned.  _FillValue is popped and passed separately.
# ---------------------------------------------------------------------------
NEW_VARS = [
    ("aleafstor", "f8", {
        "_FillValue": _FV_F8,
        "long_name": "Leaf allocation coefficient to storage post harvest used in CNAllocation",
        "units": "unitless", "coordinates": "pftname",
    }),
    ("arootf2", "f8", {
        "_FillValue": None,  # no _FillValue in original file
        "long_name": "Late root Allocation coefficient parameter used in CNAllocation",
        "units": "unitless", "coordinates": "pftname",
    }),
    ("covercrop", "i4", {
        "_FillValue": _FV_I4,
        "long_name": "covercrop flag", "units": "-", "coordinates": "pftname",
    }),
    ("crequ", "f8", {
        "_FillValue": _FV_F8,
        "long_name": "Chilling requirements for bud burst of fruit tree crops",
        "units": "days", "coordinates": "pftname",
        "comment:": ("Bud burst is calculated using the Sequential Model from "
                     "Cesaraccio et al. 2005, used values for crequ should be "
                     "calibrated for the region and cultivar"),
    }),
    ("crit_temp", "f8", {
        "_FillValue": _FV_F8,
        "long_name": "Critical temperature to initiate leaf offset for fruit tree crops",
        "units": "K", "coordinates": "pftname",
    }),
    ("grnrp", "f8", {
        "_FillValue": None,  # no _FillValue in original file
        "long_name": "Growing Degree Days for fruit expansion used in CNPhenology",
        "units": "unitless", "coordinates": "pftname",
    }),
    ("lfmat", "f8", {
        "_FillValue": None,  # no _FillValue in original file
        "long_name": "Growing Degree Days for canopy maturity used in CNPhenology",
        "units": "unitless", "coordinates": "pftname",
    }),
    ("max_NH_harvest_date", "i4", {
        "_FillValue": _FV_I4,
        "long_name": "Maximum apple harvest date for the Northern Hemisphere",
        "units": "YYYMMDD", "coordinates": "pftname",
        "comment:": ("Typical apple harvest dates for the Northern Hemisphere vary "
                     "with variety and can range from mid August to November"),
    }),
    ("max_SH_harvest_date", "i4", {
        "_FillValue": _FV_I4,
        "long_name": "Maximum apple harvest date for the Southern Hemisphere",
        "units": "YYYMMDD", "coordinates": "pftname",
        "comment:": ("Typical apple harvest dates for the Southern Hemisphere vary "
                     "with variety and can range from mid January to May"),
    }),
    ("mulch_pruning", "f8", {
        "_FillValue": _FV_F8,
        "long_name": "Binary flag for exporting or mulching of pruning material",
        "units": "logical flag", "coordinates": "pftname",
        "flag_meanings": "exporting mulching",
        "flag_values": np.array([0., 1.]),
    }),
    ("ndays_stor", "f8", {
        "_FillValue": _FV_F8,
        "long_name": "Length of period for storage growth of fruit tree crops",
        "units": "days", "coordinates": "pftname",
    }),
    ("nstem", "f8", {
        "_FillValue": _FV_F8,
        "long_name": "Stem density", "units": "#/m2", "coordinates": "pftname",
    }),
    ("perennial", "f8", {
        "_FillValue": None,  # no _FillValue in original file
        "long_name": "Binary flag for perennial crop phenology",
        "units": "logical flag", "coordinates": "pftname",
        "flag_meanings": "NON-perennial perennial",
        "flag_values": np.array([0., 1.]),
    }),
    ("prune_fr", "f8", {
        "_FillValue": _FV_F8,
        "long_name": "Fraction of deadstem biomass that is pruned",
        "units": "unitless", "coordinates": "pftname",
    }),
    ("taper", "f8", {
        "_FillValue": _FV_F8,
        "long_name": "Tapering ratio of height:radius_breast_height",
        "units": "unitless", "coordinates": "pftname",
    }),
    ("transplant", "f8", {
        "_FillValue": None,  # no _FillValue in original file
        "long_name": "Initial carbon for crops transplanted from nursery",
        "units": "gC/m2", "coordinates": "pftname",
    }),
]


def setup_new_vars(src_path: str, dst_path: str, zero_fill: bool = False) -> None:
    fv_f8 = _FV_F8_ZERO if zero_fill else _FV_F8
    fv_i4 = _FV_I4_ZERO if zero_fill else _FV_I4

    shutil.copy2(src_path, dst_path)

    with nc.Dataset(dst_path, "r+") as ds:
        npft = ds.dimensions["pft"].size

        for name, dtype, attrs in NEW_VARS:
            orig_fv = attrs.pop("_FillValue")

            if zero_fill and orig_fv is None:
                # No fill value in original: create without one, init to real zeros
                var = ds.createVariable(name, dtype, ("pft",))
                var.setncatts(attrs)
                var[:] = np.zeros(npft, dtype=dtype)
            else:
                # Use runtime fill value (safe NaN/max-int by default, 0 with --zero-fill)
                fv = fv_i4 if dtype == "i4" else fv_f8
                var = ds.createVariable(name, dtype, ("pft",), fill_value=fv)
                var.setncatts(attrs)
                var[:] = np.full(npft, fv, dtype=dtype)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_nc",  metavar="INPUT.nc")
    parser.add_argument("output_nc", metavar="OUTPUT.nc")
    parser.add_argument("--zero-fill", action="store_true",
                        help="Use 0 / 0.0 as fill value (matches original Selhausen "
                             "param file); default is np.nan / 2147483647")
    args = parser.parse_args()
    setup_new_vars(args.input_nc, args.output_nc, zero_fill=args.zero_fill)
    print(f"Done: {args.output_nc}")


if __name__ == "__main__":
    main()
