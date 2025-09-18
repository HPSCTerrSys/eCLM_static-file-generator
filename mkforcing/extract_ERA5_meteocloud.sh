#!/usr/bin/env bash
set -o pipefail

# load env -> not all CDO are compiled with "-t ecmwf"
# module use $OTHERSTAGES
# ml Stages/2022  NVHPC/22.9  ParaStationMPI/5.5.0-1 CDO/2.0.2

function message(){
if [ -z "${quiet}" ];then
  echo "$1"
fi # quiet
}

# default values of parameters
iyear=2017
imonth=07
ihour=(00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23)
outdir=${iyear}-${imonth}
runpp=1
area=(-48 74 20 74)

# Function to parse input
parse_arguments() {
    for arg in "$@"; do
        key="${arg%%=*}"
        value="${arg#*=}"

        case "$key" in
            quiet) quiet=y;;
            iyear) iyear="$value" ;;
            imonth) imonth="$value" ;;
            ihour) ihour="$value" ;;
            outdir) outdir="$value" ;;
            runpp) runpp="$value" ;;
            area) area="$value" ;;
            *) echo "Warning: Unknown parameter: $key" ;;
        esac
    done
}

# Call the function to parse the input arguments
# Users needs to make sure for consistent input
parse_arguments "$@"

message "=========================="
message "Year: "$iyear
message "Month: "$imonth
message "Hours: "$ihour
message "Selected area W: "${area[0]}
message "Selected area E: "${area[1]}
message "Selected area S: "${area[2]}
message "Selected area N: "${area[3]}
message "Output directory: "$outdir
message "Max running procs: "$runpp
message "=========================="

cd ${outdir}

# start a counter for background jobs
running_jobs=0

for year in ${iyear}
do
for month in ${imonth}
do
days_per_month=$(cal ${month} ${year} | awk 'NF {DAYS = $NF}; END {print DAYS}')
for day in $(seq -w 1 ${days_per_month})
do
for hour in "${ihour[@]}"
do

# increment the running job counter
running_jobs=$((running_jobs+1))

message "Process "$year"-"$month"-"$day"-"$hour" prun: "$running_jobs

# select domain area
cdo sellonlatbox,${area[0]},${area[1]},${area[2]},${area[3]} /p/data1/slmet/met_data/ecmwf/era5/grib/${year}/${month}/${year}${month}${day}${hour}_ml.grb cut_domain_${year}${month}${day}${hour}.grb
# select lowermost model level
cdo sellevel,137 cut_domain_${year}${month}${day}${hour}.grb lower_level_${year}${month}${day}${hour}.grb
# select temperature, horizontal wind speed, humidity
cdo -t ecmwf selname,t,u,v,q lower_level_${year}${month}${day}${hour}.grb variables_lower_level_${year}${month}${day}${hour}.grb

# if the max number of parallel tasks is reached, wait for a job to finish
if [[ ${running_jobs} -ge ${runpp} ]]; then
   wait -n  # wait for one job to finish before starting another
   running_jobs=$((running_jobs-1))  # decrement the running job counter
fi

done
done

wait

# merge hourly files to monthly
cdo merge  variables_lower_level_${year}*.grb meteocloud_${year}_${month}.grb
# transform from grib to netcdf format
cdo -t ecmwf -f nc4 copy meteocloud_${year}_${month}.grb meteocloud_${year}_${month}.nc

# clean-up
rm variables_lower_level_${year}*.grb cut_domain_${year}* lower_level_${year}*

done
done

