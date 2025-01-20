# Replacement of CLM5 data with CLM3_5 data

The script `replace_clm5_with_clm3_5_data.sh` replaces variables in the CLM5 surfacedataset with data from CLM3_5 given that the data was produced accordingly, including explicit mapping of the urban landcover type and correct CLM5 soil levels.
The changed mapping for CLM3_5 can be found here:
https://icg4geo.icg.kfa-juelich.de/Configurations/TSMP_statfiles_IBG3/TSMP_EUR-0275/-/tree/main/static.resource/08_LandCover

# Replacement of CLM5 data with ICON data

** work in progress, on the long-run to be implemented in the static file generation process **

This section assumes that CLM performs on the icosahedral grid.

For running R-script on JSC machine, load `ml Stages/2025  GCCcore R` in advance, R-package `ncdf4` needs to be installed.

This script unifies the CLM5/eCLM domain file and surface file.

Replacement of domain file:
`replace_domfile2tsmp.r`
This script can be also used to modify the OASIS mask (optional).

Replacement of surface file:
`replace_surffile2tsmp.r`

Replacement of topography file:
`replace_topo2tsmp.r`

Usage:
`Rscript <script.r>`
