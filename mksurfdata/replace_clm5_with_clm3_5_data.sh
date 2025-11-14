#!/usr/bin/env bash

##This scripts replaces variables in the surface file of CLM5 with variables from a CLM3_5 file. This is easily doable for the variables handeled with nco, the pft-percentages need a special treatment. Because they are splittet into crop and natural pfts in CLM5.
##It is still under discussion whether the soillevels are identical but both CLM versions have 10 levles in the surface file. LAI and other plant parameters can only be replaced like this if there are the same number of them in both datasets. 

CLM_3_5_path=/p/scratch/cslts/hartick1/TSMP_EUR-0275_transform_for_eCLM/TSMP_EUR-11/static.resource/10_GatherCLM35/surfdata_CLM_EUR-11_TSMP_FZJ-IBG3_CLMPFLDomain_1592x1544.nc
#CLM5_path=/p/scratch/cslts/hartick1/temp/work_chris_cut.nc
CLM5_path_cut_pft=/p/scratch/cslts/hartick1/temp/work_chris_cut.nc


#ncks -A -v PCT_SAND,PCT_CLAY,MONTHLY_LAI,MONTHLY_SAI,MONTHLY_HEIGHT_TOP,MONTHLY_HEIGHT_BOT $CLM_3_5_path $CLM5_path
#ncks -d cft,0,1 -d lsmpft,0,16 $CLM5_path $CLM5_path_cut_pft
python replace.py $CLM_3_5_path $CLM5_path_cut_pft



#ncks -A -v PCT_SAND,PCT_CLAY,MONTHLY_LAI,MONTHLY_SAI,MONTHLY_HEIGHT_TOP,MONTHLY_HEIGHT_BOT $CLM_3_5_path $CLM5_path_cut_pft
ncks  -A -v PCT_SAND,PCT_CLAY,PCT_WETLAND,LANDFRAC_PFT,PFTDATA_MASK $CLM_3_5_path $CLM5_path_cut_pft
