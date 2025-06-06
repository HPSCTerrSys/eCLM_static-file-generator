import os
import numpy as np
from netCDF4 import Dataset

# === Settings ===

dirname = "/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/"

# Input/output files
fnameraw = os.path.join(dirname, "eclm/static/surfdata_ICON-11_hist_16pfts_Irrig_CMIP6_simyr2000_c230302.nc")
filenamenew = os.path.join(dirname, "eclm/static/surfdata_ICON-11_hist_16pfts_Irrig_CMIP6_simyr2000_c230302_gcvurb-pfsoil_py.nc")
filesoil = "/p/scratch/cslts/poll1/sim/euro-cordex/tsmp2_workflow-engine/dta/geo/eclm/static/test/pct_sand-clay_remapped.nc"
fnamerefext = os.path.join(dirname, "icon/static/external_parameter_icon_europe011_DOM01_tiles.nc")

# Flags
lsoil = True
lhomsoil = False
llc = True
lhomllc = False
lurb = True
l_pftparam = True

# === Soil Processing ===

if lsoil:
    with Dataset(filesoil) as ds:
        pct_clay = ds.variables["PCT_CLAY"][:]
        pct_sand = ds.variables["PCT_SAND"][:]

    if lhomsoil:
        pct_clay_mod = np.full_like(pct_clay, 30)
        pct_sand_mod = np.full_like(pct_sand, 30)
    else:
        pct_clay_mod = np.copy(pct_clay)
        pct_clay_mod[np.isnan(pct_clay_mod)] = 0
        pct_clay_mod[pct_clay_mod > 100] = 100

        pct_sand_mod = np.copy(pct_sand)
        pct_sand_mod[np.isnan(pct_sand_mod)] = 0
        pct_sand_mod[pct_sand_mod > 100] = 100

    if not os.path.exists(filenamenew):
        os.system(f"cp {fnameraw} {filenamenew}")

    with Dataset(filenamenew, "r+") as ds:
        ds.variables["PCT_CLAY"][:] = pct_clay_mod
        ds.variables["PCT_SAND"][:] = pct_sand_mod

    print("Wrote soil characteristics into surface file.")

# SLOPES TO DO

# === Land Cover Processing ===

if llc:
    with Dataset(fnameraw) as ds:
        pct_natveg = ds.variables["PCT_NATVEG"][:]
        pct_crop = ds.variables["PCT_CROP"][:]
        pct_wetland = ds.variables["PCT_WETLAND"][:]
        pct_lake = ds.variables["PCT_LAKE"][:]
        pct_glacier = ds.variables["PCT_GLACIER"][:]
        pct_urban = ds.variables["PCT_URBAN"][:]
        pct_nat_pft = ds.variables["PCT_NAT_PFT"][:]
        pct_cft = ds.variables["PCT_CFT"][:]

    if lhomllc:
        shape_natveg = pct_natveg.shape
        shape_urban = pct_urban.shape
        shape_nat_pft = pct_nat_pft.shape
        shape_cft = pct_cft.shape

        pct_natveg_new = np.full(shape_natveg, 100)
        pct_crop_new = np.zeros(shape_natveg)
        pct_wetland_new = np.zeros(shape_natveg)
        pct_lake_new = np.zeros(shape_natveg)
        pct_glacier_new = np.zeros(shape_natveg)
        pct_urban_new = np.zeros(shape_urban)
        pct_nat_pft_new = np.zeros(shape_nat_pft)
        pct_cft_new = np.zeros(shape_cft)

        pct_nat_pft_new[:, 0] = 100
        pct_cft_new[:, 0] = 100

        # Add saving logic to `filenamenew` here if needed

    else:
        with Dataset(fnamerefext) as ds:
            luclass_ref = ds.variables["LU_CLASS_FRACTION"][:]

        # Initialize arrays
        pct_natveg_new = np.zeros_like(pct_natveg)
        pct_crop_new = np.zeros_like(pct_crop)
        pct_wetland_new = np.zeros_like(pct_wetland)
        pct_lake_new = np.zeros_like(pct_lake)
        pct_glacier_new = np.zeros_like(pct_glacier)
        pct_urban_new = np.zeros_like(pct_urban)
        pct_nat_pft_new = np.zeros_like(pct_nat_pft)
        pct_cft_new = np.zeros_like(pct_cft)

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

    # Initialize the mappings
    gcv09pftmap = [
        [16],                     # 1: irrigated croplands
        [15],                     # 2: rainfed croplands
        [15, 7, 10],             # 3: mosaic cropland (50-70%) - vegetation (20-50%)
        [15, 7, 10],             # 4: mosaic vegetation (50-70%) - cropland (20-50%)
        [5],                     # 5: closed broadleaved evergreen forest
        [6],                     # 6: closed broadleaved deciduous forest
        [7, 14],                 # 7: open broadleaved deciduous forest
        [1],                     # 8: closed needleleaved evergreen forest
        [2],                     # 9: open needleleaved deciduous forest
        [9, 14],                 #10: mixed broadleaved and needleleaved forest
        [10, 13],                #11: mosaic shrubland (50-70%) - grassland (20-50%)
        [10, 13],                #12: mosaic grassland (50-70%) - shrubland (20-50%)
        [10, 13],                #13: closed to open shrubland
        [13],                    #14: closed to open herbaceous vegetation
        [0, 9],                  #15: sparse vegetation
        [0, 7],                  #16: closed to open forest regularly flooded
        [0, 7, 9],               #17: closed forest or shrubland permanently flooded
        [0, 14],                 #18: closed to open grassland regularly flooded
        [17],                    #19: artificial surfaces
        [0],                     #20: bare areas
        [18],                    #21: water bodies
        [19],                    #22: permanent snow and ice
        [0]                      #23: undefined
    ]
    
    gcv09pftwgt = [
        [1],                     # 1: irrigated croplands
        [1],                     # 2: rainfed croplands
        [0.6, 0.2, 0.2],        # 3: mosaic cropland (50-70%) - vegetation (20-50%)
        [0.4, 0.3, 0.3],        # 4: mosaic vegetation (50-70%) - cropland (20-50%)
        [1],                     # 5: closed broadleaved evergreen forest
        [1],                     # 6: closed broadleaved deciduous forest
        [0.8, 0.2],              # 7: open broadleaved deciduous forest
        [1],                     # 8: closed needleleaved evergreen forest
        [1],                     # 9: open needleleaved deciduous forest
        [0.5, 0.5],              #10: mixed broadleaved and needleleaved forest
        [0.65, 0.35],            #11: mosaic shrubland (50-70%) - grassland (20-50%)
        [0.35, 0.65],            #12: mosaic grassland (50-70%) - shrubland (20-50%)
        [0.8, 0.2],              #13: closed to open shrubland
        [1],                     #14: closed to open herbaceous vegetation
        [0.8, 0.2],              #15: sparse vegetation
        [0.15, 0.85],            #16: closed to open forest regularly flooded
        [0.1, 0.45, 0.45],       #17: closed forest or shrubland permanently flooded
        [0.15, 0.85],            #18: closed to open grassland regularly flooded
        [1],                     #19: artificial surfaces
        [1],                     #20: bare areas
        [1],                     #21: water bodies
        [1],                     #22: permanent snow and ice
        [1]                      #23: undefined
    ]
    
    for ii in range(luclass_ref.shape[0]):
