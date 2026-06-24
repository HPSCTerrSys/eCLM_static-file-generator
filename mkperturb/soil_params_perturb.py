#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Perturb soil texture and hydraulic properties in eCLM surface files
for ensemble generation.

Sand, clay, and organic matter fractions are perturbed by adding
spatially uniform noise drawn from a uniform distribution
(±noise_range %). Physical constraints are enforced afterwards: values
are clipped to valid ranges and sand + clay is kept ≤ 100 %.

Soil hydraulic properties (saturated matric potential, porosity, shape
parameter, saturated hydraulic conductivity) are then derived from the
perturbed textures via Clapp-Hornberger pedotransfer functions and
perturbed with additive Gaussian noise in log-space, using per-cell
standard deviations that depend on sand and clay content.

Source for standard deviations of soil hydraulic parameter is Table 5
(and a little Table 4) from:
- Cosby, B. J., Hornberger, G. M., Clapp, R. B., & Ginn,
  T. R. (1984). A statistical exploration of the relationships of soil
  moisture characteristics to the physical properties of soils. Water
  Resources Research, 20(6),
  682–690. http://dx.doi.org/10.1029/wr020i006p00682

Each call to the perturbation function generates one ensemble member and writes it to
a NetCDF file named after the input file with a zero-padded member index appended
(e.g. surfdata_..._00001.nc).

Reproducibility is supported via --seed (default: 67890) or by saving/restoring
the NumPy random state to/from a JSON file (--state-file).

Usage
-----
Generate 150 ensemble members with default settings::

    python soil_params_perturb.py surfdata.nc ./ensemble/

Resume a previous run using a saved random state::

    python soil_params_perturb.py surfdata.nc ./ensemble/ --state-file rnd_state.json

Generate members 51–100 with a custom noise range::

    python soil_params_perturb.py surfdata.nc ./ensemble/ --start 50 --count 50 --noise-range 10
