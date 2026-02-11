# Creating a custom case

By sourcing the provided environment file

```
source jsc.2024_Intel.sh
```

the necessary compilations in this repository can be performed consistently. It also contains the export of necessary paths for netCDF.
If you are on a [JSC](https://www.fz-juelich.de/en/ias/jsc) machine, it will be very useful to set this data path:

```
export CSMDATA="/p/largedata2/detectdata/CentralDB/projects/z04"
```

If not, you'll have to get the relevant raw data at the respective steps and either set `$CSMDATA` to a different path or replace it with your respective local directory.

To create all static files needed to run eCLM, you first need to create a gridfile, then mapping and domain files and only then you can create surface and forcing files.
For this the grid has to be properly defined in one of the following formats:

- SCRIP
- ESMF-Mesh
- CF-convention-file

SCRIP is a very old format not maintained anymore but is still the most effective solution.
ESMF is able to basically handle any netCDF file that follows the CF-conventions version 1.6 and includes lat/lon values and corners.
This means that ESMF mesh files are also able to describe unstructured grids.

**Hint:** Once a static file generation is started, it is best
practice to **not anymore copy or move the repository**. This ensures
tracability of absolute paths, e.g. absolute paths of map files saved
in the domain file as netCDF attributes.

<details>
<summary><strong> Creating a custom case (old)  - Click to expand</strong></summary>

This workflow will guide you through creating your own input datasets at a resolution of your choice for eCLM simulations.

Throughout this process, you will use a range of different scripts to create the necessary files.

```{figure} ../images/Build_custom_input.png
:height: 500px
:name: fig5

Overview of the work flow for the creation of custom surface datasets adapted from the <a href="https://escomp.github.io/ctsm-docs/versions/release-clm5.0/html/users_guide/using-clm-tools/creating-surface-datasets.html#" target="_blank">CLM5.0 User's Guide</a>.
```
<p>

This workflow is based on the following Github repository that contains all the necessary tools: https://github.com/HPSCTerrSys/eCLM_static_file_workflow. It follows the official CLM-workflow but makes a few adaptations. The basis is the clm5.0 release but there might be newer developments in the <a href="https://github.com/ESCOMP/CTSM.git" target="_blank">CTSM</a> and <a href="https://github.com/ESMCI/cime.git" target="_blank">CIME</a> Github repositories. 

To get started, log into the JSC system and clone the repository for instance into your folder in `project1` that you created during the build of eCLM.

```sh
cd /p/project1/projectID/user1 # replace projectID with your compute project and user1 with your username

git clone https://github.com/HPSCTerrSys/eCLM_static_file_workflow.git 
```

Sourcing the environment file that is contained in the repository will load all the required software modules.

```sh
cd eCLM_static_file_workflow/
source jsc.2023_Intel.sh
```
You are now ready to start with the workflow.

```{tableofcontents}
```

</details>

