## Program to replace CLM surface file variables with synced
## variables for other components
##

## Load libs
require(ncdf4)

########
## Settings
########

dirname <- "/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/"

# Reference eCLM surface file 
fnameraw <- paste0(dirname,"eclm/static/surfdata_ICON-11_hist_16pfts_Irrig_CMIP6_simyr2000_c230302.nc")
#filenameref <- "/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/eclm/static/surfdata_ICON-11_hist_16pfts_Irrig_CMIP6_simyr2000_c230302.nc"

# New/Modified eCLM surface file
filenamenew <- paste0(dirname,"eclm/static/surfdata_ICON-11_hist_16pfts_Irrig_CMIP6_simyr2000_c230302_gcvurb-pfsoil.nc")

# soil characteristics
lsoil <- T 
lhomsoil <- F
# PCT_Sand-Clay needs to be processed on the ICON grid
# -> currrently interpolated from TSMP1
# cdo -select,name=PCT_CLAY,PCT_SAND /p/scratch/cjjsc39/poll1/sim/DETECT_EUR-11_ECMWF-ERA5_evaluation_r1i1p1_FZJ-COSMO5-01-CLM3-5-0-ParFlow3-12-0_vtest/geo/TSMP_EUR-11/static/clm/surfdata_CLM_EUR-11_TSMP_FZJ-IBG3_CLMPFLDomain_444x432.nc pct_sand-clay.nc
# cdo remap,/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/oasis/static-ressources/clm_grid_masked.txt,/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/oasis/static-ressources/nn/rmp_gpfl_to_gclm_DISTWGT.nc -setgrid,/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/oasis/static-ressources/pfl_grid.txt pct_sand-clay.nc pct_sand-clay_remapped.nc
filesoil <- "/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/eclm/static/test/pct_sand-clay_remapped.nc"
#filenamenew <- "/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/eclm/static/surfdata_ICON-11_hist_16pfts_Irrig_CMIP6_simyr2000_c230302_hom.nc"
#filesoil <- "/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/eclm/static/test/pct_sand-clay_remapped.nc"

# land cover
llc <- T
lhomllc <- F
fnamerefext <-  paste0(dirname,"icon/static/external_parameter_icon_europe011_DOM01_tiles.nc")
lurb <- T # modify urban parameter

# landuseparameter
l_pftparam = T

########
## Start of Program
########

# read in variables
ff <- nc_open(filesoil)
pct_clay <- ncvar_get(ff,"PCT_CLAY")
pct_sand <- ncvar_get(ff,"PCT_SAND")
nc_close(ff)


###
# Soil Characteristics
###

if (lsoil) {
if (lhomsoil) {
 pct_clay_mod <- array(30,dim(pct_clay))
 pct_sand_mod <- array(30,dim(pct_sand))
} else {
 pct_clay_mod <- pct_clay
 pct_clay_mod[which(is.na(pct_clay))] <- 0
 pct_clay_mod[which(pct_clay > 100)] <- 100
 pct_sand_mod <- pct_sand
 pct_sand_mod[which(is.na(pct_sand))] <- 0
 pct_sand_mod[which(pct_sand > 100)] <- 100
} # lhomsoil

## Save files
# copy files pct_sand_mod <- array(30,dim(pct_sand))

 if (!file.exists(filenamenew))
        system(paste0("cp ",fnameraw," ",filenamenew))

# save new files
 ff <- nc_open(filenamenew,write=TRUE)
 ncvar_put(ff,"PCT_CLAY",pct_clay_mod)
 ncvar_put(ff,"PCT_SAND",pct_sand_mod)
 nc_close(ff)

 print("Wrote soil characteristics into surface-file")

} # lsoil

# Inidicator code snippet ParFlow
# ## ParFlow3
# file="/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/parflow/static/EUR-11_TSMP_FZJ-IBG3_eCLMPFLDomain_444x432_INDICATOR_regridded_rescaled_SoilGrids250-v2017_BGR3_alv.sa"
# filenew="/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/parflow/static/EUR-11_TSMP_FZJ-IBG3_eCLMPFLDomain_444x432_INDICATOR_regridded_rescaled_SoilGrids250-v2017_BGR3_hom.sa"
# indicator_org <- read.table(file, skip = 1)
# indicator_new <- indicator_org
# indicator_new[,1] = 8
# write.table(indicator_new, file=filenew, row.names=FALSE, col.names=TRUE, sep="\n")

