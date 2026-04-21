## Program to modify CLM5/eCLM topography file
##
##

## Load libs
require(ncdf4)

########
## Settings
########

dirname <- "/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/"

# Reference eCLM domainfile 
#fnameraw <- paste0(dirname,"eclm/static/topo/topodata_0.9x1.25_USGS_070110_stream_c151201.nc")
fnameraw <- paste0(dirname,"eclm/static/topo/topodata_dummy.nc") # created with ncgen based on topofile above

# New/Modified eCLM domainfile
fnamenew <- paste0(dirname,"eclm/static/topo/topodata_ICON-aster_stream_c250101.nc")

# Reference files (ICON grid and external parameter)
fnameref <- paste0(dirname,"icon/static/europe011_DOM01.nc")
fnamerefext <-  paste0(dirname,"icon/static/external_parameter_icon_europe011_DOM01_tiles.nc")

########
## Start of Program
########

## Read in actual topo
ff <- nc_open(fnameraw)
mask_raw <- ncvar_get(ff,"mask")
topo_raw <- ncvar_get(ff,"TOPO")
nc_close(ff)

## Read in ICON grid file
ff <- nc_open(fnameref)
area_ref <- ncvar_get(ff,"cell_area")
nc_close(ff)

## Read in ICON external file
ff <- nc_open(fnamerefext)
# frland_ref <- ncvar_get(ff,"FR_LAND")
# frlake_ref <- ncvar_get(ff,"FR_LAKE")
lonc_ref <- ncvar_get(ff,"clon")
latc_ref <- ncvar_get(ff,"clat")
topo_ref <- ncvar_get(ff,"topography_c")
nc_close(ff)

#
mask_new <- array(1,dim(mask_raw))

# 
if (length(topo_raw) != length(topo_ref)){ warning("Topography fields do not match!") }

## Overwrite eCLM topo

if (!file.exists(fnamenew))
    system(paste0("cp ",fnameraw," ",fnamenew))

filename <- paste0(fnamenew)
ff <- nc_open(filename,write=TRUE)
ncvar_put(ff,"mask",mask_new)
ncvar_put(ff,"area",area_ref)
ncvar_put(ff,"TOPO",topo_ref)
ncvar_put(ff,"LONGXY",lonc_ref)
ncvar_put(ff,"LATIXY",latc_ref)
nc_close(ff)

print(paste("Write new CLM topo file ",fnamenew))
