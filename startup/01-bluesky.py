# if isnotebook():
#     from bluesky.utils import install_nb_kicker
#     install_nb_kicker()
# else:
#     from bluesky.utils import install_qt_kicker
#     install_qt_kicker()
#     print("Installing Qt Kicker...")

# # # Make ophyd listen to pyepics.
# # from ophyd import setup_ophyd
# # setup_ophyd()

# # Set up a RunEngine and use metadata backed by a sqlite file.
# from bluesky import RunEngine
# from bluesky.utils import get_history
# RE = RunEngine(get_history())

# # Set up a Broker.
# from databroker import Broker
# db = Broker.named('fmx')

# # Subscribe metadatastore to documents.
# # If this is removed, data is not saved to metadatastore.
# RE.subscribe(db.insert)

# # Set up SupplementalData.
# from bluesky import SupplementalData
# sd = SupplementalData()
# RE.preprocessors.append(sd)

# # Add a progress bar.
# # from bluesky.utils import ProgressBarManager
# # pbar_manager = ProgressBarManager()
# # RE.waiting_hook = pbar_manager

# # Register bluesky IPython magics.
# from bluesky.magics import BlueskyMagics
# get_ipython().register_magics(BlueskyMagics)

# # Set up the BestEffortCallback.
# from bluesky.callbacks.best_effort import BestEffortCallback
# bec = BestEffortCallback()
# #RE.subscribe(bec)
# #peaks = bec.peaks  # just as alias for less typing

# # At the end of every run, verify that files were saved and
# # print a confirmation message.
# from bluesky.callbacks.broker import verify_files_saved
# # RE.subscribe(post_run(verify_files_saved), 'stop')

# # Import matplotlib and put it in interactive mode.
# import matplotlib.pyplot as plt
# plt.ion()

# # Make plots update live while scans run.
# from bluesky.utils import install_qt_kicker
# install_qt_kicker()

# # Optional: set any metadata that rarely changes.
# # RE.md['beamline_id'] = 'YOUR_BEAMLINE_HERE'

# # convenience imports
# from bluesky.callbacks import *
# from bluesky.callbacks.broker import *
# from bluesky.simulators import *
# from bluesky.plans import *
# import numpy as np

# from pyOlog.ophyd_tools import *

# # Uncomment the following lines to turn on verbose messages for
# # debugging.
# # import logging
# # ophyd.logger.setLevel(logging.DEBUG)
# # logging.basicConfig(level=logging.DEBUG)


import nslsii

BEAMLINE_ID = 'fmx'

nslsii.configure_base(get_ipython().user_ns, BEAMLINE_ID)


from pathlib import Path

import appdirs


try:
    from bluesky.utils import PersistentDict
except ImportError:
    import msgpack
    import msgpack_numpy
    import zict

    class PersistentDict(zict.Func):
        """
        A MutableMapping which syncs it contents to disk.
        The contents are stored as msgpack-serialized files, with one file per item
        in the mapping.
        Note that when an item is *mutated* it is not immediately synced:
        >>> d['sample'] = {"color": "red"}  # immediately synced
        >>> d['sample']['shape'] = 'bar'  # not immediately synced
        but that the full contents are synced to disk when the PersistentDict
        instance is garbage collected.
        """
        def __init__(self, directory):
            self._directory = directory
            self._file = zict.File(directory)
            self._cache = {}
            super().__init__(self._dump, self._load, self._file)
            self.reload()

            # Similar to flush() or _do_update(), but without reference to self
            # to avoid circular reference preventing collection.
            # NOTE: This still doesn't guarantee call on delete or gc.collect()!
            #       Explicitly call flush() if immediate write to disk required.
            def finalize(zfile, cache, dump):
                zfile.update((k, dump(v)) for k, v in cache.items())

            import weakref
            self._finalizer = weakref.finalize(
                self, finalize, self._file, self._cache, PersistentDict._dump)

        @property
        def directory(self):
            return self._directory

        def __setitem__(self, key, value):
            self._cache[key] = value
            super().__setitem__(key, value)

        def __getitem__(self, key):
            return self._cache[key]

        def __delitem__(self, key):
            del self._cache[key]
            super().__delitem__(key)

        def __repr__(self):
            return f"<{self.__class__.__name__} {dict(self)!r}>"

        @staticmethod
        def _dump(obj):
            "Encode as msgpack using numpy-aware encoder."
            # See https://github.com/msgpack/msgpack-python#string-and-binary-type
            # for more on use_bin_type.
            return msgpack.packb(
                obj,
                default=msgpack_numpy.encode,
                use_bin_type=True)

        @staticmethod
        def _load(file):
            return msgpack.unpackb(
                file,
                object_hook=msgpack_numpy.decode,
                raw=False)

        def flush(self):
            """Force a write of the current state to disk"""
            for k, v in self.items():
                super().__setitem__(k, v)

        def reload(self):
            """Force a reload from disk, overwriting current cache"""
            self._cache = dict(super().items())

# runengine_metadata_dir = appdirs.user_data_dir(appname="bluesky") / Path("runengine-metadata")
runengine_metadata_dir = Path(f"/GPFS/CENTRAL/xf17id1/skinnerProjectsBackup/bnlpx_config/{BEAMLINE_ID}_bluesky_config/")

# PersistentDict will create the directory if it does not exist
RE.md = PersistentDict(runengine_metadata_dir)
