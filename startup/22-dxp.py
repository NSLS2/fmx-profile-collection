from ophyd.mca import (EpicsMCA, EpicsDXP, Mercury1, SoftDXPTrigger)
from ophyd import Component as Cpt, Signal

class FMXMercury(Mercury1, SoftDXPTrigger):
    count_time = Cpt(Signal, value=None)


mercury = FMXMercury('XF:17IDC-ES:FMX{Det:Mer}', name='mercury')
mercury.read_attrs = ['mca.spectrum', 'mca.preset_live_time', 'mca.rois.roi0.count']