###
# SLOPES
###

#TODO

### 
# Land Cover
### 

if (llc) {

 # read in variables
 ff <- nc_open(fnameraw)
 pct_natveg <- ncvar_get(ff,"PCT_NATVEG")
 pct_crop <- ncvar_get(ff,"PCT_CROP")
 pct_wetland <- ncvar_get(ff,"PCT_WETLAND")
 pct_lake <- ncvar_get(ff,"PCT_LAKE")
 pct_glacier <- ncvar_get(ff,"PCT_GLACIER")
 pct_urban <- ncvar_get(ff,"PCT_URBAN")
 pct_nat_pft <- ncvar_get(ff,"PCT_NAT_PFT")
 pct_cft <- ncvar_get(ff,"PCT_CFT")
 nc_close(ff)

# # range check
# print(range(pct_natveg+pct_crop+pct_wetland+pct_lake+pct_urban[,1]+pct_urban[,2]+ pct_urban[,3]+pct_glacier))

 # check
 pct_cft_tmp <- array(NA,c(dim(pct_cft)[2],dim(pct_cft)[1]))
 for (icft in 1:dim(pct_cft)[2]) {
   pct_cft_tmp[icft,] <- pct_cft[,icft]
 }
 pct_nat_pft_tmp <- array(NA,c(dim(pct_nat_pft)[2],dim(pct_nat_pft)[1]))
  for (ipft in 1:dim(pct_nat_pft)[2]) {
   pct_nat_pft_tmp[ipft,] <- pct_nat_pft[,ipft]
 }
# print(range(colSums(pct_cft_tmp)))
# print(range(colSums(pct_nat_pft_tmp)))

 if (lhomllc){
  # initialize
  pct_natveg_new <-  pct_crop_new <- pct_wetland_new <- pct_lake_new <- pct_glacier_new  <- array(NA,dim(pct_natveg))
  pct_urban_new <- array(NA,dim(pct_urban))
  pct_nat_pft_new <- array(NA,dim(pct_nat_pft))
  pct_cft_new <- array(NA,dim(pct_cft))


  # land use
  pct_natveg_new[] <- 100
  pct_crop_new[] <- 0
  pct_wetland_new[] <- 0
  pct_lake_new[] <- 0
  pct_glacier_new[] <- 0
  pct_urban_new[] <- 0
  pct_nat_pft_new[] <- 0
  pct_nat_pft_new[,1] <- 100
  pct_cft_new[,] <- 0
  pct_cft_new[,1] <- 100

## no lake, no urban:
#
# pct_other <- pct_wetland+pct_lake+pct_urban[,,1]+pct_urban[,,2]+ pct_urban[,,3]+pct_glacier
#
#  pct_natveg_new <-  pct_natveg+pct_other
#  pct_crop_new <- pct_crop
#  pct_wetland_new <- pct_lake_new <- pct_glacier_new  <- array(0,dim(pct_natveg))
#  pct_urban_new <- array(0,dim(pct_urban))
#  pct_nat_pft_new <- pct_nat_pft
#  pct_cft_new <- pct_cft

## no lake:
#
#  pct_other <- pct_wetland+pct_lake+pct_glacier
#
#  pct_natveg_new <-  pct_natveg+pct_other
#  pct_wetland_new <- pct_lake_new <- pct_glacier_new  <- array(0,dim(pct_natveg))
#  pct_nat_pft_new <- pct_nat_pft

 } else { # lhomllc

 ff <- nc_open(fnamerefext)
 luclass_ref <- ncvar_get(ff,"LU_CLASS_FRACTION")
 nc_close(ff)

 # initialize with 0, exept pct_natveg
 pct_natveg_new <- pct_crop_new <- pct_wetland_new <- pct_lake_new <- pct_glacier_new  <- array(0,dim(pct_natveg))
 pct_urban_new <- array(0,dim(pct_urban))
 pct_nat_pft_new <- array(0,dim(pct_nat_pft))
 pct_cft_new <- array(0,dim(pct_cft))

# 1 DATA lu_gcv2009_v3 /  0.07_wp,  0.9_wp,  3.3_wp, 1.0_wp, 190.0_wp,  0.72_wp, 1._wp,  30._wp, & ! irrigated croplands
# 2                  &   0.07_wp,  0.9_wp,  3.3_wp, 1.0_wp, 170.0_wp,  0.72_wp, 1._wp,  30._wp, & ! rainfed croplands
# 3                  &   0.25_wp,  0.8_wp,  3.0_wp, 0.5_wp, 160.0_wp,  0.55_wp, 1._wp,  10._wp, & ! mosaic cropland (50-70%) - vegetation (20-50%)
# 4                  &   0.07_wp,  0.9_wp,  3.5_wp, 0.7_wp, 150.0_wp,  0.72_wp, 1._wp,  30._wp, & ! mosaic vegetation (50-70%) - cropland (20-50%)
# 5                  &   1.00_wp,  0.8_wp,  5.0_wp, 1.0_wp, 280.0_wp,  0.38_wp, 1._wp,  50._wp, & ! closed broadleaved evergreen forest
# 6                  &   1.00_wp,  0.9_wp,  6.0_wp, 1.0_wp, 225.0_wp,  0.31_wp, 1._wp,  50._wp, & ! closed broadleaved deciduous forest
# 7                  &   0.15_wp,  0.8_wp,  4.0_wp, 1.5_wp, 225.0_wp,  0.31_wp, 1._wp,  30._wp, & ! open broadleaved deciduous forest
# 8                  &   1.00_wp,  0.8_wp,  5.0_wp, 0.6_wp, 300.0_wp,  0.27_wp, 1._wp,  50._wp, & ! closed needleleaved evergreen forest
# 9                  &   1.00_wp,  0.9_wp,  5.0_wp, 0.6_wp, 300.0_wp,  0.33_wp, 1._wp,  50._wp, & ! open needleleaved deciduous forest
#10                  &   1.00_wp,  0.9_wp,  5.0_wp, 0.8_wp, 270.0_wp,  0.29_wp, 1._wp,  50._wp, & ! mixed broadleaved and needleleaved forest
#11                  &   0.20_wp,  0.8_wp,  2.5_wp, 0.8_wp, 200.0_wp,  0.60_wp, 1._wp,  30._wp, & ! mosaic shrubland (50-70%) - grassland (20-50%)
#12                  &   0.20_wp,  0.8_wp,  2.5_wp, 0.6_wp, 200.0_wp,  0.65_wp, 1._wp,  10._wp, & ! mosaic grassland (50-70%) - shrubland (20-50%)
#13                  &   0.15_wp,  0.8_wp,  2.5_wp, 0.9_wp, 265.0_wp,  0.65_wp, 1._wp,  50._wp, & ! closed to open shrubland
#14                  &   0.03_wp,  0.9_wp,  3.1_wp, 0.4_wp, 140.0_wp,  0.82_wp, 1._wp,  30._wp, & ! closed to open herbaceous vegetation
#15                  &   0.05_wp,  0.5_wp,  0.6_wp, 0.2_wp, 120.0_wp,  0.76_wp, 1._wp,  10._wp, & ! sparse vegetation
#16                  &   1.00_wp,  0.8_wp,  5.0_wp, 1.0_wp, 190.0_wp,  0.30_wp, 1._wp,  50._wp, & ! closed to open forest regulary flooded
#17                  &   1.00_wp,  0.8_wp,  5.0_wp, 1.0_wp, 190.0_wp,  0.30_wp, 1._wp,  50._wp, & ! closed forest or shrubland permanently flooded
#18                  &   0.05_wp,  0.8_wp,  2.0_wp, 0.7_wp, 120.0_wp,  0.76_wp, 1._wp,  30._wp, & ! closed to open grassland regularly flooded
#19                  &   1.00_wp,  0.2_wp,  1.6_wp, 0.2_wp, 300.0_wp,  0.50_wp, 1._wp, 200._wp, & ! artificial surfaces
#20                  &   0.05_wp,  0.05_wp, 0.6_wp,0.05_wp, 300.0_wp,  0.82_wp, 1._wp, 200._wp, & ! bare areas
#21                  &   0.0002_wp,0.0_wp,  0.0_wp, 0.0_wp, 150.0_wp,  -1.0_wp,-1._wp, 200._wp, & ! water bodies
#22                  &   0.01_wp,  0.0_wp,  0.0_wp, 0.0_wp, 120.0_wp,  -1.0_wp, 1._wp, 200._wp, & ! permanent snow and ice
#23                  &   0.00_wp,  0.0_wp,  0.0_wp, 0.0_wp, 250.0_wp,  -1.0_wp,-1._wp, 200._wp  / ! undefined
#

# # CLM5 PFTs 
# 0 	Bare Ground
# 1 	Needleleaf evergreen tree – temperate
# 2 	Needleleaf evergreen tree - boreal
# 3 	Needleleaf deciduous tree – boreal
# 4 	Broadleaf evergreen tree – tropical
# 5 	Broadleaf evergreen tree – temperate
# 6 	Broadleaf deciduous tree – tropical
# 7 	Broadleaf deciduous tree – temperate
# 8 	Broadleaf deciduous tree – boreal
# 9 	Broadleaf evergreen shrub - temperate
# 10 	Broadleaf deciduous shrub – temperate
# 11 	Broadleaf deciduous shrub – boreal
# 12 	C_3 arctic grass
# 13 	C_3 grass
# 14 	C_4 grass

#> (colSums(colSums(pct_urban)))
#[1] 4.280616e+01 1.853037e+05 1.538387e+06

# > unique(urban_region_id_ref)
# [1]  0 12 19 22  5 15 16 32 28 33 11

# globecover2009 to CLM PFT mapping and weights
 gcv09pftmap <- list(
  c(16), # 1  irrigated croplands
  c(15), # 2  rainfed croplands
  c(15,7,10), # 3  mosaic cropland (50-70%) - vegetation (20-50%)
  c(15,7,10), # 4  mosaic vegetation (50-70%) - cropland (20-50%)
  c(5), # 5  closed broadleaved evergreen forest
  c(7), # 6  closed broadleaved deciduous forest
  c(7, 14), # 7  open broadleaved deciduous forest
  c(1), # 8  closed needleleaved evergreen forest
  c(3), # 9  open needleleaved deciduous forest
  c(1,7), #10  mixed broadleaved and needleleaved forest
  c(9,14), #11  mosaic shrubland (50-70%) - grassland (20-50%)
  c(9,14), #12  mosaic grassland (50-70%) - shrubland (20-50%)
  c(9,14), #13  closed to open shrubland
  c(14), #14  closed to open herbaceous vegetation
  c(0,9), #15  sparse vegetation
  c(0,7), #16  closed to open forest regulary flooded
  c(0,7,9), #17  closed forest or shrubland permanently flooded
  c(0,14), #18  closed to open grassland regularly flooded
  c(17), #19  artificial surfaces
  c(0), #20  bare areas
  c(18), #21  water bodies
  c(19), #22  permanent snow and ice
  c(0)) #23  undefined

 gcv09pftwgt <- list(
  c(1), # 1  irrigated croplands
  c(1), # 2  rainfed croplands
  c(0.6,0.2,0.2), # 3  mosaic cropland (50-70%) - vegetation (20-50%)
  c(0.4,0.3,0.3), # 4  mosaic vegetation (50-70%) - cropland (20-50%)
  c(1), # 5  closed broadleaved evergreen forest
  c(1), # 6  closed broadleaved deciduous forest
  c(0.8, 0.2), # 7  open broadleaved deciduous forest
  c(1), # 8  closed needleleaved evergreen forest
  c(1), # 9  open needleleaved deciduous forest
  c(0.5,0.5), #10  mixed broadleaved and needleleaved forest
  c(0.65,0.35), #11  mosaic shrubland (50-70%) - grassland (20-50%)
  c(0.35,0.65), #12  mosaic grassland (50-70%) - shrubland (20-50%)
  c(0.8,0.2), #13  closed to open shrubland
  c(1), #14  closed to open herbaceous vegetation
  c(0.8,0.2), #15  sparse vegetation
  c(0.15,0.85), #16  closed to open forest regulary flooded
  c(0.1,0.45,0.45), #17  closed forest or shrubland permanently flooded
  c(0.15,0.85), #18  closed to open grassland regularly flooded
  c(1), #19  artificial surfaces
  c(1), #20  bare areas
  c(1), #21  water bodies
  c(1), #22  permanent snow and ice
  c(1)) #23  undefined

 for (ii in (1:dim(luclass_ref)[1])){
   indgcv= which(luclass_ref[ii,]!=0)
   for (igcv in (1:length(indgcv))){
    pftl <- gcv09pftmap[[indgcv[igcv]]] + 1 # as list counts from 0
    wgtl <- gcv09pftwgt[[indgcv[igcv]]]
    for (ipft in (1:length(pftl))){
     ilupct <- 100 * luclass_ref[ii,indgcv[igcv]] * wgtl[ipft]
     if (pftl[ipft] <= 15) {
	pct_natveg_new[ii] = pct_natveg_new[ii] + ilupct
        pct_nat_pft_new[ii,pftl[ipft]] = pct_nat_pft_new[ii,pftl[ipft]] + ilupct
     } else if (pftl[ipft] == 16 || pftl[ipft] == 17 ){
	pct_crop_new[ii] = pct_crop_new[ii] + ilupct
        pct_cft_new[ii,pftl[ipft]-15] = pct_cft_new[ii,pftl[ipft]-15] + ilupct
     } else if (pftl[ipft] == 18 ){
        pct_urban_new[ii,3] <- pct_urban_new[ii,3] + ilupct
     } else if (pftl[ipft] == 19 ){
	pct_wetland_new[ii] = pct_wetland_new[ii] + ilupct # might change to lake?
     } else if (pftl[ipft] == 20 ){
	pct_glacier_new[ii] = pct_glacier_new[ii] + ilupct
     } # if ipft
    } # for ipft
   } # for igcv
   # correct sum, if not 100
   tstsum <- (pct_natveg_new[ii]+pct_crop_new[ii]+pct_wetland_new[ii]+pct_lake_new[ii]+sum(pct_urban_new[ii,])+pct_glacier_new[ii])
   if (tstsum!=100){
     fac <- 100/tstsum
     pct_natveg_new[ii] = pct_natveg_new[ii] * fac
     pct_crop_new[ii] = pct_crop_new[ii] * fac
     pct_wetland_new[ii] = pct_wetland_new[ii] * fac
     pct_lake_new[ii] = pct_lake_new[ii] * fac
     pct_urban_new[ii,] = pct_urban_new[ii,] * fac
     pct_glacier_new[ii] = pct_glacier_new[ii] *fac
   } # if tstsum
   isumcft <- sum(pct_cft_new[ii,])
   if (isumcft == 0){
     pct_cft_new[ii,1] <- 100
   } else {
     pct_cft_new[ii,] <- pct_cft_new[ii,]/isumcft*100
   } # if sumcft
   isumpft <- sum(pct_nat_pft_new[ii,])
   if (isumpft == 0){
     pct_nat_pft_new[ii,1] <- 100
   } else {
     pct_nat_pft_new[ii,] <- pct_nat_pft_new[ii,]/isumpft*100
   } # if sumpft
 } # for ii

 # range check
 print(paste0("Rangecheck landunits: ",range(pct_natveg_new+pct_crop_new+pct_wetland_new+pct_lake_new+pct_urban_new[,1]+pct_urban_new[,2]+ pct_urban_new[,3]+pct_glacier_new)))

# take lai from reference
# code from ICON
#  ext_data%atm%laifac_t(jc,jb,jt) = &
#            (wfac*ext_data%atm%laimax_lcc(ilu) + (1._wp-wfac)*laimin(ilu))/MAX(0.01_wp,ext_data%atm%laimax_lcc(ilu))
# lai_min_terra =  c(0.5, 0.5, 0.7, 0.7, 5.0, 0.5, 0.5, 3.0, 1.5, 1.5, 1.0, 1.0, 1.5, 1.0, 0.3, 5.0, 5.0, 1.0, 1.0, 0.2, 0.0, 0.0, 0.0)
 if (l_pftparam) {
  print("replace pft parameter (can take time)")
  # read in variables
  ff <- nc_open(fnameraw)
  monthly_lai <- ncvar_get(ff,"MONTHLY_LAI")
  monthly_sai <- ncvar_get(ff,"MONTHLY_SAI")
  monthly_hgt_top <- ncvar_get(ff,"MONTHLY_HEIGHT_TOP")
  monthly_hgt_bot <- ncvar_get(ff,"MONTHLY_HEIGHT_BOT")
  nc_close(ff)
#
  # replace zeros with meaningful values
  # unfortunately the pct_natveg is not meaningful in reference
  # if meaningful rewrite this function
  pft_replacezeros <- function(var) {
    var_new <- var
    var_new[which(var==0)] <- NA
    var_new[,1,] <- 0 # bare soil
    # need improvement
    meanvar <- array(NA,dim(var_new)[2:3])
    for (ipft in 2:dim(var_new)[2]){
     meanvar[ipft,] <- colMeans(var_new[,ipft,],na.rm=T)
     for (ii in 1:dim(var_new)[1]){
      ind_var <- which(is.na(var_new[ii,ipft,]))
      if (length(ind_var)!=0){
	var_new[ii,ipft,] <- meanvar[ipft,]
      }
     } # for ii
    } # for ipft
#    ind_var <- which(is.na(var_new), arr.ind =T)
    return(var_new)
  } # function

  monthly_lai_new <- pft_replacezeros(monthly_lai)
  monthly_sai_new <- pft_replacezeros(monthly_sai)
  monthly_hgt_top_new <- pft_replacezeros(monthly_hgt_top)
  monthly_hgt_bot_new <- pft_replacezeros(monthly_hgt_bot)

  ff <- nc_open(filenamenew,write=TRUE)
  buffer <- ncvar_put(ff,"MONTHLY_LAI",monthly_lai_new)
  buffer <- ncvar_put(ff,"MONTHLY_SAI",monthly_sai_new)
  buffer <- ncvar_put(ff,"MONTHLY_HEIGHT_TOP",monthly_hgt_top_new)
  buffer <- ncvar_put(ff,"MONTHLY_HEIGHT_BOT",monthly_hgt_bot_new)
  nc_close(ff)

 } # l_pftparam

 #
 if (lurb){
  print("replace urban parameter")
  ff <- nc_open(fnameraw)
  urban_region_id_ref <- ncvar_get(ff,"URBAN_REGION_ID")
  thick_roof_ref <- ncvar_get(ff,"THICK_ROOF")
  thick_wall_ref <- ncvar_get(ff,"THICK_WALL")
  wtroad_perv_ref <- ncvar_get(ff,"WTROAD_PERV")
  alb_improad_dir_ref <- ncvar_get(ff,"ALB_IMPROAD_DIR")
  alb_improad_dif_ref <- ncvar_get(ff,"ALB_IMPROAD_DIF")
  alb_perroad_dir_ref <- ncvar_get(ff,"ALB_PERROAD_DIR")
  alb_perroad_dif_ref <- ncvar_get(ff,"ALB_PERROAD_DIF")
  alb_wall_dif_ref <- ncvar_get(ff,"ALB_WALL_DIF")
  tk_roof_ref <- ncvar_get(ff,"TK_ROOF")
  tk_wall_ref <- ncvar_get(ff,"TK_WALL")
  cv_roof_ref <- ncvar_get(ff,"CV_ROOF")
  ht_roof_ref <- ncvar_get(ff,"HT_ROOF")
  canyon_hwr_ref <- ncvar_get(ff,"CANYON_HWR")
  em_improad_ref <- ncvar_get(ff,"EM_IMPROAD")
  em_perroad_ref <- ncvar_get(ff,"EM_PERROAD")
  em_roof_ref <- ncvar_get(ff,"EM_ROOF")
  em_wall_ref <- ncvar_get(ff,"EM_WALL")
  t_building_min_ref <- ncvar_get(ff,"T_BUILDING_MIN")
  wind_hgt_canyon_ref <- ncvar_get(ff,"WIND_HGT_CANYON")
  alb_roof_dir_ref <- ncvar_get(ff,"ALB_ROOF_DIR")
  cv_wall_ref <- ncvar_get(ff,"CV_WALL")
  alb_roof_dir_ref <- ncvar_get(ff,"ALB_ROOF_DIR")
  alb_roof_dif_ref <- ncvar_get(ff,"ALB_ROOF_DIF")
  alb_wall_dir_ref <- ncvar_get(ff,"ALB_WALL_DIR")
  alb_wall_dif_ref <- ncvar_get(ff,"ALB_WALL_DIF")
  wtlunit_roof_ref <- ncvar_get(ff,"WTLUNIT_ROOF")
  nc_close(ff)

  urban_region_id_mod <- urban_region_id_ref
  urban_region_id_mod[which(urban_region_id_ref==0)] <- 1 # check urbanid

  # calculate median of every column
  medianarrN0 <- function(var) {
    if (length(dim(var))==1) {
      return(array(median(var[which(var!=0)]),dim(var)))
    } else if (length(dim(var))==2){
      tmp <- array(NA,dim(var))
      for (ii in 1:dim(var)[2]){
	tmp[,ii] = median(var[which(var[,ii]!=0),ii])
      } # for ii
      return(tmp)
    } else {
      tmp <- array(NA,dim(var))
      for (ii in 1:dim(var)[2]){
       for (jj in 1:dim(var)[3]){
        tmp[,ii,jj] = median(var[which(var[,ii,jj]!=0),ii,jj])
       } # for jj
      } # for ii
      return(tmp)
    } # if dim
  } # function

  thick_roof_mod <- medianarrN0(thick_roof_ref)
  thick_wall_mod <- medianarrN0(thick_wall_ref)
  wtroad_perv_mod <- medianarrN0(wtroad_perv_ref)
  alb_improad_dir_mod <- medianarrN0(alb_improad_dir_ref)
  alb_improad_dif_mod <- medianarrN0(alb_improad_dif_ref)
  alb_perroad_dir_mod <- medianarrN0(alb_perroad_dir_ref)
  alb_perroad_dif_mod <- medianarrN0(alb_perroad_dif_ref)
  alb_wall_dif_mod <- medianarrN0(alb_wall_dif_ref)
  tk_roof_mod <- medianarrN0(tk_roof_ref)
  tk_wall_mod <- medianarrN0(tk_wall_ref)
  cv_roof_mod <- medianarrN0(cv_roof_ref)
  ht_roof_mod <- medianarrN0(ht_roof_ref)
  canyon_hwr_mod <- medianarrN0(canyon_hwr_ref)
  em_improad_mod <- medianarrN0(em_improad_ref)
  em_perroad_mod <- medianarrN0(em_perroad_ref)
  em_roof_mod <- medianarrN0(em_roof_ref)
  em_wall_mod <- medianarrN0(em_wall_ref)
  t_building_min_mod <- medianarrN0(t_building_min_ref)
  wind_hgt_canyon_mod <- medianarrN0(wind_hgt_canyon_ref)
  alb_roof_dir_mod <- medianarrN0(alb_roof_dir_ref)
  cv_wall_mod <- medianarrN0(cv_wall_ref)
  alb_roof_dir_mod <- medianarrN0(alb_roof_dir_ref)
  alb_roof_dif_mod <- medianarrN0(alb_roof_dif_ref)
  alb_wall_dir_mod <- medianarrN0(alb_wall_dir_ref)
  alb_wall_dif_mod <- medianarrN0(alb_wall_dif_ref)
  wtlunit_roof_mod <- medianarrN0(wtlunit_roof_ref)

  ff <- nc_open(filenamenew,write=TRUE)
  buffer <- ncvar_put(ff,"URBAN_REGION_ID",urban_region_id_mod)
  buffer <- ncvar_put(ff,"THICK_ROOF",thick_roof_mod)
  buffer <- ncvar_put(ff,"THICK_WALL",thick_wall_mod)
  buffer <- ncvar_put(ff,"WTROAD_PERV",wtroad_perv_mod)
  buffer <- ncvar_put(ff,"ALB_IMPROAD_DIR",alb_improad_dir_mod)
  buffer <- ncvar_put(ff,"ALB_IMPROAD_DIF",alb_improad_dif_mod)
  buffer <- ncvar_put(ff,"ALB_PERROAD_DIR",alb_perroad_dir_mod)
  buffer <- ncvar_put(ff,"ALB_PERROAD_DIF",alb_perroad_dif_mod)
  buffer <- ncvar_put(ff,"ALB_WALL_DIF",alb_wall_dif_mod)
  buffer <- ncvar_put(ff,"TK_ROOF",tk_roof_mod)
  buffer <- ncvar_put(ff,"TK_WALL",tk_wall_mod)
  buffer <- ncvar_put(ff,"CV_ROOF",cv_roof_mod)
  buffer <- ncvar_put(ff,"HT_ROOF",ht_roof_mod)
  buffer <- ncvar_put(ff,"CANYON_HWR",canyon_hwr_mod)
  buffer <- ncvar_put(ff,"EM_IMPROAD",em_improad_mod)
  buffer <- ncvar_put(ff,"EM_PERROAD",em_perroad_mod)
  buffer <- ncvar_put(ff,"EM_ROOF",em_roof_mod)
  buffer <- ncvar_put(ff,"EM_WALL",em_wall_mod)
  buffer <- ncvar_put(ff,"T_BUILDING_MIN",t_building_min_mod)
  buffer <- ncvar_put(ff,"WIND_HGT_CANYON",wind_hgt_canyon_mod)
  buffer <- ncvar_put(ff,"ALB_ROOF_DIR",alb_roof_dir_mod)
  buffer <- ncvar_put(ff,"CV_WALL",cv_wall_mod)
  buffer <- ncvar_put(ff,"ALB_ROOF_DIR",alb_roof_dir_mod)
  buffer <- ncvar_put(ff,"ALB_ROOF_DIF",alb_roof_dif_mod)
  buffer <- ncvar_put(ff,"ALB_WALL_DIR",alb_wall_dir_mod)
  buffer <- ncvar_put(ff,"ALB_WALL_DIF",alb_wall_dif_mod)
  buffer <- ncvar_put(ff,"WTLUNIT_ROOF",wtlunit_roof_mod)
  nc_close(ff)

  print("Wrote urban parameter into surface-file")

 } # if lurb

 } # lhomllc

 ## Save files
 # copy files
 if (!file.exists(filenamenew))
        system(paste0("cp ",fnameraw," ",filenamenew))

 # save new files
 ff <- nc_open(filenamenew,write=TRUE)
 buffer <- ncvar_put(ff,"PCT_NATVEG",pct_natveg_new)
 buffer <- ncvar_put(ff,"PCT_CROP",pct_crop_new)
 buffer <- ncvar_put(ff,"PCT_WETLAND",pct_wetland_new)
 buffer <- ncvar_put(ff,"PCT_LAKE",pct_lake_new)
 buffer <- ncvar_put(ff,"PCT_GLACIER",pct_glacier_new)
 buffer <- ncvar_put(ff,"PCT_URBAN",pct_urban_new)
 buffer <- ncvar_put(ff,"PCT_NAT_PFT",pct_nat_pft_new)
 buffer <- ncvar_put(ff,"PCT_CFT",pct_cft_new)
 nc_close(ff)

 print("Wrote land cover into surface-file")

} # llc
