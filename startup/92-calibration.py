from ophyd import Device, Component as Cpt, EpicsSignal, EpicsSignalRO

class BeamlineCalibrations(Device):
    LoMagCal = Cpt(EpicsSignal, 'LoMagCal}')
    HiMagCal = Cpt(EpicsSignal, 'HiMagCal}')

BL_calibration = BeamlineCalibrations('XF:17ID-ES:FMX{Misc-',
                                      name='BL_calibration',
                                      read_attrs=['LoMagCal', 'HiMagCal'])