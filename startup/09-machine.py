from ophyd import Device, EpicsSignal, EpicsSignalRO, EpicsMotor
from ophyd import Component as Cpt
from ophyd.utils import set_and_wait


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
class InsertionDevice(Device):
    gap = Cpt(EpicsMotor, '-Ax:Gap}-Mtr',
              kind='hinted', name='')
    brake = Cpt(EpicsSignal, '}BrakesDisengaged-Sts',
                write_pv='}BrakesDisengaged-SP',
                kind='omitted', add_prefix=('read_pv', 'write_pv', 'suffix'))

    def set(self, *args, **kwargs):
        set_and_wait(self.brake, 1)
        return self.gap.set(*args, **kwargs)

    def stop(self, *, success=False):
        return self.gap.stop(success=success)

ivu_gap = InsertionDevice('SR:C17-ID:G1{IVU21:2', name='ivu')
