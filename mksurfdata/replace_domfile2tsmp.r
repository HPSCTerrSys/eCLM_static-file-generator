## Program to CLM5/eCLM domain file
##
##

## Load libs
require(ncdf4)

########
## Settings
########

dirname <- "/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/"

# Reference eCLM domainfile 
fnameraw <- paste0(dirname,"eclm/static/domain.lnd.ICON-11_ICON-11.230302.nc")
#fnameraw <- "/p/scratch/cslts/poll1/sim/euro-cordex/eur-0275_icon-eclm_testcase/eur-0275_icon-eclm_testcase/geo/static/eclm/domain.lnd.R13B07_R13B07.240419.nc"

# New/Modified eCLM domainfile
fnamenew <- paste0(dirname,"eclm/static/domain.lnd.ICON-11_ICON-11.230302_landlake.nc")
#fnamenew <- "/p/scratch/cslts/poll1/sim/euro-cordex/eur-0275_icon-eclm_testcase/eur-0275_icon-eclm_testcase/geo/static/eclm/domain.lnd.R13B07_R13B07.240419_land.nc"


# Reference files (ICON grid and external pareameter)
l_hom <- F # all grid points active (reference needed)
fnameref <- paste0(dirname,"icon/static/europe011_DOM01.nc")
fnamerefext <-  paste0(dirname,"icon/static/external_parameter_icon_europe011_DOM01_tiles.nc")
#fnameref <- "/p/scratch/cslts/poll1/sim/euro-cordex/eur-0275_icon-eclm_testcase/eur-0275_icon-eclm_testcase/geo/static/icon/EUR-R13B07_2473796_grid_inclbrz_v1.nc"
#fnamerefext <- "/p/scratch/cslts/poll1/sim/euro-cordex/eur-0275_icon-eclm_testcase/eur-0275_icon-eclm_testcase/geo/static/icon/external_parameter_icon_EUR-R13B07_2473796_grid_inclbrz_v1.nc"

# 
l_rm_iconlake <- F
fnamenewext <-  paste0(dirname,"icon/static/external_parameter_icon_europe011_DOM01_tiles_nolakes.nc")
#fnamenewext <- "/p/scratch/cslts/poll1/sim/euro-cordex/eur-0275_icon-eclm_testcase/eur-0275_icon-eclm_testcase/geo/static/icon/external_parameter_icon_EUR-R13B07_2473796_grid_inclbrz_v1_allland.nc"

# 
l_oas_mask <- F
fnameoasmask <-  paste0(dirname,"oasis/static/masks_lakes_rev.nc")
#fnameoasmask <- "/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/oasis/static/masks_lakes_rev.nc"

########
## Start of Program
########

# const
r_earth <- 6371000 # can vary with lon/lat

## Read in actual grid

ff <- nc_open(fnameraw)
mask_raw <- ncvar_get(ff,"mask")
frac_raw <- ncvar_get(ff,"frac")
area_raw <- ncvar_get(ff,"area")
lonc_raw <- ncvar_get(ff,"xc")
lonv_raw <- ncvar_get(ff,"xv")
nc_close(ff)

if (l_hom){

 # all land
 mask_new <- array(1,dim(mask_raw))
 frac_new <- array(1,dim(frac_raw))

} else {

 ##
 ff <- nc_open(fnameref)
 area_ref <- ncvar_get(ff,"cell_area")
 nc_close(ff)

 ff <- nc_open(fnamerefext)
 frland_ref <- ncvar_get(ff,"FR_LAND")
 frlake_ref <- ncvar_get(ff,"FR_LAKE")
 soiltyp_ref <- ncvar_get(ff,"SOILTYP")
 luclass_ref <- ncvar_get(ff,"LU_CLASS_FRACTION")
 nc_close(ff)

 mask_new <- array(1,dim(mask_raw))

 ## Calculate new mask
 mask_new <- frac_new <- array(1,dim(mask_raw))
 frland_new <- frland_ref+frlake_ref
 mask_new[frland_new<0.5] <- 0 # water points but no lakes
 frac_new[frland_new<0.5] <- 0

} # l_hom

## Remove lake soil type from ICON
if (l_rm_iconlake){
 soiltyp_new <- soiltyp_ref
 ind_frland <- which(frland_new>=0.5)
 for (ii in 1:length(ind_frland)){
   if (soiltyp_ref[ind_frland[ii]]==8 | soiltyp_ref[ind_frland[ii]]==9){
     soiltyp_new[ind_frland[ii]] <- 3 # change to sandy soil
   } # if soiltyp
 } # for ii
 luclass_new <- luclass_ref
 #ind_frlake <- which(frlake_ref>=0.5)
 ind_frlake <- which(frlake_ref>0.)
 for (ii in 1:length(ind_frlake)){
   # take water point lu to vegetation
   luclass_new[ind_frlake[ii],21] <- luclass_ref[ind_frlake[ii],21]-frlake_ref[ind_frlake[ii]]
   luclass_new[ind_frlake[ii],4] <- luclass_ref[ind_frlake[ii],4]+frlake_ref[ind_frlake[ii]]
 } # for ii

 # to check LU_CLASS_FRACTION, NDVIRATIO, NDVI_MAX
} # l_rm_iconlake

# transform all negative longitudes
lonc_new <- lonc_raw
lonc_new[lonc_new< 0] = lonc_new[lonc_new< 0]+360
lonv_new <- lonv_raw
lonv_new[lonv_new< 0] = lonv_new[lonv_new< 0]+360

# transform to radian
area_new <- area_ref/r_earth

frlake_new <- array(0,dim(frlake_ref))

## Overwrite eCLM grid

if (!file.exists(fnamenew))
    system(paste0("cp ",fnameraw," ",fnamenew))

filename <- paste0(fnamenew)
ff <- nc_open(filename,write=TRUE)
ncvar_put(ff,"mask",mask_new)
ncvar_put(ff,"frac",frac_new)
ncvar_put(ff,"area",area_new)
ncvar_put(ff,"xc",lonc_new)
ncvar_put(ff,"xv",lonv_new)
nc_close(ff)

print(paste("Write new CLM domain file ",fnamenew))

## Overwrite ICON extpar
if (l_rm_iconlake){
 if (!file.exists(fnamenewext))
    system(paste0("cp ",fnamerefext," ",fnamenewext))

 ff <- nc_open(fnamenewext,write=TRUE)
 ncvar_put(ff,"FR_LAKE",frlake_new)
 ncvar_put(ff,"SOILTYP",soiltyp_new)
 ncvar_put(ff,"LU_CLASS_FRACTION",luclass_new)
 nc_close(ff) 

 print(paste("Write new ICON external parameter",fnamenewext)) 
} # l_rm_iconlake

## rewrite mask.nc
if (l_oas_mask){
 mask_oas <- array(0,dim(mask_raw))
 mask_oas[mask_new==0] <- 1 # inverse mask
 ff <- nc_open(fnameoasmask,write=TRUE)
 ncvar_put(ff,"gclm.msk",mask_oas)
 nc_close(ff)  
} # l_oas_mask
