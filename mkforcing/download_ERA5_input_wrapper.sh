#!/usr/bin/env bash
# Before using this script CDSAPI has to be configured (see README)
# Needs to be executed at LOGIN node as connection to "outside" is required
set -eo pipefail

# load environment
module load Python

# Settings
start_date="2017-07" # yyyy-mm
end_date="2018-08"   # yyyy-mm + 1
out_dir="cdsapidwn"

# Function to parse input
parse_arguments() {
    for arg in "$@"; do
        key="${arg%%=*}"
        value="${arg#*=}"

        case "$key" in
            start_date) start_date="$value" ;;
            end_date) end_date="$value" ;;
            out_dir) out_dir="$value" ;;
            *) echo "Warning: Unknown parameter: $key" ;;
        esac
    done
}

# Call the function to parse the input arguments
# Users needs to make sure for consistent input
parse_arguments "$@"


# create output directory
mkdir -p $out_dir

# loop over months
current_date=$start_date
while [[ "$current_date" < "$end_date" ]]; do
    echo "Processing month: $current_date"

    year="${current_date%%-*}"
    month="${current_date#*-}"

    # start download script with data request
    ./download_ERA5_input.py $year $month $out_dir

    # Increment the month
    current_date=$(date -I -d "$current_date-01 + 1 month" | cut -d'-' -f1,2)
done
