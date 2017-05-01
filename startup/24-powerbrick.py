from ophyd import (EpicsSignal, EpicsSignalRO, EpicsMotor, Device, Component as Cpt,
                   DeviceStatus) 

class PBSignalWithRBV(EpicsSignal):
    # An EPICS signal that uses the NSLS-II convention of 'pvname-SP' being the
    # setpoint and 'pvname-I' being the read-back

    def __init__(self, prefix, **kwargs):
        super().__init__(prefix + '-I', write_pv=prefix + '-SP', **kwargs)


class PowerBrickVectorMotor(Device):
    start = Cpt(PBSignalWithRBV, 'Start')
    end = Cpt(PBSignalWithRBV, 'End')

    def __init__(self, prefix, mtr, *, parent=None, **kwargs):
        self.mtr = EpicsMotor(mtr.prefix)
        cfg_attrs = ['start', 'end']
        super().__init__(prefix, configuration_attrs=cfg_attrs,
                         parent=parent, **kwargs)


class PowerBrickVectorBase(Device):
    x = Cpt(PowerBrickVectorMotor, 'Pos:X', mtr=gonio.gx)
    y = Cpt(PowerBrickVectorMotor, 'Pos:Y', mtr=gonio.py)
    z = Cpt(PowerBrickVectorMotor, 'Pos:Z', mtr=gonio.pz)
    o = Cpt(PowerBrickVectorMotor, 'Pos:O', mtr=gonio.o)

    exposure = Cpt(PBSignalWithRBV, 'Val:Exposure')
    num_samples = Cpt(PBSignalWithRBV, 'Val:NumSamples')

    expose = Cpt(EpicsSignal, 'Expose-Sel')
    hold = Cpt(EpicsSignal, 'Hold-Sel')

    state = Cpt(EpicsSignalRO, 'Sts:State-Sts', auto_monitor=True)
    running = Cpt(EpicsSignalRO, 'Sts:Running-Sts', auto_monitor=True)

    go = Cpt(EpicsSignal, 'Cmd:Go-Cmd')
    proceed = Cpt(EpicsSignal, 'Cmd:Proceed-Cmd')
    abort = Cpt(EpicsSignal, 'Cmd:Abort-Cmd')

    def __init__(self, prefix, configuration_attrs=None, *args, **kwargs):
        cfg_attrs = ['x', 'y', 'z', 'o', 'exposure', 'num_samples', 'expose', 'hold']
        if configuration_attrs is not None:
            cfg_attrs = configuration_attrs + cfg_attrs
        super().__init__(prefix, configuration_attrs=cfg_attrs, *args, **kwargs)
        
        self.motors = [self.x, self.y, self.z, self.o]


class PowerBrickVector(PowerBrickVectorBase):
    def __init__(self, prefix, *args, **kwargs):
        self._holding_status = None
        self._running_status = None
        super().__init__(prefix, *args, **kwargs)

    def kickoff(self):
        print(self.name, "kickoff")
        self._running_status = DeviceStatus(self)
        self._holding_status = DeviceStatus(self)

        if self.hold.get():
            self.state.subscribe(self._state_changed, run=False)
        else:
            self._holding_status._finished()

        self.go.put(1, wait=True)
        self.running.subscribe(self._running_status_changed, run=False)
        return self._holding_status

    def complete(self):
        print(self.name, "complete")
        if self.hold.get():
            self.proceed.put(1, wait=True)
        return self._running_status
    
    def _state_changed(self, value=None, old_value=None, obj=None, *args, **kwargs):
        if old_value != 2 and value == 2:
            print(self.name, "holding")
            obj.clear_sub(self._state_changed)
            self._holding_status._finished()
            self._holding_status = None

    def _running_status_changed(self, value=None, old_value=None, obj=None, *args, **kwargs):
        if old_value == 1 and value == 0:
            print(self.name, "finished")
            obj.clear_sub(self._running_status_changed)
            self._running_status._finished()
            self._running_status = None
                

pb_vec = PowerBrickVector('XF:17IDC-ES:FMX{Gon:1-Vec}', name='pb_vec')
