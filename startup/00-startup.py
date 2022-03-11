from ophyd.signal import EpicsSignalBase
# EpicsSignalBase.set_default_timeout(timeout=10, connection_timeout=10)  # old style
EpicsSignalBase.set_defaults(timeout=10, connection_timeout=10)  # new style


import sys
import logging

import bluesky

import matplotlib
from IPython import get_ipython

# get_ipython().run_line_magic('matplotlib', 'widget')  # i.e. %matplotlib widget
# get_ipython().run_line_magic('matplotlib', 'notebook')
import matplotlib.pyplot


# Import matplotlib and put it in interactive mode.
import matplotlib.pyplot as plt

plt.ion()
