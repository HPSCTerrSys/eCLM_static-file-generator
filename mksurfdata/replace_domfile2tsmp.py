import os
import numpy as np
from netCDF4 import Dataset

## Settings (needs to be modified by user)
dirname = "/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/"

# Reference eCLM domain file
fnameraw = os.path.join(dirname, "eclm/static/domain.lnd.ICON-11_ICON-11.230302.nc")

# New/Modified eCLM domain file
fnamenew = os.path.join(dirname, "eclm/static/domain.lnd.ICON-11_ICON-11.230302_landlake_py.nc")

# Reference files (ICON grid and external parameters)
l_hom = False  # all grid points active (reference needed)
fnameref = os.path.join(dirname, "icon/static/europe011_DOM01.nc")
fnamerefext = os.path.join(dirname, "icon/static/external_parameter_icon_europe011_DOM01_tiles.nc")

# Remove lake soil type from ICON
l_rm_iconlake = False
fnamenewext = os.path.join(dirname, "icon/static/external_parameter_icon_europe011_DOM01_tiles_nolakes.nc")

# OASIS mask
l_oas_mask = False
fnameoasmask = os.path.join(dirname, "oasis/static/masks_lakes_rev.nc")

## Program start

# Constants
r_earth = 6371000  # can vary with lon/lat

# Read in actual grid
with Dataset(fnameraw, "r") as ff:
    mask_raw = ff.variables["mask"][:]
    frac_raw = ff.variables["frac"][:]
    area_raw = ff.variables["area"][:]
    lonc_raw = ff.variables["xc"][:]
    lonv_raw = ff.variables["xv"][:]

if l_hom:
    # All land
    mask_new = np.ones_like(mask_raw, dtype=np.float32)
    frac_new = np.ones_like(frac_raw, dtype=np.float32)
else:
    # Read reference files
    with Dataset(fnameref, "r") as ff:
        area_ref = ff.variables["cell_area"][:]
    
    with Dataset(fnamerefext, "r") as ff:
        frland_ref = ff.variables["FR_LAND"][:]
        frlake_ref = ff.variables["FR_LAKE"][:]
        soiltyp_ref = ff.variables["SOILTYP"][:]
        luclass_ref = ff.variables["LU_CLASS_FRACTION"][:]

    mask_new = np.ones_like(mask_raw, dtype=np.float32)
    frac_new = np.ones_like(frac_raw, dtype=np.float32)

    # Calculate new mask
    frland_new = frland_ref + frlake_ref
    # Calculate new mask
    frland_new = frland_ref + frlake_ref
    water_mask = (frland_new < 0.5).astype(bool)

    # Ensure mask_new and frac_new are 2D arrays
    if mask_new.ndim == 2 and water_mask.ndim == 2:
        mask_new[water_mask] = 0.0
        frac_new[water_mask] = 0.0
    else:
        # If dimensions don't match, reshape the mask
        water_mask = water_mask.reshape(mask_new.shape)
        mask_new[water_mask] = 0.0
        frac_new[water_mask] = 0.0

# Remove lake soil type from ICON if required
if l_rm_iconlake:
    soiltyp_new = soiltyp_ref.copy()
    luclass_new = luclass_ref.copy()

    # Change lake points to sandy soil
    ind_frland = np.where(frland_new >= 0.5)
    for idx in range(len(ind_frland[0])):
        i, j = ind_frland[0][idx], ind_frland[1][idx]
        if soiltyp_ref[i, j] in (8, 9):
            soiltyp_new[i, j] = 3

    # Adjust LU_CLASS_FRACTION
    ind_frlake = np.where(frlake_ref > 0.)
    for idx in range(len(ind_frlake[0])):
        i, j = ind_frlake[0][idx], ind_frlake[1][idx]
        luclass_new[i, j, 21] -= frlake_ref[i, j]
        luclass_new[i, j, 4] += frlake_ref[i, j]

# Transform all negative longitudes
lonc_new = lonc_raw.copy()
lonc_new[lonc_new < 0] += 360
lonv_new = lonv_raw.copy()
lonv_new[lonv_new < 0] += 360

# Transform to radians
area_new = area_ref / r_earth

# Prepare variables for output
frlake_new = np.zeros_like(frlake_ref)

# Overwrite eCLM grid
if not os.path.exists(fnamenew):
    os.system(f"cp {fnameraw} {fnamenew}")

with Dataset(fnamenew, "r+") as ff:
    ff.variables["mask"][:] = mask_new
    ff.variables["frac"][:] = frac_new
    ff.variables["area"][:] = area_new
    ff.variables["xc"][:] = lonc_new
    ff.variables["xv"][:] = lonv_new

print(f"Written new CLM domain file: {fnamenew}")

# Overwrite ICON external parameters if required
if l_rm_iconlake and not os.path.exists(fnamenewext):
    os.system(f"cp {fnamerefext} {fnamenewext}")

    with Dataset(fnamenewext, "r+") as ff:
        ff.variables["FR_LAKE"][:] = frlake_new
        ff.variables["SOILTYP"][:] = soiltyp_new
        ff.variables["LU_CLASS_FRACTION"][:] = luclass_new

    print(f"Written new ICON external parameter: {fnamenewext}")

# Rewrite mask for OASIS if required
if l_oas_mask:
    mask_oas = np.zeros_like(mask_raw)
    mask_oas[mask_new == 0] = 1  # Inverse mask

    with Dataset(fnameoasmask, "r+") as ff:
        ff.variables["gclm.msk"][:] = mask_oas

print("Process completed successfully")
