import os
import numpy as np
import json
import datetime

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
def copy_attr_dim(src, dst, usr=None):
    """
    Copy dimensions and global attributes from a source to a destination NetCDF dataset.

    All global attributes from ``src`` are copied to ``dst`` under the prefix
    ``original_attribute_``. Provenance metadata (``perturbed_by``,
    ``perturbed_on_date``) is added to ``dst``.

    Parameters
    ----------
    src : netCDF4.Dataset
        Source dataset to copy dimensions and attributes from.
    dst : netCDF4.Dataset
        Destination dataset to write dimensions and attributes to.
    usr : str, optional
        Username to record in the ``perturbed_by`` attribute. Defaults to the
        ``USER`` environment variable, or ``"unknown"`` if not set.
    """
    # copy attributes
    for name in src.ncattrs():
        dst.setncattr("original_attribute_" + name, src.getncattr(name))
    # copy dimensions
    for name, dimension in src.dimensions.items():
        dst.createDimension(name, len(dimension))
    # Additional attribute
    if usr is None:
        usr = os.environ.get("USER", "unknown")
    dst.setncattr("perturbed_by", usr)
    dst.setncattr("perturbed_on_date",
                  datetime.datetime.today().strftime("%d.%m.%y"))
    # TODO: More attributes, possibly repository-related
