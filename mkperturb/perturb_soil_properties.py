#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import netCDF4 as nc

# import matplotlib.pyplot as plt
# import pandas as pd
# import seaborn as sns
# import os
import json
import datetime

# from pandas.plotting import scatter_matrix
# import pdb


num_ensemble = 50


# Helper functions


# Helper function to serialize / deserialize random state with json


def rnd_state_serialize():
    tmp_state = np.random.get_state()
    save_state = ()
    for i in tmp_state:
        if type(i) is np.ndarray:
            save_state = save_state + (i.tolist(),)
        else:
            save_state = save_state + (i,)
    json.dump(save_state, open("rnd_state.json", "w"))


def rnd_state_deserialize():
    tmp_state = json.load(open("rnd_state.json", "r"))
    load_state = ()
    for i in tmp_state:
        if type(i) is list:
            load_state = load_state + (np.array(i),)
        else:
            load_state = load_state + (i,)
    np.random.set_state(load_state)


# Helper function - copy attributes and dimensions
def copy_attr_dim(src, dst):
    # copy attributes
    for name in src.ncattrs():
        dst.setncattr("original_attribute_" + name, src.getncattr(name))
    # copy dimensions
    for name, dimension in src.dimensions.items():
        dst.createDimension(name, len(dimension))
    # Additional attribute
    dst.setncattr("perturbed_by", "Y.Ewerdwalbesloh")
    dst.setncattr("perturbed_on_date",
                  datetime.datetime.today().strftime("%d.%m.%y"))


def disturbSandClay(num_ensemble=64):  # Yorck code
    sorig = (
        "/p/project1/detectc01/clm_inputfiles/eCLM/surface/"
        + "surface_file_no_irrigation_LC_corrected/"
        + "surfdata_EUR-11_hist_16pfts_Irrig_CMIP6_simyr2000_c230808_GLC2000"
        + ".nc"
    )
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
    max_sand = np.max(sand[idx_nonzero])
    min_clay = np.min(clay[idx_nonzero])
    max_clay = np.max(clay[idx_nonzero])

    # Generate spatially uniform distributed noise, +-10%
    noise_sand = 10 - 20 * np.random.rand(num_ensemble, 1)
    noise_clay = 10 - 20 * np.random.rand(num_ensemble, 1)
    noise_om = 10 - 20 * np.random.rand(num_ensemble, 1)

    for i in range(num_ensemble):
        sname = (
            "/p/project/detectc01/clm_inputfiles/eCLM/"
            + "surface/ensemble_texture/"
            + "surfdata_"
            + "EUR-11_hist_16pfts_Irrig_CMIP6_simyr2000_c230808_GLC2000_"
            + str(i + 1).zfill(5)
            + ".nc"
        )

        sand_dis = sand + noise_sand[i]
        clay_dis = clay + noise_clay[i]
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

        om_dis = org + noise_om[i]
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


