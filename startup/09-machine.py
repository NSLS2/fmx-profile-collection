from ophyd import PVPositionerPC, EpicsSignal, EpicsSignalRO
from ophyd import Component as Cpt

# Ugly, ugly hack (sorry)
# Can't set the PV's precision, so I'll force it here
class EpicsSignalPrec(EpicsSignal):
    @property
    def precision(self):
        return 4
    
class EpicsSignalROPrec(EpicsSignal):
    @property
    def precision(self):
        return 4

# Undulator

class Undulator(PVPositionerPC):
    readback = Cpt(EpicsSignalROPrec, '-LEnc}Gap')
    setpoint = Cpt(EpicsSignalPrec, '-Mtr:2}Inp:Pos')
    actuate = Cpt(EpicsSignal, '-Mtr:2}Sw:Go')
    actuate_value = 1
    stop_signal = Cpt(EpicsSignal, '-Mtr:2}Pos.STOP')
    stop_value = 1

ivu_gap = Undulator('SR:C17-ID:G1{IVU21:2', name='ivu_gap', timeout=20)

