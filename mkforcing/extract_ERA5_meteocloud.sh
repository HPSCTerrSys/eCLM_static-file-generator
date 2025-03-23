#!/usr/bin/env bash

# load env -> not all CDO are compiled with "-t ecmwf"
# module use $OTHERSTAGES
# ml Stages/2022  NVHPC/22.9  ParaStationMPI/5.5.0-1 CDO/2.0.2

if [ -z "$1" ]
then
   iyear=2017
   echo "Take the default year "$iyear
else
   iyear=$1
   echo "Calculate the year "$iyear
fi

if [ -z "$2" ]
then
   imonth=07
   echo "Take the default month "$imonth
else
   imonth=$(printf %02d $2)
   echo "Calculate the month "$imonth
fi

if [ -z "$3" ]
then
   outdir=${iyear}-${imonth}
   echo "Take the default output directory "$outdir
else
   outdir=$3
   echo "Output directory: "$outdir
fi

cd ${outdir}

for year in ${iyear}
do
for month in ${imonth}
do
days_per_month=$(cal ${month} ${year} | awk 'NF {DAYS = $NF}; END {print DAYS}')
for my_date in $(seq -w 1 ${days_per_month})
do
for time in 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23
do

cdo sellonlatbox,-48,74,20,74 /p/data1/slmet/met_data/ecmwf/era5/grib/${year}/${month}/${year}${month}${my_date}${time}_ml.grb cut_domain_${year}${month}${my_date}${time}.grb

cdo sellevel,137 cut_domain_${year}${month}${my_date}${time}.grb lower_level_${year}${month}${my_date}${time}.grb
#cdo -t ecmwf -f nc4 copy lower_level_${month}${my_date}${time}.grb lower_level_${month}${my_date}${time}.nc
cdo -t ecmwf selname,t,u,v,q lower_level_${year}${month}${my_date}${time}.grb variables_lower_level_${year}${month}${my_date}${time}.grb

done
done
cdo merge  variables_lower_level_${year}*.grb meteocloud_${year}_${month}.grb
rm variables_lower_level_${year}*.grb cut_domain_${year}* lower_level_${year}*
cdo -t ecmwf -f nc4 copy meteocloud_${year}_${month}.grb meteocloud_${year}_${month}.nc
done
done
