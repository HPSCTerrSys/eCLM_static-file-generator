#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Perturb soil hydraulic properties in eCLM surface files for ensemble generation.

Two perturbation modes are supported:

- **hydraulic**: Soil hydraulic properties (saturated matric potential, porosity,
  shape parameter, saturated hydraulic conductivity) are computed from the
  Clapp-Hornberger pedotransfer functions as implemented in CLM, adjusted for
  organic matter content, and then multiplied by a spatially uniform Gaussian
  random factor. The perturbed properties are written as new variables
  (PSIS_SAT_adj, THETAS_adj, SHAPE_PARAM_adj, KSAT_adj) on the full CLM ground
  layer grid (nlevgrnd = 25).

- **texture**: Sand, clay, and organic matter fractions are perturbed by adding
  spatially uniform noise drawn from a uniform distribution. Physical constraints
  (non-negativity, sand + clay <= 100 %) are enforced after perturbation.

Each call to the main perturbation functions generates one ensemble member and
writes it to a NetCDF file named after the input file with a zero-padded member
index appended (e.g. surfdata_..._00001.nc).

Reproducibility is supported via an explicit --seed argument or by
saving/restoring the NumPy random state to/from a JSON file (--state-file).

Original author: Yorck Ewerdwalbesloh
"""

import argparse
import datetime
import json
import os

import netCDF4 as nc
import numpy as np


def rnd_state_serialize(state_file):
    """Save the current NumPy random state to a JSON file.

    Parameters
    ----------
    state_file : str
        Path to the output JSON file.
    """
    tmp_state = np.random.get_state()
    save_state = ()
    for i in tmp_state:
        if type(i) is np.ndarray:
            save_state = save_state + (i.tolist(),)
        else:
            save_state = save_state + (i,)
    json.dump(save_state, open(state_file, "w"))


def rnd_state_deserialize(state_file):
    """Restore the NumPy random state from a JSON file written by rnd_state_serialize.

    Parameters
    ----------
    state_file : str
        Path to the JSON file containing the saved random state.
    """
    tmp_state = json.load(open(state_file, "r"))
    load_state = ()
    for i in tmp_state:
        if type(i) is list:
            load_state = load_state + (np.array(i),)
        else:
            load_state = load_state + (i,)
    np.random.set_state(load_state)


def copy_attr_dim(src, dst):
    """Copy global attributes and dimensions from a source to a destination NetCDF dataset.

    All original global attributes are copied with the prefix
    'original_attribute_'. The dimensions are copied with their sizes.
    Additionally, 'perturbed_by' (from $USER) and 'perturbed_on_date' attributes
    are added to the destination.

    Parameters
    ----------
    src : netCDF4.Dataset
        Open source dataset to copy from.
    dst : netCDF4.Dataset
        Open destination dataset to copy into.
    """
    # copy attributes
    for name in src.ncattrs():
        dst.setncattr("original_attribute_" + name, src.getncattr(name))
    # copy dimensions
    for name, dimension in src.dimensions.items():
        dst.createDimension(name, len(dimension))
    # Additional attribute
    dst.setncattr("perturbed_by", os.getenv("USER", "unknown"))
    dst.setncattr("perturbed_on_date",
                  datetime.datetime.today().strftime("%d.%m.%y"))


def disturb_sand_clay(input_file, output_dir, iensemble=0, noise_range=10):
    """Perturb soil texture by adding spatially uniform noise to sand, clay, and OM fractions.

    A single scalar noise value is drawn independently for each of PCT_SAND,
    PCT_CLAY, and ORGANIC from a uniform distribution on
    [-noise_range, +noise_range] and added to the entire spatial field. Physical
    constraints are enforced afterwards:
      - Cells with zero sand are left at zero (ocean/glacier mask).
      - sand + clay is kept <= 100 %.
      - Values are clipped to [min_observed, 100] for each fraction.
      - Organic matter is clipped to [0, 130] kg/m³ and zeroed where the
        original is zero.

    The output file is named after the input file with a zero-padded ensemble
    index appended, e.g. surfdata_..._00001.nc.

    Parameters
    ----------
    input_file : str
        Path to the source eCLM surface NetCDF file.
    output_dir : str
        Directory in which the perturbed file is written.
    iensemble : int, optional
        0-based ensemble member index used for output file naming (default: 0).
    noise_range : float, optional
        Half-range of the uniform noise in percentage points (default: 10,
        i.e. noise drawn from [-10, +10]).
    """
    sorig = input_file
    ncid = nc.Dataset(sorig, "r")
    # Get the variables
    sand = ncid.variables["PCT_SAND"][:]
    clay = ncid.variables["PCT_CLAY"][:]
    org = ncid.variables["ORGANIC"][:]
    # Close the netCDF file
    ncid.close()

    # Extremes of the variables
    idx_zero = sand == 0
    idx_nonzero = sand != 0
    min_sand = np.min(sand[idx_nonzero])
    min_clay = np.min(clay[idx_nonzero])

    # Generate spatially uniform distributed noise
    noise_sand = noise_range - 2 * noise_range * np.random.rand(1)
    noise_clay = noise_range - 2 * noise_range * np.random.rand(1)
    noise_om = noise_range - 2 * noise_range * np.random.rand(1)

    stem = os.path.splitext(os.path.basename(sorig))[0]
    sname = os.path.join(output_dir, f"{stem}_{str(iensemble + 1).zfill(5)}.nc")

    sand_dis = sand + noise_sand
    clay_dis = clay + noise_clay
    sand_dis[idx_zero] = 0
    clay_dis[idx_zero] = 0

    idx = (sand_dis + clay_dis) > 100
    temp = (sand_dis + clay_dis - 100) / 2
    sand_dis[idx] = sand_dis[idx] - temp[idx]
    clay_dis[idx] = clay_dis[idx] - temp[idx]

    idx = sand_dis > 100
    sand_dis[idx] = sand_dis[idx] - (sand_dis[idx] - 100)
    clay_dis[idx] = clay_dis[idx] - (sand_dis[idx] - 100)

    idx = clay_dis > 100
    sand_dis[idx] = sand_dis[idx] - (clay_dis[idx] - 100)
    clay_dis[idx] = clay_dis[idx] - (clay_dis[idx] - 100)

    idx = (sand_dis + clay_dis) < 0
    temp = (sand_dis + clay_dis) / 2
    sand_dis[idx] = sand_dis[idx] - temp[idx]
    clay_dis[idx] = clay_dis[idx] - temp[idx]

    idx = np.logical_and(sand_dis < min_sand, idx_nonzero)
    sand_dis[idx] = np.minimum(
        sand_dis[idx] - sand_dis[idx] + min_sand, 100 - min_sand
    )
    clay_dis[idx] = clay_dis[idx] - sand_dis[idx] + min_sand

    idx = np.logical_and(clay_dis < min_clay, idx_nonzero)
    sand_dis[idx] = np.minimum(
        sand_dis[idx] - clay_dis[idx] + min_clay, 100 - min_clay
    )
    clay_dis[idx] = clay_dis[idx] - clay_dis[idx] + min_clay

    om_dis = org + noise_om
    om_dis[idx_zero] = 0
    om_dis[org == 0] = 0
    om_dis[om_dis > 130] = 130
    om_dis[om_dis < 0] = 0

    with nc.Dataset(sorig) as src, nc.Dataset(sname, "w") as dst:
        # Copy attributes
        copy_attr_dim(src, dst)

        # Copy non-perturbed variables:
        for name, var in src.variables.items():
            if name != "PCT_SAND" and name != "PCT_CLAY" and name != "ORGANIC":
                nvar = dst.createVariable(name, var.datatype, var.dimensions)
                dst[name].setncatts(src[name].__dict__)
                dst[name][:] = src[name][:]
        # Add perturbations
        pct_sand = dst.createVariable(
            "PCT_SAND",
            datatype=np.float64,
            dimensions=(
                "nlevsoi",
                "lsmlat",
                "lsmlon",
            ),
            fill_value=1.0e30,
        )
        pct_sand.setncatts({"long_name": "percent sand", "units": "unitless"})

        pct_clay = dst.createVariable(
            "PCT_CLAY",
            datatype=np.float64,
            dimensions=(
                "nlevsoi",
                "lsmlat",
                "lsmlon",
            ),
            fill_value=1.0e30,
        )
        pct_clay.setncatts({"long_name": "percent clay", "units": "unitless"})

        om = dst.createVariable(
            "ORGANIC",
            datatype=np.float64,
            dimensions=(
                "nlevsoi",
                "lsmlat",
                "lsmlon",
            ),
            fill_value=1.0e30,
        )
        om.setncatts(
            {
                "long_name": "organic matter density at soil levels",
                "units": "kg/m3 (assumed carbon content 0.58 gC per gOM)",
            }
        )

        dst.variables["PCT_SAND"][:] = sand_dis.reshape(
            dst.variables["ORGANIC"].shape
        )

        dst.variables["PCT_CLAY"][:] = clay_dis.reshape(
            dst.variables["ORGANIC"].shape
        )

        dst.variables["ORGANIC"][:] = om_dis.reshape(dst.variables["ORGANIC"].shape)


def soil_parameters(
    input_file,
    output_dir,
    iensemble=0,
    std_sucsat=0.2,
    std_watsat=0.05,
    std_bsw=0.1,
    std_hksat=0.1,
    max_watsat=0.93,
    hksat_clip=(0.5, 2.0),
    n_perturb_levels=25,
):
    """Perturb soil hydraulic properties directly using CLM pedotransfer functions.

    For each ensemble member, four hydraulic properties are computed from the
    Clapp-Hornberger pedotransfer functions as coded in CLM, adjusted for organic
    matter content following the CLM parameterization, and then multiplied by a
    spatially uniform scalar drawn from N(1, std_*). The perturbed fields are
    written on the full CLM ground layer grid (nlevgrnd = 25 levels) as new
    variables alongside all original variables:

      - PSIS_SAT_adj : saturated soil matric potential (mmH2O)
      - THETAS_adj   : porosity (vol/vol), clipped to [0, max_watsat]
      - SHAPE_PARAM_adj : Clapp-Hornberger b parameter (unitless)
      - KSAT_adj     : saturated hydraulic conductivity (mm/s)

    The soil layer geometry and pedotransfer coefficients follow the CLM5 source
    code. Organic matter adjustment uses the parameterization of Lawrence and
    Slater (2008).

    The output file is named after the input file with a zero-padded ensemble
    index appended, e.g. surfdata_..._00001.nc.

    Parameters
    ----------
    input_file : str
        Path to the source eCLM surface NetCDF file.
    output_dir : str
        Directory in which the perturbed file is written.
    iensemble : int, optional
        0-based ensemble member index used for output file naming (default: 0).
    std_sucsat : float, optional
        Std dev of the multiplicative Gaussian noise for saturated matric
        potential (default: 0.2).
    std_watsat : float, optional
        Std dev of the multiplicative Gaussian noise for porosity (default: 0.05).
    std_bsw : float, optional
        Std dev of the multiplicative Gaussian noise for the shape (b) parameter
        (default: 0.1).
    std_hksat : float, optional
        Std dev of the multiplicative Gaussian noise for saturated hydraulic
        conductivity (default: 0.1).
    max_watsat : float, optional
        Upper clip applied to the perturbed porosity (default: 0.93).
    hksat_clip : tuple of float, optional
        (min, max) bounds applied to the Ksat multiplicative factor before
        scaling, to prevent extreme values (default: (0.5, 2.0)).
    n_perturb_levels : int, optional
        Number of levels (counting from the surface) to which the random
        perturbation is applied. Deeper levels receive the unperturbed CLM
        mean values. Must be <= nlevgrnd (25). Default: 25 (all levels).
    """
    sorig = input_file
    stem = os.path.splitext(os.path.basename(sorig))[0]
    sname = os.path.join(output_dir, f"{stem}_{str(iensemble + 1).zfill(5)}.nc")

    with nc.Dataset(sorig) as src, nc.Dataset(sname, "w") as dst:

        copy_attr_dim(src, dst)

        dst.createDimension("nlevgrnd", 25)

        dim_lvl = src.dimensions["nlevsoi"].size
        dim_lat = src.dimensions["lsmlat"].size
        dim_lon = src.dimensions["lsmlon"].size
        dim_types = 3

        # perturb organic matter

        organic = src["ORGANIC"][:]
        pct_sand = src["PCT_SAND"][:]
        pct_clay = src["PCT_CLAY"][:]

        # Copy non-perturbed variables:
        for name, var in src.variables.items():
            nvar = dst.createVariable(name, var.datatype, var.dimensions)
            dst[name].setncatts(src[name].__dict__)
            dst[name][:] = src[name][:]

        # initialize variables in nc file
        psis_sat = dst.createVariable(
            "PSIS_SAT_adj",
            datatype=np.float64,
            dimensions=(
                "nlevgrnd",
                "lsmlat",
                "lsmlon",
            ),
            fill_value=1.0e3,
        )
        psis_sat.setncatts(
            {"long_name": "Sat. soil matric potential", "units": "mmH20"}
        )

        thetas = dst.createVariable(
            "THETAS_adj",
            datatype=np.float64,
            dimensions=(
                "nlevgrnd",
                "lsmlat",
                "lsmlon",
            ),
            fill_value=1.0e30,
        )
        thetas.setncatts({"long_name": "Porosity", "units": "vol/vol"})

        # Shape (b) parameter
        shape_param = dst.createVariable(
            "SHAPE_PARAM_adj",
            datatype=np.float64,
            dimensions=(
                "nlevgrnd",
                "lsmlat",
                "lsmlon",
            ),
            fill_value=1.0e30,
        )
        shape_param.setncatts({"long_name": "Shape (b) parameter", "units": "unitless"})

        # Saturated hydraulic conductivity
        ks = dst.createVariable(
            "KSAT_adj",
            datatype=np.float64,
            dimensions=(
                "nlevgrnd",
                "lsmlat",
                "lsmlon",
            ),
            fill_value=1.0e30,
        )
        ks.setncatts({"long_name": "Sat. hydraulic conductivity", "units": "mm/s"})

        # sample one random value per vairable per ensemble member with standard deviations that are chosen pretty randomly based on what rovides the best spread
        random_value_sucsat = np.random.normal(loc=1, scale=std_sucsat)
        random_value_watsat = np.random.normal(loc=1, scale=std_watsat)
        random_value_bsw = np.random.normal(loc=1, scale=std_bsw)
        random_value_hksat = np.random.normal(loc=1, scale=std_hksat)

        # first, compute depth at which sand and clay are taken for one layer, based on CLM source code

        zsoifl = np.zeros(pct_sand.shape[0])
        zisoifl = np.zeros(pct_sand.shape[0] + 1)
        dzsoifl = np.zeros(pct_sand.shape[0])

        for j in range(pct_sand.shape[0]):
            zsoifl[j] = 0.025 * (np.exp(0.5 * (j + 1 - 0.5)) - 1)

        dzsoifl[0] = 0.5 * (zsoifl[0] + zsoifl[1])
        for j in range(1, pct_sand.shape[0] - 1):
            dzsoifl[j] = 0.5 * (zsoifl[j + 1] - zsoifl[j - 1])
        dzsoifl[pct_sand.shape[0] - 1] = (
            zsoifl[pct_sand.shape[0] - 1] - zsoifl[pct_sand.shape[0] - 2]
        )

        zisoifl[0] = 0
        for j in range(1, pct_sand.shape[0]):
            zisoifl[j] = 0.5 * (zsoifl[j - 1] + zsoifl[j])
        zisoifl[pct_sand.shape[0]] = (
            zsoifl[pct_sand.shape[0] - 1] + 0.5 * dzsoifl[pct_sand.shape[0] - 1]
        )

        nlevsoi = 20
        nlevgrnd = 25

        dzsoi = np.zeros(nlevgrnd)
        zisoi = np.zeros(nlevgrnd + 1)
        zsoi = np.zeros(nlevgrnd)

        for j in range(4):
            dzsoi[j] = (j + 1) * 0.02

        for j in range(4, 13):
            dzsoi[j] = dzsoi[3] + (j - 3) * 0.04

        for j in range(13, nlevsoi):
            dzsoi[j] = dzsoi[12] + (j - 12) * 0.10

        for j in range(nlevsoi, nlevgrnd):
            dzsoi[j] = dzsoi[nlevsoi - 1] + (((j - (nlevsoi - 1)) * 25) ** 1.5) / 100

        zisoi[0] = 0
        for j in range(1, nlevgrnd + 1):
            zisoi[j] = np.sum(dzsoi[:j])

        for j in range(nlevgrnd):
            zsoi[j] = 0.5 * (zisoi[j] + zisoi[j + 1])

        for j in range(nlevgrnd):

            # use right sand and clay values (from depth that we computed), as well as organic matter for adjustment
            if j == 0:
                sand = pct_sand[0, :, :]
                clay = pct_clay[0, :, :]
                org = organic[0, :, :]
            elif j < nlevsoi:
                for k in range(pct_sand.shape[0] - 1):
                    if zisoi[j + 1] >= zisoifl[k + 1] and zisoi[j + 1] < zisoifl[k + 2]:
                        clay = pct_clay[k + 1, :, :]
                        sand = pct_sand[k + 1, :, :]
                        org = organic[k + 1, :, :]
            else:
                clay = pct_clay[-1, :, :]
                sand = pct_sand[-1, :, :]
                org = np.zeros(organic[-1, :, :].shape)

            # compute soil hydraulic properties like in CLM
            sucsat = 10 * 10 ** (1.88 - 0.0131 * sand)
            watsat = 0.489 - 0.00126 * sand
            bsw = 2.91 + 0.159 * clay
            xksat = 0.0070556 * 10 ** (-0.884 + 0.0153 * sand)

            # some paramters from CLM
            om_frac = org / 130
            zsapric = 0.5
            pcalpha = 0.5
            pcbeta = 0.139

            # adjust values with organic matter
            om_watsat = np.maximum(0.93 - 0.1 * (zsoi[j] / zsapric), 0.83)

            om_b = np.minimum(2.7 + 9.3 * (zsoi[j] / zsapric), 12.0)

            om_sucsat = np.minimum(10.3 - 0.2 * (zsoi[j] / zsapric), 10.1)

            lok = (0.28 - 0.2799 * (zsoi[j] / zsapric)) * np.ones(xksat.shape)
            om_hksat = np.maximum(lok, xksat)

            watsat = (1 - om_frac) * watsat + om_frac * om_watsat
            bsw = (1 - om_frac) * bsw + om_frac * om_b
            sucsat = (1 - om_frac) * sucsat + om_frac * om_sucsat

            perc_norm = np.where(om_frac > pcalpha, (1.0 - pcalpha) ** (-pcbeta), 0)
            perc_frac = np.where(
                om_frac > pcalpha, perc_norm * (om_frac - pcalpha) ** pcbeta, 0
            )
            uncon_frac = (1 - om_frac) + (1 - perc_frac) * om_frac
            uncon_hksat = np.where(
                om_frac < 1.0,
                uncon_frac
                / (
                    ((1.0 - om_frac) / xksat) + ((1.0 - perc_frac) * om_frac) / om_hksat
                ),
                0,
            )
            hksat = uncon_frac * uncon_hksat + (perc_frac * om_frac) * om_hksat

            # perturb adjusted parameters and write them in the surface files
            if j < n_perturb_levels:
                dst.variables["PSIS_SAT_adj"][j, :, :] = sucsat * random_value_sucsat
                dst.variables["THETAS_adj"][j, :, :] = np.clip(
                    watsat * random_value_watsat, 0, max_watsat
                )
                dst.variables["SHAPE_PARAM_adj"][j, :, :] = bsw * random_value_bsw
                dst.variables["KSAT_adj"][j, :, :] = hksat * np.clip(
                    random_value_hksat, hksat_clip[0], hksat_clip[1]
                )
            else:
                dst.variables["PSIS_SAT_adj"][j, :, :] = sucsat
                dst.variables["THETAS_adj"][j, :, :] = np.clip(watsat, 0, max_watsat)
                dst.variables["SHAPE_PARAM_adj"][j, :, :] = bsw
                dst.variables["KSAT_adj"][j, :, :] = hksat


def main():
    """Parse command-line arguments and run the ensemble perturbation."""
    parser = argparse.ArgumentParser(
        description="Perturb soil hydraulic properties in an eCLM surface file."
    )
    parser.add_argument("input_file", help="Path to the source surface NetCDF file.")
    parser.add_argument("output_dir", help="Directory for the perturbed ensemble output files.")
    parser.add_argument("--start", type=int, default=0, help="First ensemble member index (0-based, default: 0).")
    parser.add_argument("--count", type=int, default=50, help="Number of ensemble members to generate (default: 50).")
    parser.add_argument(
        "--mode",
        choices=["hydraulic", "texture"],
        default="hydraulic",
        help="Perturbation mode: 'hydraulic' perturbs soil hydraulic properties directly "
             "(default), 'texture' perturbs sand/clay/OM fractions.",
    )
    # Perturbation parameters — hydraulic mode
    parser.add_argument("--std-sucsat", type=float, default=0.2, help="Std dev of multiplicative noise for saturated matric potential (default: 0.2).")
    parser.add_argument("--std-watsat", type=float, default=0.05, help="Std dev of multiplicative noise for porosity (default: 0.05).")
    parser.add_argument("--std-bsw", type=float, default=0.1, help="Std dev of multiplicative noise for shape (b) parameter (default: 0.1).")
    parser.add_argument("--std-hksat", type=float, default=0.1, help="Std dev of multiplicative noise for saturated hydraulic conductivity (default: 0.1).")
    parser.add_argument("--max-watsat", type=float, default=0.93, help="Upper clip for perturbed porosity (default: 0.93).")
    parser.add_argument("--hksat-clip", type=float, nargs=2, default=[0.5, 2.0], metavar=("MIN", "MAX"), help="Clip bounds for the Ksat multiplicative factor (default: 0.5 2.0).")
    parser.add_argument("--n-perturb-levels", type=int, default=25, help="Number of levels from the surface to which the perturbation is applied; deeper levels receive unperturbed CLM mean values (default: 25, i.e. all levels).")
    # Perturbation parameters — texture mode
    parser.add_argument("--noise-range", type=float, default=10.0, help="Half-range of uniform noise for sand/clay/OM perturbation in percentage points (default: 10).")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed for the random number generator. If omitted, a random seed is used and printed.",
    )
    parser.add_argument(
        "--state-file",
        default=None,
        help="Path to a JSON file for saving/restoring the random state. "
             "If the file exists, the state is restored from it (resuming a previous run) "
             "and --seed is ignored. After the run, the state is saved to this file.",
    )
    args = parser.parse_args()

    # Initialise random state
    if args.state_file and os.path.isfile(args.state_file):
        if args.seed is not None:
            print(f"Warning: --state-file '{args.state_file}' exists; ignoring --seed.")
        rnd_state_deserialize(args.state_file)
        print(f"Restored random state from '{args.state_file}'.")
    else:
        seed = args.seed if args.seed is not None else int(np.random.randint(0, 2**31))
        np.random.seed(seed)
        print(f"Random seed: {seed}")

    os.makedirs(args.output_dir, exist_ok=True)

    for i in range(args.start, args.start + args.count):
        if args.mode == "hydraulic":
            soil_parameters(
                args.input_file, args.output_dir, i,
                std_sucsat=args.std_sucsat,
                std_watsat=args.std_watsat,
                std_bsw=args.std_bsw,
                std_hksat=args.std_hksat,
                max_watsat=args.max_watsat,
                hksat_clip=args.hksat_clip,
                n_perturb_levels=args.n_perturb_levels,
            )
        else:
            disturb_sand_clay(args.input_file, args.output_dir, i, noise_range=args.noise_range)
        print(f"Done with ensemble member {i + 1}")

    if args.state_file:
        rnd_state_serialize(args.state_file)
        print(f"Saved random state to '{args.state_file}'.")


if __name__ == "__main__":
    main()
