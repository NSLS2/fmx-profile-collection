from ophyd.mca import (EpicsMCA, EpicsDXP, Mercury1, SoftDXPTrigger)

class FMXMercury(Mercury1, SoftDXPTrigger):
    pass


mercury = FMXMercury('XF:17IDC-ES:FMX{Det:Mer}', name='mercury')
mercury.read_attrs = ['mca.spectrum', 'mca.preset_live_time', 'mca.rois.roi0.count']
