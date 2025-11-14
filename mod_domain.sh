#!/usr/bin/env bash

surface_file="/p/project1/cjibg36/jibg3674/eCLM_static-file-generator/mksurfdata/surfdata_EUR-11_hist_78pfts_CMIP6_simyr2005_c251022.nc"
# domain_file=domain.nc
# landmask_file=landmask.nc

ncap2 -O -s 'where(LONGXY<0) LONGXY=LONGXY+360' ${surface_file} temp.nc
# mv temp.nc ${surface_file}

# ncap2 -O -s 'where(xc<0) xc=xc+360' ${domain_file} temp.nc
# ncap2 -O -s 'where(xv<0) xv=xv+360' temp.nc ${domain_file}
# 
# ncrename -v LANDMASK,mask -v FRAC,frac ${landmask_file}
# ncks -A -v mask ${landmask_file} ${domain_file}
# ncks -A -v frac ${landmask_file} ${domain_file}
