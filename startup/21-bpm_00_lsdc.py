from ophyd import Device, EpicsSignal, Component as Cpt, EpicsSignalRO

class Xbpm(Device):
    x = Cpt(EpicsSignalRO, 'Pos:X-I')
    y = Cpt(EpicsSignalRO, 'Pos:Y-I')
    a = Cpt(EpicsSignalRO, 'Ampl:ACurrAvg-I')
    b = Cpt(EpicsSignalRO, 'Ampl:BCurrAvg-I')
    c = Cpt(EpicsSignalRO, 'Ampl:CCurrAvg-I')
    d = Cpt(EpicsSignalRO, 'Ampl:DCurrAvg-I')
    total = Cpt(EpicsSignalRO, 'Ampl:CurrTotal-I')

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

xbpm2 = Xbpm('SR:C17-BI{XBPM:2}', name='xbpm2')
print("xbpm2")

bpm1 = Bpm('XF:17IDA-BI:FMX{BPM:1}', name='bpm1')
print("bpm1")
bpm4 = Bpm('XF:17IDC-BI:FMX{BPM:4}', name='bpm4')
print("bpm4")

bpm1.sum_all.kind = 'hinted'
bpm4.sum_all.kind = 'hinted'

bpm1_sum_all_precision = EpicsSignal('XF:17IDA-BI:FMX{BPM:1}SumAll:MeanValue_RBV.PREC')
bpm1_sum_all_precision.put(10)

## 20250107 BPM4 IOC disconnected
#bpm4_sum_all_precision = EpicsSignal('XF:17IDC-BI:FMX{BPM:4}SumAll:MeanValue_RBV.PREC')
#bpm4_sum_all_precision.put(10)
