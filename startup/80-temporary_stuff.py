## Disable warning on this positioner. End switch faulty

from ophyd.utils.epics_pvs import AlarmSeverity
light.y.tolerated_alarm = AlarmSeverity.MAJOR