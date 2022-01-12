from ophyd import Device, EpicsSignal, EpicsSignalRO, EpicsMotor
from ophyd import Component as Cpt
from ophyd.utils import set_and_wait

beam_current = EpicsSignal('SR:OPS-BI{DCCT:1}I:Real-I')

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

# Photon Local Feedback, sector 17 orbit angle correction onto FMX XBPM1
class PhotonLocalFeedback(Device):
    x_enable = Cpt(EpicsSignal, 'X-FdbkEnabled')
    y_enable = Cpt(EpicsSignal, 'Y-FdbkEnabled')

photon_local_feedback_c17 = PhotonLocalFeedback('SR:APHLA:LBAgent{BUMP:C17-R7X2}', name='photon_local_feedback')