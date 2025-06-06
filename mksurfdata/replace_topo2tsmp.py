# Program to modify CLM5/eCLM topography file 
import os
import shutil
import netCDF4 as nc

## Settings (Users needs to modify paths)
dirname = "/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/"

# Reference eCLM domainfile
fnameraw = os.path.join(dirname, "eclm/static/topo/topodata_dummy.nc")

# New/Modified eCLM domainfile
fnamenew = os.path.join(dirname, "eclm/static/topo/topodata_ICON-aster_stream_c250101.nc")

# Reference files (ICON grid and external parameter)
fnameref = os.path.join(dirname, "icon/static/europe011_DOM01.nc")
fnamerefext = os.path.join(dirname, "icon/static/external_parameter_icon_europe011_DOM01_tiles.nc")

## Program start

# Read in actual topo
with nc.Dataset(fnameraw, 'r') as ff:
    mask_raw = ff.variables['mask'][:]
    topo_raw = ff.variables['TOPO'][:]

# Read in ICON grid file
with nc.Dataset(fnameref, 'r') as ff:
    area_ref = ff.variables['cell_area'][:]

# Read in ICON external file
with nc.Dataset(fnamerefext, 'r') as ff:
    lonc_ref = ff.variables['clon'][:]
    latc_ref = ff.variables['clat'][:]
    topo_ref = ff.variables['topography_c'][:]

# Create new mask
mask_new = nc.num2griddef(mask_raw.shape, 1)

# Overwrite eCLM topo
if not os.path.exists(fnamenew):
    shutil.copy(fnameraw, fnamenew)

# Open the new file for writing
with nc.Dataset(fnamenew, 'a') as ff:
    # Update variables
    ff.variables['mask'][:] = mask_new
    ff.variables['area'][:] = area_ref
    ff.variables['TOPO'][:] = topo_ref
    ff.variables['LONGXY'][:] = lonc_ref
    ff.variables['LATIXY'][:] = latc_ref

print(f"Written new CLM topo file: {fnamenew}")
