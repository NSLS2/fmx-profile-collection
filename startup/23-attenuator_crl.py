from ophyd import PVPositioner, PVPositionerPC, Device, Component as Cpt, EpicsMotor, EpicsSignal, EpicsSignalRO

class Transmission(Device):
    energy = Cpt(EpicsSignal, 'Energy-SP') # PV only used for debugging. Attenuator uses Bragg axis energy
    transmission = Cpt(EpicsSignal, 'Trans-SP')
    set_trans = Cpt(EpicsSignal, 'Cmd:Set-Cmd.PROC')

class AttenuatorBCU(Device):
    a1 = Cpt(EpicsMotor, '-Ax:1}Mtr')
    a2 = Cpt(EpicsMotor, '-Ax:2}Mtr')
    a3 = Cpt(EpicsMotor, '-Ax:3}Mtr')
    a4 = Cpt(EpicsMotor, '-Ax:4}Mtr')
    done = Cpt(EpicsSignalRO, 'attenDone')

class RISlider(Device):
    mv_in = Cpt(EpicsSignal, 'Cmd:In-Cmd')
    mv_out = Cpt(EpicsSignal, 'Cmd:Out-Cmd')
    status = Cpt(EpicsSignalRO, 'Pos-Sts') # status: 0 (Not In), 1 (In)
    
class AttenuatorRI(Device):
    f1 = Cpt(RISlider, '01}')
    f2 = Cpt(RISlider, '02}')
    f3 = Cpt(RISlider, '03}')
    f4 = Cpt(RISlider, '04}')
    f5 = Cpt(RISlider, '05}')
    f6 = Cpt(RISlider, '06}')
    f7 = Cpt(RISlider, '07}')
    f8 = Cpt(RISlider, '08}')
    f9 = Cpt(RISlider, '09}')
    f10 = Cpt(RISlider, '10}')
    f11 = Cpt(RISlider, '11}')
    f12 = Cpt(RISlider, '12}')

#######################################################
### FMX
#######################################################


## BCU Transmission
trans_bcu = Transmission('XF:17IDC-OP:FMX{Attn:BCU}', name='BCU_Transmission',
                         read_attrs=['transmission'])
## RI Transmission
trans_ri = Transmission('XF:17IDC-OP:FMX{Attn:RI}', name='RI_Transmission',
                        read_attrs=['transmission'])

## BCU Attenuator
atten_bcu = AttenuatorBCU('XF:17IDC-OP:FMX{Attn:BCU', name='BCU_Attenuator',
                          read_attrs=['done'])

## RI Attenuator
atten_ri = AttenuatorRI('XF:17IDC-OP:FMX{Attn:', name='RI_Attenuator',
                          read_attrs=[])
