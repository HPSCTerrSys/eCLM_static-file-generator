#!/usr/bin/env python3
"""
Add one or more new PFT-dimensioned variables to a eCLM parameter file.

Variables are initialised to their fill value by default (np.nan for floats,
2147483647 for integers) so that unset indices are unambiguously missing.

Usage:
    # Minimal: name and dtype only
    setup_new_vars.py INPUT.nc OUTPUT.nc --var "myparam|f8"

    # With attributes (all optional after dtype)
    setup_new_vars.py INPUT.nc OUTPUT.nc \\
        --var "myparam|f8|My parameter description|unitless|pftname"

    # Multiple variables in one call
    setup_new_vars.py INPUT.nc OUTPUT.nc \\
        --var "myparam|f8|My parameter|kg/m2|pftname" \\
        --var "myflag|i4|My flag|-|pftname"

    # Use 0 / 0.0 as fill value instead of NaN / 2147483647
    setup_new_vars.py INPUT.nc OUTPUT.nc --zero-fill \\
        --var "myparam|f8|My parameter|unitless|pftname"

    # No _FillValue attribute at all; initialise to real zeros
    setup_new_vars.py INPUT.nc OUTPUT.nc --no-fill-value \\
        --var "myparam|f8|My parameter|unitless|pftname"

--var format:  NAME|DTYPE[|LONG_NAME[|UNITS[|COORDINATES]]]
    NAME         netCDF variable name
    DTYPE        f8, f4, i4, i2, …
    LONG_NAME    optional descriptive name
    UNITS        optional units string
    COORDINATES  optional coordinates attribute (e.g. pftname)
    Fields are separated by | (not : ) to allow colons in long_name.
"""

import sys
import argparse
import shutil
import numpy as np
import netCDF4 as nc


def add_vars(src_path: str, dst_path: str, var_specs: list,
             zero_fill: bool = False, no_fill_value: bool = False) -> None:
    fv_f8 = 0.0         if zero_fill else np.nan
    fv_i4 = np.int32(0) if zero_fill else nc.default_fillvals["i4"]

    shutil.copy2(src_path, dst_path)

    with nc.Dataset(dst_path, "r+") as ds:
        npft = ds.dimensions["pft"].size

        for spec in var_specs:
            parts = spec.split("|")
            if len(parts) < 2:
                raise ValueError(f"--var requires at least NAME|DTYPE, got: {spec!r}")
            name, dtype = parts[0], parts[1]
            attrs = {}
            if len(parts) > 2 and parts[2]: attrs["long_name"]   = parts[2]
            if len(parts) > 3 and parts[3]: attrs["units"]       = parts[3]
            if len(parts) > 4 and parts[4]: attrs["coordinates"] = parts[4]

            if no_fill_value:
                var = ds.createVariable(name, dtype, ("pft",))
                var.setncatts(attrs)
                var[:] = np.zeros(npft, dtype=dtype)
            else:
                fv = fv_i4 if dtype == "i4" else fv_f8
                var = ds.createVariable(name, dtype, ("pft",), fill_value=fv)
                var.setncatts(attrs)
                var[:] = np.full(npft, fv, dtype=dtype)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_nc",  metavar="INPUT.nc")
    parser.add_argument("output_nc", metavar="OUTPUT.nc")
    parser.add_argument("--var", metavar="NAME|DTYPE[|LONG_NAME[|UNITS[|COORDINATES]]]",
                        action="append", required=True,
                        help="Variable to add (repeatable). See header for format.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--zero-fill", action="store_true",
                      help="Use 0 / 0.0 as fill value (default: np.nan / 2147483647)")
    mode.add_argument("--no-fill-value", action="store_true",
                      help="No _FillValue attribute; initialise to real zeros")
    args = parser.parse_args()
    add_vars(args.input_nc, args.output_nc, args.var,
             zero_fill=args.zero_fill, no_fill_value=args.no_fill_value)
    print(f"Done: {args.output_nc}")


if __name__ == "__main__":
    main()