def SoilParameters(iensemble=0):

    sname = (
        "/p/project1/detectc01/clm_inputfiles/eCLM/surface/ensemble_test/"
        + "surfdata_EUR-11_hist_16pfts_Irrig_CMIP6_simyr2000_c230808_GLC2000_"
        + str(iensemble + 1).zfill(5)
        + ".nc"
    )
    sorig = "/p/project1/detectc01/clm_inputfiles/eCLM/surface/surface_file_no_irrigation_LC_corrected/surfdata_EUR-11_hist_16pfts_Irrig_CMIP6_simyr2000_c230808_GLC2000.nc"

    with nc.Dataset(sorig) as src, nc.Dataset(sname, "w") as dst:

        copy_attr_dim(src, dst)

        dst.createDimension("nlevgrnd", 25)

        dim_lvl = src.dimensions["nlevsoi"].size
        dim_lat = src.dimensions["lsmlat"].size
        dim_lon = src.dimensions["lsmlon"].size
        dim_lvl_p = 25
        dim_types = 3

        # perturb organic matter

        organic = src["ORGANIC"][:]
        pct_sand = src["PCT_SAND"][:]
        pct_clay = src["PCT_CLAY"][:]

        # noise_om   = 10-20*np.random.rand(1)

        # perturbed_om = organic + noise_om
        # perturbed_om[perturbed_om>130] = 130
        # perturbed_om[organic==0] = 0
        # perturbed_om[perturbed_om<0] = 0

        # #rnd_type_cell = np.random.uniform(low=0.9, high=1.1)

        # #perturbed_om = organic * rnd_type_cell
        # #perturbed_om[perturbed_om > 130] = 130
        # #perturbed_om[perturbed_om < 0] = 0
        # #perturbed_om[organic == 0] = 0

        # # Copy non-perturbed variables:
        # for name, var in src.variables.items():
        #     if name != "ORGANIC":
        #         nvar = dst.createVariable(name, var.datatype, var.dimensions)
        #         dst[name].setncatts(src[name].__dict__)
        #         dst[name][:] = src[name][:]

        # om = dst.createVariable("ORGANIC",
        #                         datatype=np.float64,
        #                         dimensions=("nlevsoi", "lsmlat", "lsmlon",),
        #                         fill_value=1.e+30)
        # om.setncatts({'long_name': u"organic matter density at soil levels",
        #               'units': u"kg/m3 (assumed carbon content 0.58 gC per gOM)"})
        # dst.variables["ORGANIC"][:] = perturbed_om
        # #dst.variables["ORGANIC"][:] = organic

        # # Saturated soil matric potential

        # psis_sat = dst.createVariable("PSIS_SAT",
        #                             datatype=np.float64,
        #                             dimensions=("nlevsoi", "lsmlat", "lsmlon",),
        #                             fill_value=1.e+3)
        # psis_sat.setncatts({'long_name': u"Sat. soil matric potential",
        #                         'units': u"mmH20"})

        # sucsat                       = 1.88-0.0131*pct_sand
        # sucsat_std                   = (0.72 - 0.0026 * (100-pct_sand-pct_clay) + 0.0012*pct_clay)/10
        # random_value                 = np.random.normal(loc=0.0, scale=1)
        # noise_sucsat                 = sucsat_std * random_value
        # perturbed_log_sucsat         = 10*(10**(sucsat+noise_sucsat))
        # back_transformed_sucsat      = np.clip(perturbed_log_sucsat,0,1000)
        # dst.variables["PSIS_SAT"][:] = back_transformed_sucsat

        # # Porosity
        # thetas = dst.createVariable("THETAS",
        #                             datatype=np.float64,
        #                             dimensions=("nlevsoi", "lsmlat", "lsmlon",),
        #                             fill_value=1.e+30)
        # thetas.setncatts({'long_name': u"Porosity",
        #                         'units': u"vol/vol"})
        # watsat                     = 0.489 - 0.00126*pct_sand
        # watsat_std                 = ((7.73-0.073*pct_clay) / 100.0)/10
        # random_value               = np.random.normal(loc=0.0, scale=1)
        # noise_watsat               = watsat_std * random_value
        # # organic matter perturbation has a higher impact, no organic matter in deeper soil layers --> spread in deeper soil layers smaller than in
        # # upper soil layers, we make the perturbation of watsat in deepest soil layer larger
        # perturbed_watsat           = watsat + noise_watsat
        # dst.variables["THETAS"][:] = perturbed_watsat

        # # Shape (b) parameter
        # shape_param = dst.createVariable("SHAPE_PARAM",
        #                             datatype=np.float64,
        #                             dimensions=("nlevsoi", "lsmlat", "lsmlon",),
        #                             fill_value=1.e+30)
        # shape_param.setncatts({'long_name': u"Shape (b) parameter",
        #                         'units': u"unitless"})
        # bsw                              = 2.91 + 0.159*pct_clay
        # bsw_std                          = (0.0500 * pct_clay + 1.34)/10
        # random_value                     = np.random.normal(loc=0.0, scale=1)
        # noise_bsw                        = bsw_std * random_value
        # #noise_bsw[-2:,:,:]               = noise_bsw[-2:,:,:]*1.5
        # perturbed_bsw                    = bsw + noise_bsw
        # perturbed_bsw[perturbed_bsw < 0] = 0
        # dst.variables["SHAPE_PARAM"][:]  = perturbed_bsw

        # # Saturated hydraulic conductivity
        # ks = dst.createVariable("KSAT",
        #                         datatype=np.float64,
        #                         dimensions=("nlevsoi", "lsmlat", "lsmlon",),
        #                         fill_value=1.e+30)
        # ks.setncatts({'long_name': u"Sat. hydraulic conductivity", 'units': u"mm/s"})
        # xksat                    = -0.884+0.0153*pct_sand
        # xksat_std                = (0.459 + 0.00321*(100-(pct_sand+pct_clay)))
        # random_value             = np.random.normal(loc=0.0, scale=1)
        # noise_xksat              = xksat_std * random_value
        # perturbed_log_xksat      = 0.0070566*(10**(xksat+noise_xksat))
        # dst.variables["KSAT"][:] = perturbed_log_xksat

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
        random_value_sucsat = np.random.normal(
            loc=1, scale=0.2
        )  # , size=(pct_sand.shape[1],pct_sand.shape[2]))
        random_value_watsat = np.random.normal(
            loc=1, scale=0.05
        )  # , size=random_value_sucsat.shape)
        random_value_bsw = np.random.normal(
            loc=1, scale=0.1
        )  # , size=random_value_sucsat.shape)
        random_value_hksat = np.random.normal(
            loc=1, scale=0.1
        )  # , size=random_value_sucsat.shape) scale=0.25

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

        for j in range(dim_lvl_p):

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

            dst.variables["PSIS_SAT_adj"][j, :, :] = sucsat * random_value_sucsat

            dst.variables["THETAS_adj"][j, :, :] = np.clip(
                watsat * random_value_watsat, 0, 0.93
            )

            dst.variables["SHAPE_PARAM_adj"][j, :, :] = bsw * random_value_bsw

            dst.variables["KSAT_adj"][j, :, :] = hksat * np.clip(
                random_value_hksat, 0.5, 2
            )  # clip bounds: 0.1, 10


# Settings / parameters
# plotting = False
rnd_state_file = "rnd_state.json"
force_seed = False
# Either seed random number generator or continue with existing state
# if not os.path.isfile(rnd_state_file) or force_seed:
#    np.random.seed(42)
# else:
#    rnd_state_deserialize()

# disturbSandClay(num_ensemble)
for i in range(50, 200):
    SoilParameters(i)
    print("Done with ensemble member " + str(i + 1))
