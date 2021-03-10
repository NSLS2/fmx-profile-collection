from ophyd import EpicsSignal

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

