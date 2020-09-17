from ophyd import Device, EpicsSignal, Component as Cpt, EpicsSignalRO

class Bpm(Device):
    x = Cpt(EpicsSignalRO, 'PosX:MeanValue_RBV')
    y = Cpt(EpicsSignalRO, 'PosY:MeanValue_RBV')
    a = Cpt(EpicsSignalRO, 'Current1:MeanValue_RBV')
    b = Cpt(EpicsSignalRO, 'Current2:MeanValue_RBV')
    c = Cpt(EpicsSignalRO, 'Current3:MeanValue_RBV')
    d = Cpt(EpicsSignalRO, 'Current4:MeanValue_RBV')
    sum_x = Cpt(EpicsSignalRO, 'SumX:MeanValue_RBV')
    sum_y = Cpt(EpicsSignalRO, 'SumY:MeanValue_RBV')
    sum_all = Cpt(EpicsSignalRO, 'SumAll:MeanValue_RBV')

class Xbpm(Device):
    x = Cpt(EpicsSignalRO, 'Pos:X-I')
    y = Cpt(EpicsSignalRO, 'Pos:Y-I')
    a = Cpt(EpicsSignalRO, 'Ampl:ACurrAvg-I')
    b = Cpt(EpicsSignalRO, 'Ampl:BCurrAvg-I')
    c = Cpt(EpicsSignalRO, 'Ampl:CCurrAvg-I')
    d = Cpt(EpicsSignalRO, 'Ampl:DCurrAvg-I')
    total = Cpt(EpicsSignalRO, 'Ampl:CurrTotal-I')

class Best(Device):
    x_mean  = Cpt(EpicsSignal, 'PosX_Mean')
    x_std = Cpt(EpicsSignal, 'PosX_Std')
    y_mean  = Cpt(EpicsSignal, 'PosY_Mean')
    y_std = Cpt(EpicsSignal, 'PosY_Std')
    int_mean  = Cpt(EpicsSignal, 'Int_Mean')
    int_std = Cpt(EpicsSignal, 'Int_Std')

#best = Best('XF:16IDB-CT{Best}:BPM0:', name='best')
bpm1 = Bpm('XF:17IDA-BI:FMX{BPM:1}', name='bpm1')
bpm4 = Bpm('XF:17IDC-BI:FMX{BPM:4}', name='bpm4')
xbpm2 = Xbpm('SR:C17-BI{XBPM:2}', name='xbpm2')
