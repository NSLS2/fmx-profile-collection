from ophyd import PVPositioner, PVPositionerPC, Device, Component as Cpt, EpicsMotor, EpicsSignal, EpicsSignalRO

class Transmission(Device):
    energy = Cpt(EpicsSignal, 'Energy-SP') # PV only used for debugging. Attenuator uses Bragg axis energy
    transmission = Cpt(EpicsSignal, 'Trans-SP')
    set_trans = Cpt(EpicsSignal, 'Cmd:Set-Cmd.PROC')

## Dummy Attenuator - for read/write_lut() and XF:17ID-ES:FMX{Misc-LUT:atten}X-Wfm/Y-Wfm
class AttenuatorLUT(Device):
    done = Cpt(EpicsSignalRO, '}attenDone')

class AttenuatorBCU(Device):
    a1 = Cpt(EpicsMotor, '-Ax:1}Mtr', labels=['fmx'])
    a2 = Cpt(EpicsMotor, '-Ax:2}Mtr', labels=['fmx'])
    a3 = Cpt(EpicsMotor, '-Ax:3}Mtr', labels=['fmx'])
    a4 = Cpt(EpicsMotor, '-Ax:4}Mtr', labels=['fmx'])
    done = Cpt(EpicsSignalRO, '}attenDone')

#######################################################
### FMX
#######################################################

## BCU Transmission
trans_bcu = Transmission('XF:17IDC-OP:FMX{Attn:BCU}', name='trans_bcu',
                         read_attrs=['transmission'])
## RI Transmission
trans_ri = Transmission('XF:17IDC-OP:FMX{Attn:RI}', name='trans_ri',
                        read_attrs=['transmission'])

## Dummy Attenuator - for read/write_lut() and XF:17ID-ES:FMX{Misc-LUT:atten}X-Wfm/Y-Wfm
atten = AttenuatorLUT('XF:17IDC-OP:FMX{Attn:BCU', name='atten',
                          read_attrs=['done'])

## BCU Attenuator
atten_bcu = AttenuatorBCU('XF:17IDC-OP:FMX{Attn:BCU', name='atten_bcu',
                          read_attrs=['done', 'a1', 'a2', 'a3', 'a4'],
                          labels=['fmx'])