"""

import argparse
import os
import numpy as np
import netCDF4 as nc

from utils import rnd_state_serialize, rnd_state_deserialize, copy_attr_dim


def perturb_soil_textures_and_parameters(input_file, output_dir, iensemble=0, noise_range=20.0):
    """
    Perturb soil texture and hydraulic properties for one ensemble member.

    Sand, clay, and organic matter fractions are perturbed by adding a spatially
    uniform scalar noise drawn from Uniform(-noise_range, +noise_range) independently
    for each fraction. The same noise value is applied across all soil levels and all
    grid cells. Physical constraints are enforced afterwards:
      - Sand and clay are clipped to [0, 99] %.
      - Organic matter is clipped to [0, 130] kg/m³.
      - Sand + clay is kept ≤ 100 % via proportional rescaling.

    Soil hydraulic properties (PSIS_SAT, THETAS, SHAPE_PARAM, KSAT) are then derived
    from the perturbed textures via Clapp-Hornberger pedotransfer functions and
    perturbed with additive per-cell Gaussian noise in log-space, using standard
    deviations that depend on local sand and clay content.

    The output file is named after the input file with a zero-padded ensemble index
    appended, e.g. surfdata_..._00001.nc.

    Parameters
    ----------
    input_file : str
        Path to the source eCLM surface NetCDF file.
    output_dir : str
        Directory in which the perturbed file is written.
    iensemble : int, optional
        0-based ensemble member index used for output file naming (default: 0).
    noise_range : float, optional
        Half-range of the uniform noise in percentage points (default: 20,
        i.e. noise drawn from [-20, +20]).
    """
    sorig = input_file
    stem = os.path.splitext(os.path.basename(sorig))[0]
    sname = os.path.join(output_dir, f"{stem}_{str(iensemble + 1).zfill(5)}.nc")

    with nc.Dataset(sorig) as src, nc.Dataset(sname, "w") as dst:
        # Copy attributes
        copy_attr_dim(src, dst, script="soil_params_perturb.py")
        # dimension of perturbed fields
        dim_lvl   = src.dimensions["nlevsoi"].size
        dim_lat   = src.dimensions["lsmlat"].size
        dim_lon   = src.dimensions["lsmlon"].size
        dim_types = 3

        # Perturb %SAND, %CLAY and OM:
        rnd_type_cell = np.random.uniform(low=-noise_range, high=noise_range, size=dim_lat*dim_lon*dim_types).reshape(dim_types, dim_lat*dim_lon)
        rnd = np.zeros((dim_types, dim_lvl, dim_lat*dim_lon))
        for t in range(dim_types):
            for c in range(dim_lat*dim_lon):
                rnd[t, :, c] = rnd_type_cell[t, c]
        rnd = rnd.reshape((dim_types, dim_lvl, dim_lat, dim_lon))

        # Keep percentages normalized (sum to 100)
        pct = np.array([src.variables["PCT_SAND"][:] + rnd[0],
                        src.variables["PCT_CLAY"][:] + rnd[1],
                        src.variables["ORGANIC"][:]  + rnd[2]])
                          
        # Keep in range between 0 and 99 percent 
        for l in range(dim_lvl):
            for la in range(dim_lat):
                for lo in range(dim_lon):
 #                   for t in range(dim_types):
                        if pct[0, l, la, lo] > 99.0: 
                            pct[0, l, la, lo] = 99.0
                        if pct[1, l, la, lo] > 99.0: 
                            pct[1, l, la, lo] = 99.0
                        if pct[0, l, la, lo] < 0.0: 
                            pct[0, l, la, lo] = 0.0
                        if pct[1, l, la, lo] < 0.0:
                            pct[1, l, la, lo] = 0.0
        # Keep OM in range 
                        if pct[2,l, la, lo] > 130.0: 
                             pct[2,l, la, lo] = 130.0
                        if pct[2,l, la, lo] < 0.0: 
                             pct[2,l, la, lo] = 0.0

        # Keep percentages normalized (sum to 100)       
        for l in range(dim_lvl):
            for la in range(dim_lat):
                for lo in range(dim_lon):
                    old_sum = np.sum(pct[:2, l, la, lo])
                    for t in range(dim_types-1):
                        if old_sum > 100.0:
                            pct[t, l, la, lo] = 100.0 * pct[t, l, la, lo] / old_sum
        
        # Copy non-perturbed variables:
        for name, var in src.variables.items():
            if name != "PCT_SAND" and name != "PCT_CLAY" and name != "ORGANIC":
                nvar = dst.createVariable(name, var.datatype, var.dimensions)
                dst[name].setncatts(src[name].__dict__)
                dst[name][:] = src[name][:]

        
        # Add perturbations
        pct_sand = dst.createVariable("PCT_SAND", 
                                      datatype=np.float64, 
                                      dimensions=("nlevsoi", "lsmlat", "lsmlon",), 
                                      fill_value=1.e+30)
        pct_sand.setncatts({'long_name': u"percent sand",
                            'units': u"unitless"})
        dst.variables["PCT_SAND"][:] = pct[0].reshape(dst.variables["PCT_SAND"].shape)
        SAND = dst.variables["PCT_SAND"][:]

        pct_clay = dst.createVariable("PCT_CLAY", 
                                      datatype=np.float64, 
                                      dimensions=("nlevsoi", "lsmlat", "lsmlon",), 
                                      fill_value=1.e+30)
        pct_clay.setncatts({'long_name': u"percent clay",
                            'units': u"unitless"})
        dst.variables["PCT_CLAY"][:] = pct[1].reshape(dst.variables["PCT_CLAY"].shape)
        CLAY = dst.variables["PCT_CLAY"][:]
		
        om = dst.createVariable("ORGANIC", 
                                datatype=np.float64, 
                                dimensions=("nlevsoi", "lsmlat", "lsmlon",), 
                                fill_value=1.e+30)
        om.setncatts({'long_name': u"organic matter density at soil levels",
                      'units': u"kg/m3 (assumed carbon content 0.58 gC per gOM)"})
        dst.variables["ORGANIC"][:] = pct[2].reshape(dst.variables["ORGANIC"].shape)
        
        
        # Perturb soil hydraulic parameters
        # Saturated soil matric potential
        psis_sat = dst.createVariable("PSIS_SAT",
                                    datatype=np.float64, 
                                    dimensions=("nlevsoi", "lsmlat", "lsmlon",), 
                                    fill_value=1.e+30)
        psis_sat.setncatts({'long_name': u"Sat. soil matric potential",
                                'units': u"mmH20"})
        sucsat                       = 10. * ( 10.**(1.88-0.0131*SAND))
        sucsat_std                   = 0.72 + 0.0012*CLAY
        noise_sucsat                 = np.random.normal(loc=0.0, scale=sucsat_std, size=pct_sand.shape)
        perturbed_log_sucsat         = np.log10(sucsat) + noise_sucsat
        back_transformed_sucsat      = np.clip(np.power(10, perturbed_log_sucsat), 0, 1000)
        dst.variables["PSIS_SAT"][:] = back_transformed_sucsat

        # Porosity
        thetas = dst.createVariable("THETAS",
                                    datatype=np.float64, 
                                    dimensions=("nlevsoi", "lsmlat", "lsmlon",), 
                                    fill_value=1.e+30)
        thetas.setncatts({'long_name': u"Porosity",
                                'units': u"vol/vol"})
        watsat                     = 0.489 - 0.00126*SAND
        watsat_std                 = (7.73-0.073*CLAY) / 100.0
        noise_watsat               = np.random.normal(loc=0.0, scale=watsat_std, size=pct_sand.shape)
        perturbed_watsat           = watsat + noise_watsat
        dst.variables["THETAS"][:] = perturbed_watsat

        # Shape (b) parameter
        shape_param = dst.createVariable("SHAPE_PARAM",
                                    datatype=np.float64, 
                                    dimensions=("nlevsoi", "lsmlat", "lsmlon",), 
                                    fill_value=1.e+30)
        shape_param.setncatts({'long_name': u"Shape (b) parameter",
                                'units': u"unitless"})
        bsw                              = 2.91 + 0.159*CLAY
        bsw_std                          = 0.0500 * CLAY + 1.34 
        noise_bsw                        = np.random.normal(loc=0.0, scale=bsw_std, size=pct_clay.shape)
        perturbed_bsw                    = bsw + noise_bsw
        perturbed_bsw[perturbed_bsw < 0] = 0
        dst.variables["SHAPE_PARAM"][:]  = perturbed_bsw

        # Saturated hydraulic conductivity
        ks = dst.createVariable("KSAT",
                                datatype=np.float64, 
                                dimensions=("nlevsoi", "lsmlat", "lsmlon",), 
                                fill_value=1.e+30)
        ks.setncatts({'long_name': u"Sat. hydraulic conductivity", 'units': u"mm/s"})
        xksat                    = 0.0070556 *( 10.**(-0.884+0.0153*SAND))
        xksat_std                = 0.459 + 0.00321*(1-(SAND+CLAY)/100)
        noise_xksat              = np.random.normal(loc=0.0, scale=xksat_std, size=pct_sand.shape)
        perturbed_log_xksat      = np.log10(xksat) + noise_xksat
        back_transformed_xksat   = np.power(10, perturbed_log_xksat)
        dst.variables["KSAT"][:] = back_transformed_xksat


def main():
    """Parse command-line arguments and run the ensemble perturbation."""
    parser = argparse.ArgumentParser(
        description="Perturb soil texture and hydraulic properties in an eCLM surface file."
    )
    parser.add_argument("input_file", help="Path to the source surface NetCDF file.")
    parser.add_argument("output_dir", help="Directory for the perturbed ensemble output files.")
    parser.add_argument("--start", type=int, default=0,
                        help="First ensemble member index (0-based, default: 0).")
    parser.add_argument("--count", type=int, default=150,
                        help="Number of ensemble members to generate (default: 150).")
    parser.add_argument("--noise-range", type=float, default=20.0,
                        help="Half-range of uniform noise for sand/clay/OM perturbation "
                             "in percentage points (default: 20).")
    parser.add_argument("--seed", type=int, default=67890,
                        help="Seed for the random number generator (default: 67890).")
    parser.add_argument("--state-file", default=None,
                        help="Path to a JSON file for saving/restoring the random state. "
                             "If the file exists, the state is restored from it (resuming a "
                             "previous run) and --seed is ignored. After the run, the state "
                             "is saved to this file.")
    args = parser.parse_args()

    if args.state_file and os.path.isfile(args.state_file):
        print(f"Warning: --state-file '{args.state_file}' exists; ignoring --seed.")
        rnd_state_deserialize(args.state_file)
        print(f"Restored random state from '{args.state_file}'.")
    else:
        np.random.seed(args.seed)
        print(f"Random seed: {args.seed}")

    os.makedirs(args.output_dir, exist_ok=True)

    for ens in range(args.start, args.start + args.count):
        perturb_soil_textures_and_parameters(
            args.input_file, args.output_dir, ens, noise_range=args.noise_range
        )
        print(f"Ensemble member {ens + 1} perturbed and saved to output file.")

    if args.state_file:
        rnd_state_serialize(args.state_file)
        print(f"Saved random state to '{args.state_file}'.")


if __name__ == "__main__":
    main()
