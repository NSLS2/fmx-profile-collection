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

xbpm2 = Xbpm('SR:C17-BI{XBPM:2}', name='xbpm2')
#best = Best('XF:16IDB-CT{Best}:BPM0:', name='best')
