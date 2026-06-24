import os
import sys
import warnings
import numpy as np
import json
import datetime

try:
    import git
    _GIT_AVAILABLE = True
except ImportError:
    _GIT_AVAILABLE = False

# Helper functions
# ----------------

# Helper function to serialize / deserialize random state with json


def rnd_state_serialize(state_file):
    """Save the current NumPy random state to a JSON file.

    Parameters
    ----------
    state_file : str
        Path to the output JSON file.
    """
    # retrieve the current state of the NumPy random number generator
    tmp_state = np.random.get_state()

    # initialize a tuple to hold the serialized state
    save_state = ()

    # loop over each element of the state
    for i in tmp_state:
        # check if the element is a NumPy array
        if type(i) is np.ndarray:
            # convert the NumPy array to a list and add it to the save_state tuple
            save_state = save_state + (i.tolist(),)
        else:
            # if not, it is added to the save_state tuple as is
            save_state = save_state + (i,)

    # write the serialized state to a JSON file
    json.dump(save_state, open(state_file, "w"))


def rnd_state_deserialize(state_file):
    """
    Restore the NumPy random state from a JSON file written by rnd_state_serialize.

    Parameters
    ----------
    state_file : str
        Path to the JSON file containing the saved random state.
    """
    # read the serialized state from the "rnd_state.json" file
    tmp_state = json.load(open(state_file, "r"))

    # initialize a tuple to hold the deserialized state
    load_state = ()

    # loop over each element of the serialized state
    for i in tmp_state:
        # check if the element is a list
        if type(i) is list:
            # convert the list to a NumPy array and add it to the load_state tuple
            load_state = load_state + (np.array(i),)
        else:
            # if not, it is added to the load_state tuple as is
            load_state = load_state + (i,)

    # set the state of the NumPy random number generator to the deserialized state.
    np.random.set_state(load_state)


# Helper function - copy attributes and dimensions
def copy_attr_dim(src, dst, usr=None, script=None):
    """
    Copy dimensions and global attributes from a source to a destination NetCDF dataset.

    All global attributes from ``src`` are copied to ``dst`` under the prefix
    ``original_attribute_``. Provenance metadata (``perturbed_by``,
    ``perturbed_on_date``, ``perturbed_with_script``, ``perturbed_with_git_repo``,
    ``perturbed_with_git_hash``) is added to ``dst``.

    Parameters
    ----------
    src : netCDF4.Dataset
        Source dataset to copy dimensions and attributes from.
    dst : netCDF4.Dataset
        Destination dataset to write dimensions and attributes to.
    usr : str, optional
        Username to record in the ``perturbed_by`` attribute. Defaults to the
        ``USER`` environment variable, or ``"unknown"`` if not set.
    script : str, optional
        Path of the calling script to record in ``perturbed_with_script``.
        Pass ``__file__`` from the calling script. Defaults to ``"unknown"``.
    """
    # copy attributes as-is to preserve CF-convention names
    for name in src.ncattrs():
        dst.setncattr(name, src.getncattr(name))
    # copy dimensions
    for name, dimension in src.dimensions.items():
        dst.createDimension(name, len(dimension))
    # provenance: user, date, script
    if usr is None:
        usr = os.environ.get("USER", "unknown")
    dst.setncattr("perturbed_by", usr)
    dst.setncattr("perturbed_on_date",
                  datetime.datetime.today().strftime("%Y-%m-%d"))
    dst.setncattr("perturbed_with_script",
                  script if script is not None else "unknown")
    # append to history attribute to document the processing step
    old_history = src.getncattr("history") if "history" in src.ncattrs() else ""
    dst.setncattr("history", old_history +
                  f"\n{datetime.date.today()}: {' '.join(sys.argv)}")
    # provenance: git
    if not _GIT_AVAILABLE:
        warnings.warn("`import git` not available.", UserWarning)
        dst.setncattr("perturbed_with_git_repo", "unknown (gitpython not installed)")
        dst.setncattr("perturbed_with_git_hash", "unknown (gitpython not installed)")
        return
    try:
        # Anchor to utils.py's own location so that the correct repo is found
        # regardless of the working directory the script is called from.
        repo = git.Repo(os.path.dirname(os.path.abspath(__file__)),
                        search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        warnings.warn("Not inside a git repository.", UserWarning)
        dst.setncattr("perturbed_with_git_repo", "unknown (not a git repository)")
        dst.setncattr("perturbed_with_git_hash", "unknown (not a git repository)")
        return
    try:
        repo_url = repo.remotes.origin.url
    except AttributeError:
        repo_url = "unknown (no remote 'origin')"
    dst.setncattr("perturbed_with_git_repo", repo_url)
    if len(repo.git.ls_files(m=True)) > 0:
        warnings.warn("Dirty worktree in git repository! Check `git status`",
                      UserWarning)
        dst.setncattr("perturbed_with_git_hash (dirty worktree)", repo.head.object.hexsha[:10])
    else:
        dst.setncattr("perturbed_with_git_hash", repo.head.object.hexsha[:10])