#        indgcv = np.nonzero(luclass_ref[ii, :])[0]
###########
####  dimension needs to be changed, further code needs to be ported from r-script
###########
        indgcv = np.where(luclass_ref[:, ii] != 0)[0]
        print(indgcv)
        for igcv in indgcv:
            pftl = gcv09pftmap[igcv]
            wgtl = gcv09pftwgt[igcv]
            for ipft in range(len(pftl)):
                ilupct = 100 * luclass_ref[ii, igcv] * wgtl[ipft]
                pft_id = pftl[ipft]
                
                if pft_id <= 15:
                    pct_natveg_new[ii] += ilupct
                    if pft_id <= len(pct_nat_pft_new[ii]):
                        pct_nat_pft_new[ii, pft_id - 1] += ilupct
                elif pft_id == 16 or pft_id == 17:
                    pct_crop_new[ii] += ilupct
                    crop_type = pft_id - 15
                    if crop_type < pct_cft_new[ii].shape[1]:
                        pct_cft_new[ii, crop_type] += ilupct
                elif pft_id == 18:
                    pct_urban_new[ii, 3] += ilupct
                elif pft_id == 19:
                    pct_wetland_new[ii] += ilupct
                elif pft_id == 20:
                    pct_glacier_new[ii] += ilupct
                    
        # Calculate the total percentage
        total = pct_natveg_new[ii] + pct_crop_new[ii] + pct_wetland_new[ii] + pct_lake_new[ii] + np.sum(pct_urban_new[ii, :]) + pct_glacier_new[ii]
        if total != 100:
            factor = 100 / total
            pct_natveg_new[ii] *= factor
            pct_crop_new[ii] *= factor
            pct_wetland_new[ii] *= factor
            pct_lake_new[ii] *= factor
            pct_urban_new[ii, :] *= factor
            pct_glacier_new[ii] *= factor
            
        # Normalize forest types
        forest_total = np.sum(pct_cft_new[ii, :])
        if forest_total == 0:
            pct_cft_new[ii, 0] = 100
        else:
            pct_cft_new[ii, :] = (pct_cft_new[ii, :] / forest_total) * 100
            
        # Normalize PFTs
        pft_total = np.sum(pct_nat_pft_new[ii, :])
        if pft_total == 0:
            pct_nat_pft_new[ii, 0] = 100
        else:
            pct_nat_pft_new[ii, :] = (pct_nat_pft_new[ii, :] / pft_total) * 100
