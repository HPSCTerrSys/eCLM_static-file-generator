import xarray as xr
import numpy as np
import sys

file_clm5 = "/p/project1/cjibg36/jibg3674/eCLM_static-file-generator/surfdata_EUR-11_hist_78pfts_CMIP6_simyr2005_c251022.nc"
file_glc2000 = "/p/project1/cjibg36/jibg3674/TSMP_EUR-11/static.resource/08_LandCover/GLC2000_PFT_urban.nc"
file_clm = "/p/project/cjibg36/jibg3674/shared_DA/setup_eclm_cordex_444x432_v9/input_clm/surfdata_EUR-11_hist_16pfts_Irrig_CMIP6_simyr2000_c230808_GLC2000.nc"
file_dest = "/p/project/cjibg36/jibg3674/shared_DA/setup_eclm_cordex_444x432_v9/input_clm/surfdata_EUR-11_hist_78pfts_CMIP6_simyr2005_c251022_GLC2000.nc"

open_clm5 = xr.open_dataset(file_clm5)
open_glc2000 = xr.open_dataset(file_glc2000)
open_clm = xr.open_dataset(file_clm)

# print(open_clm5["PCT_CLAY"].dims, open_clm["PCT_CLAY"].dims)
# print(open_clm5["PCT_CLAY"].shape, open_clm["PCT_CLAY"].shape)

open_clm5['PCT_CLAY'][:] = open_clm['PCT_CLAY'].values
open_clm5['PCT_SAND'][:] = open_clm['PCT_SAND'].values
open_clm5['ORGANIC'][:]  = open_clm['ORGANIC'].values

open_clm5["PCT_WETLAND"][:] = 0
open_clm5['PCT_URBAN'][2,:,:] = open_glc2000['PCT_PFT'][19,:,:].values
open_clm5['PCT_URBAN'][1,:,:] = 0
open_clm5['PCT_GLACIER'][:,:] = open_glc2000['PCT_PFT'][18,:,:].values
open_clm5['PCT_LAKE'][:,:] = open_glc2000['PCT_PFT'][17,:,:].values

open_clm5["PCT_CROP"][:, :] = open_glc2000["PCT_PFT"][15, :, :].values
open_clm5["PCT_NATVEG"][:, :] = np.sum(open_glc2000["PCT_PFT"][0:15, :, :].values, axis=0)
open_clm5["PCT_NAT_PFT"][0:15, :, :] = open_glc2000["PCT_PFT"][0:15, :, :].values

sum_patch = (
    open_clm5["PCT_NATVEG"].values
    + open_clm5["PCT_CROP"].values
    + np.sum(open_clm5["PCT_URBAN"].values, axis=0)
    + open_clm5["PCT_LAKE"].values
    + open_clm5["PCT_GLACIER"].values)
print("Min sum_patch:", np.nanmin(sum_patch))
print("Max sum_patch:", np.nanmax(sum_patch))

# Compute scaling factor, with safety margin
scale = np.where(sum_patch > 0, 100 / sum_patch, 1.0)
for v in ["PCT_NATVEG", "PCT_CROP", "PCT_LAKE", "PCT_GLACIER", "PCT_URBAN"]:
    open_clm5[v].values *= scale
print("New sum_patch (min, max):", np.nanmin(sum_patch * scale), np.nanmax(sum_patch * scale))


pctspec = (
    open_clm5["PCT_LAKE"].values +
    open_clm5["PCT_WETLAND"].values +
    open_clm5["PCT_GLACIER"].values +
    np.sum(open_clm5["PCT_URBAN"].values, axis=0)
)
print("Max pctspec:", np.nanmax(pctspec))

natpft = open_clm5["PCT_NAT_PFT"].values  
sum_natpft = np.sum(natpft, axis=0)
sum_crop   = np.sum(open_clm5["PCT_CFT"].values, axis=0) 
print("Min sum_natpft:", np.nanmin(sum_natpft))
print("Max sum_natpft:", np.nanmax(sum_natpft))
print("Min sum_crop:", np.nanmin(sum_crop))
print("Max sum_crop:", np.nanmax(sum_crop))

mask = sum_natpft > 0
natpft[:, mask] = natpft[:, mask] * (100.0 / sum_natpft[mask])
open_clm5["PCT_NAT_PFT"].values = natpft

mask_zero = sum_natpft == 0
open_clm5["PCT_NAT_PFT"].values[0, mask_zero] = 100.0

print("New sum_natpft (min, max):",
      np.nanmin(np.sum(open_clm5["PCT_NAT_PFT"].values, axis=0)),
      np.nanmax(np.sum(open_clm5["PCT_NAT_PFT"].values, axis=0)))

open_clm5.to_netcdf(file_dest)
print(f"Saved modified surfdata to:\n{file_dest}")

open_clm5.close()
open_glc2000.close()
open_clm.close()

