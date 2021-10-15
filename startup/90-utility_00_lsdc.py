from ophyd import Device, Component as Cpt, EpicsSignal, EpicsSignalRO
import socket


class BeamlineCalibrations(Device):
    LoMagCal = Cpt(EpicsSignal, 'LoMagCal}')
    HiMagCal = Cpt(EpicsSignal, 'HiMagCal}')

BL_calibration = BeamlineCalibrations('XF:17ID-ES:FMX{Misc-',
                                      name='BL_calibration',
                                      read_attrs=['LoMagCal', 'HiMagCal'])


class PuckSafety(Device):
    On = Cpt(EpicsSignal, 'On.PROC')
    Off = Cpt(EpicsSignal, 'Off.PROC')
    
## Robot dewar puck safety system
puck_safety = PuckSafety('XF:17IDC-OP:FMX{DewarSwitch}Seq', name='puck_safety',
                        read_attrs=[],
                        labels=['fmx'])

def blStrGet():
    """
    Return beamline string
    
    blStr: 'AMX' or 'FMX'
    
    Beamline is determined by querying hostname
    """
    hostStr = socket.gethostname()
    if hostStr == 'xf17id2-ca1':
        blStr = 'FMX'
    elif hostStr == 'xf17id1-ca1':
        blStr = 'AMX'
    else: 
        print('Error - this code must be executed on one of the -ca1 machines')
        blStr = -1
        
    return blStr


def get_energy():
    """
    Returns the current photon energy in eV derived from the DCM Bragg angle
    """ 
    
    blStr = blStrGet()
    if blStr == -1: return -1
    
    if blStr == 'AMX':
        energy = vdcm.e.user_readback.get()
    elif blStr == 'FMX':
        energy = hdcm.e.user_readback.get()
    
    return energy


