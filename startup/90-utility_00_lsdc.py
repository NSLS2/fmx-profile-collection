from functools import partial
from mxtools.fmx.utility import BeamlineCalibrations, PuckSafety, blStrGet, get_energy


BL_calibration = BeamlineCalibrations('XF:17ID-ES:FMX{Misc-',
                                      name='BL_calibration',
                                      read_attrs=['LoMagCal', 'HiMagCal'])

## Robot dewar puck safety system
puck_safety = PuckSafety('XF:17IDC-OP:FMX{DewarSwitch}Seq', name='puck_safety',
                        read_attrs=[],
                        labels=['fmx'])

get_energy = partial(get_energy, hdcm=hdcm)

# Example for unpacking kwargs:
# kwargs = {"param1": "test1",
#           "param2": "test2",}

# my_plan = partial(my_plan, **kwargs)