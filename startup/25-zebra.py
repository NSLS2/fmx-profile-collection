from enum import IntEnum

from ophyd import (Device, Component as Cpt, FormattedComponent as FC,
                   Signal)
from ophyd import (EpicsSignal, EpicsSignalRO, DeviceStatus)
from ophyd.utils import set_and_wait
import filestore.api as fs
from bluesky.plans import fly
import pandas as pd

import uuid
import time
import datetime as dt
import os


def _get_configuration_attrs(cls, *, signal_class=Signal):
    return [sig_name for sig_name in cls.signal_names
            if issubclass(getattr(cls, sig_name).cls, signal_class)]


class ZebraInputEdge(IntEnum):
    FALLING = 1
    RISING = 0


class ZebraAddresses(IntEnum):
    DISCONNECT = 0
    IN1_TTL = 1
    IN1_NIM = 2
    IN1_LVDS = 3
    IN2_TTL = 4
    IN2_NIM = 5
    IN2_LVDS = 6
    IN3_TTL = 7
    IN3_OC = 8
    IN3_LVDS = 9
    IN4_TTL = 10
    IN4_CMP = 11
    IN4_PECL = 12
    IN5_ENCA = 13
    IN5_ENCB = 14
    IN5_ENCZ = 15
    IN5_CONN = 16
    IN6_ENCA = 17
    IN6_ENCB = 18
    IN6_ENCZ = 19
    IN6_CONN = 20
    IN7_ENCA = 21
    IN7_ENCB = 22
    IN7_ENCZ = 23
    IN7_CONN = 24
    IN8_ENCA = 25
    IN8_ENCB = 26
    IN8_ENCZ = 27
    IN8_CONN = 28
    PC_ARM = 29
    PC_GATE = 30
    PC_PULSE = 31
    AND1 = 32
    AND2 = 33
    AND3 = 34
    AND4 = 35
    OR1 = 36
    OR2 = 37
    OR3 = 38
    OR4 = 39
    GATE1 = 40
    GATE2 = 41
    GATE3 = 42
    GATE4 = 43
    DIV1_OUTD = 44
    DIV2_OUTD = 45
    DIV3_OUTD = 46
    DIV4_OUTD = 47
    DIV1_OUTN = 48
    DIV2_OUTN = 49
    DIV3_OUTN = 50
    DIV4_OUTN = 51
    PULSE1 = 52
    PULSE2 = 53
    PULSE3 = 54
    PULSE4 = 55
    QUAD_OUTA = 56
    QUAD_OUTB = 57
    CLOCK_1KHZ = 58
    CLOCK_1MHZ = 59
    SOFT_IN1 = 60
    SOFT_IN2 = 61
    SOFT_IN3 = 62
    SOFT_IN4 = 63


class ZebraSignalWithRBV(EpicsSignal):
    # An EPICS signal that uses the Zebra convention of 'pvname' being the
    # setpoint and 'pvname:RBV' being the read-back

    def __init__(self, prefix, **kwargs):
        super().__init__(prefix + ':RBV', write_pv=prefix, **kwargs)


class ZebraPulse(Device):
    width = Cpt(ZebraSignalWithRBV, 'WID')
    input_addr = Cpt(ZebraSignalWithRBV, 'INP')
    input_str = Cpt(EpicsSignalRO, 'INP:STR', string=True)
    input_status = Cpt(EpicsSignalRO, 'INP:STA')
    delay = Cpt(ZebraSignalWithRBV, 'DLY')
    delay_sync = Cpt(EpicsSignal, 'DLY:SYNC')
    time_units = Cpt(ZebraSignalWithRBV, 'PRE', string=True)
    output = Cpt(EpicsSignal, 'OUT')

    input_edge = FC(EpicsSignal,
                    '{self._zebra_prefix}POLARITY:{self._edge_addr}')

    _edge_addrs = {1: 'BC',
                   2: 'BD',
                   3: 'BE',
                   4: 'BF',
                   }

    def __init__(self, prefix, *, index=None, parent=None,
                 configuration_attrs=None, read_attrs=None, **kwargs):
        if read_attrs is None:
            read_attrs = []
        if configuration_attrs is None:
            configuration_attrs = _get_configuration_attrs(self.__class__)

        zebra = parent
        self.index = index
        self._zebra_prefix = zebra.prefix
        self._edge_addr = self._edge_addrs[index]

        super().__init__(prefix, configuration_attrs=configuration_attrs,
                         read_attrs=read_attrs, parent=parent, **kwargs)


class ZebraOutputBase(Device):
    '''The base of all zebra outputs (1~8)

        Front outputs
        # TTL  LVDS  NIM  PECL  OC  ENC
        1  o    o     o
        2  o    o     o
        3  o    o               o
        4  o          o    o

        Rear outputs
        # TTL  LVDS  NIM  PECL  OC  ENC
        5                            o
        6                            o
        7                            o
        8                            o

    '''
    def __init__(self, prefix, *, index=None, read_attrs=None,
                 configuration_attrs=None, **kwargs):
        self.index = index

        if read_attrs is None:
            read_attrs = []
        if configuration_attrs is None:
            configuration_attrs = _get_configuration_attrs(self.__class__)

        super().__init__(prefix, read_attrs=read_attrs,
                         configuration_attrs=configuration_attrs, **kwargs)


class ZebraOutputType(Device):
    '''Shared by all output types (ttl, lvds, nim, pecl, out)'''
    addr = Cpt(ZebraSignalWithRBV, '')
    status = Cpt(EpicsSignalRO, ':STA')
    string = Cpt(EpicsSignalRO, ':STR', string=True)
    sync = Cpt(EpicsSignal, ':SYNC')
    write_output = Cpt(EpicsSignal, ':SET')

    def __init__(self, prefix, *, read_attrs=None, configuration_attrs=None,
                 **kwargs):
        if read_attrs is None:
            read_attrs = []
        if configuration_attrs is None:
            configuration_attrs = _get_configuration_attrs(self.__class__)

        super().__init__(prefix, read_attrs=read_attrs,
                         configuration_attrs=configuration_attrs, **kwargs)


class ZebraFrontOutput12(ZebraOutputBase):
    ttl = Cpt(ZebraOutputType, 'TTL')
    lvds = Cpt(ZebraOutputType, 'LVDS')
    nim = Cpt(ZebraOutputType, 'NIM')


class ZebraFrontOutput3(ZebraOutputBase):
    ttl = Cpt(ZebraOutputType, 'TTL')
    lvds = Cpt(ZebraOutputType, 'LVDS')
    open_collector = Cpt(ZebraOutputType, 'OC')


class ZebraFrontOutput4(ZebraOutputBase):
    ttl = Cpt(ZebraOutputType, 'TTL')
    nim = Cpt(ZebraOutputType, 'NIM')
    pecl = Cpt(ZebraOutputType, 'PECL')


class ZebraRearOutput(ZebraOutputBase):
    enca = Cpt(ZebraOutputType, 'ENCA')
    encb = Cpt(ZebraOutputType, 'ENCB')
    encz = Cpt(ZebraOutputType, 'ENCZ')
    conn = Cpt(ZebraOutputType, 'CONN')


class ZebraEncoder(Device):
    motor_pos = FC(EpicsSignalRO, '{self._zebra_prefix}M{self.index}:RBV')
    zebra_pos = FC(EpicsSignal, '{self._zebra_prefix}POS{self.index}_SET')
    encoder_res = FC(EpicsSignal, '{self._zebra_prefix}M{self.index}:MRES')
    encoder_off = FC(EpicsSignal, '{self._zebra_prefix}M{self.index}:OFF')
    _copy_pos_signal = FC(EpicsSignal, '{self._zebra_prefix}M{self.index}:SETPOS.PROC')

    def __init__(self, prefix, *, index=None, parent=None,
                 configuration_attrs=None, read_attrs=None, **kwargs):
        if read_attrs is None:
            read_attrs = []
        if configuration_attrs is None:
            configuration_attrs = _get_configuration_attrs(self.__class__)

        self.index = index
        self._zebra_prefix = parent.prefix

        super().__init__(prefix, read_attrs=read_attrs,
                         configuration_attrs=configuration_attrs,
                         parent=parent, **kwargs)

    def copy_position(self):
        self._copy_pos_signal.put(1)


class ZebraGateInput(Device):
    addr = Cpt(ZebraSignalWithRBV, '')
    string = Cpt(EpicsSignalRO, ':STR', string=True)
    status = Cpt(EpicsSignalRO, ':STA')
    sync = Cpt(EpicsSignal, ':SYNC')
    write_input = Cpt(EpicsSignal, ':SET')

    # Input edge index depends on the gate number (these are set in __init__)
    edge = FC(EpicsSignal,
              '{self._zebra_prefix}POLARITY:B{self._input_edge_idx}')

    def __init__(self, prefix, *, index=None, parent=None,
                 configuration_attrs=None, read_attrs=None, **kwargs):
        if read_attrs is None:
            read_attrs = []
        if configuration_attrs is None:
            configuration_attrs = _get_configuration_attrs(self.__class__)

        gate = parent
        zebra = gate.parent

        self.index = index
        self._zebra_prefix = zebra.prefix
        self._input_edge_idx = gate._input_edge_idx[self.index]

        super().__init__(prefix, read_attrs=read_attrs,
                         configuration_attrs=configuration_attrs,
                         parent=parent, **kwargs)


class ZebraGate(Device):
    input1 = Cpt(ZebraGateInput, 'INP1', index=1)
    input2 = Cpt(ZebraGateInput, 'INP2', index=2)
    output = Cpt(EpicsSignal, 'OUT')

    def __init__(self, prefix, *, index=None, read_attrs=None,
                 configuration_attrs=None, **kwargs):
        self.index = index
        self._input_edge_idx = {1: index - 1,
                                2: 4 + index - 1
                                }

        if read_attrs is None:
            read_attrs = []
        if configuration_attrs is None:
            configuration_attrs = ['output']

        super().__init__(prefix, configuration_attrs=configuration_attrs,
                         read_attrs=read_attrs, **kwargs)

    def set_input_edges(self, edge1, edge2):
        set_and_wait(self.input1.edge, int(edge1))
        set_and_wait(self.input2.edge, int(edge2))


class ZebraPositionCaptureDeviceBase(Device):
    source = Cpt(ZebraSignalWithRBV, 'SEL', put_complete=True)
    input_addr = Cpt(ZebraSignalWithRBV, 'INP')
    input_str = Cpt(EpicsSignalRO, 'INP:STR', string=True)
    input_status = Cpt(EpicsSignalRO, 'INP:STA')
    output = Cpt(EpicsSignalRO, 'OUT', auto_monitor=True)


class ZebraPositionCaptureArm(ZebraPositionCaptureDeviceBase):

    class ZebraArmSignalWithRBV(EpicsSignal):
        def __init__(self, prefix, **kwargs):
            super().__init__(prefix + 'ARM_OUT', write_pv=prefix+'ARM', **kwargs)

    class ZebraDisarmSignalWithRBV(EpicsSignal):
        def __init__(self, prefix, **kwargs):
            super().__init__(prefix + 'ARM_OUT', write_pv=prefix+'DISARM', **kwargs)

    arm = FC(ZebraArmSignalWithRBV, '{self._parent_prefix}')
    disarm = FC(ZebraDisarmSignalWithRBV, '{self._parent_prefix}')

    def __init__(self, prefix, *, parent=None,
                 configuration_attrs=None, read_attrs=None, **kwargs):
        if read_attrs is None:
            read_attrs = []
        if configuration_attrs is None:
            configuration_attrs = _get_configuration_attrs(self.__class__)

        self._parent_prefix = parent.prefix

        super().__init__(prefix, read_attrs=read_attrs,
                         configuration_attrs=configuration_attrs,
                         parent=parent, **kwargs)


class ZebraPositionCaptureGate(ZebraPositionCaptureDeviceBase):
    num_gates = Cpt(EpicsSignal, 'NGATE')
    start = Cpt(EpicsSignal, 'START')
    width = Cpt(EpicsSignal, 'WID')
    step = Cpt(EpicsSignal, 'STEP')


class ZebraPositionCapturePulse(ZebraPositionCaptureDeviceBase):
    max_pulses = Cpt(EpicsSignal, 'MAX')
    start = Cpt(EpicsSignal, 'START')
    width = Cpt(EpicsSignal, 'WID')
    step = Cpt(EpicsSignal, 'STEP')
    delay = Cpt(EpicsSignal, 'DLY')


class ZebraPositionCaptureData(Device):
    num_captured = Cpt(EpicsSignalRO, 'NUM_CAP')
    num_downloaded = Cpt(EpicsSignalRO, 'NUM_DOWN')

    time = Cpt(EpicsSignalRO, 'TIME')

    enc1 = Cpt(EpicsSignalRO, 'ENC1')
    enc2 = Cpt(EpicsSignalRO, 'ENC2')
    enc3 = Cpt(EpicsSignalRO, 'ENC3')
    enc4 = Cpt(EpicsSignalRO, 'ENC4')

    sys1 = Cpt(EpicsSignalRO, 'SYS1')
    sys2 = Cpt(EpicsSignalRO, 'SYS2')

    div1 = Cpt(EpicsSignalRO, 'DIV1')
    div2 = Cpt(EpicsSignalRO, 'DIV2')
    div3 = Cpt(EpicsSignalRO, 'DIV3')
    div4 = Cpt(EpicsSignalRO, 'DIV4')


class ZebraPositionCapture(Device):
    source = Cpt(ZebraSignalWithRBV, 'ENC')
    direction = Cpt(ZebraSignalWithRBV, 'DIR')
    time_units = Cpt(ZebraSignalWithRBV, 'TSPRE')

    arm = Cpt(ZebraPositionCaptureArm, 'ARM_')
    gate = Cpt(ZebraPositionCaptureGate, 'GATE_')
    pulse = Cpt(ZebraPositionCapturePulse, 'PULSE_')

    capture_enc1 = Cpt(EpicsSignal, 'BIT_CAP:B0')
    capture_enc2 = Cpt(EpicsSignal, 'BIT_CAP:B1')
    capture_enc3 = Cpt(EpicsSignal, 'BIT_CAP:B2')
    capture_enc4 = Cpt(EpicsSignal, 'BIT_CAP:B3')

    capture_sys1 = Cpt(EpicsSignal, 'BIT_CAP:B4')
    capture_sys2 = Cpt(EpicsSignal, 'BIT_CAP:B5')

    capture_div1 = Cpt(EpicsSignal, 'BIT_CAP:B6')
    capture_div2 = Cpt(EpicsSignal, 'BIT_CAP:B7')
    capture_div3 = Cpt(EpicsSignal, 'BIT_CAP:B8')
    capture_div4 = Cpt(EpicsSignal, 'BIT_CAP:B9')

    data = Cpt(ZebraPositionCaptureData, '')


class ZebraBase(Device):
    soft_input1 = Cpt(EpicsSignal, 'SOFT_IN:B0')
    soft_input2 = Cpt(EpicsSignal, 'SOFT_IN:B1')
    soft_input3 = Cpt(EpicsSignal, 'SOFT_IN:B2')
    soft_input4 = Cpt(EpicsSignal, 'SOFT_IN:B3')

    pulse1 = Cpt(ZebraPulse, 'PULSE1_', index=1)
    pulse2 = Cpt(ZebraPulse, 'PULSE2_', index=2)
    pulse3 = Cpt(ZebraPulse, 'PULSE3_', index=3)
    pulse4 = Cpt(ZebraPulse, 'PULSE4_', index=4)

    output1 = Cpt(ZebraFrontOutput12, 'OUT1_', index=1)
    output2 = Cpt(ZebraFrontOutput12, 'OUT2_', index=2)
    output3 = Cpt(ZebraFrontOutput3, 'OUT3_', index=3)
    output4 = Cpt(ZebraFrontOutput4, 'OUT4_', index=4)

    output5 = Cpt(ZebraRearOutput, 'OUT5_', index=5)
    output6 = Cpt(ZebraRearOutput, 'OUT6_', index=6)
    output7 = Cpt(ZebraRearOutput, 'OUT7_', index=7)
    output8 = Cpt(ZebraRearOutput, 'OUT8_', index=8)

    gate1 = Cpt(ZebraGate, 'GATE1_', index=1)
    gate2 = Cpt(ZebraGate, 'GATE2_', index=2)
    gate3 = Cpt(ZebraGate, 'GATE3_', index=3)
    gate4 = Cpt(ZebraGate, 'GATE4_', index=4)

    encoder1 = Cpt(ZebraEncoder, '', index=1)
    encoder2 = Cpt(ZebraEncoder, '', index=2)
    encoder3 = Cpt(ZebraEncoder, '', index=3)
    encoder4 = Cpt(ZebraEncoder, '', index=4)

    pos_capt = Cpt(ZebraPositionCapture, 'PC_')
    download_status = Cpt(EpicsSignalRO, 'ARRAY_ACQ', auto_monitor=True)
    reset = Cpt(EpicsSignal, 'SYS_RESET.PROC')

    addresses = ZebraAddresses

    def __init__(self, prefix, *, configuration_attrs=None, read_attrs=None,
                 **kwargs):
        if read_attrs is None:
            read_attrs = []
        if configuration_attrs is None:
            configuration_attrs = _get_configuration_attrs(self.__class__)

        super().__init__(prefix, configuration_attrs=configuration_attrs,
                         read_attrs=read_attrs, **kwargs)

        self.pulse = dict(self._get_indexed_devices(ZebraPulse))
        self.output = dict(self._get_indexed_devices(ZebraOutputBase))
        self.gate = dict(self._get_indexed_devices(ZebraGate))
        self.encoder = dict(self._get_indexed_devices(ZebraEncoder))

    def _get_indexed_devices(self, cls):
        for attr in self._sub_devices:
            dev = getattr(self, attr)
            if isinstance(dev, cls):
                yield dev.index, dev

    def trigger(self):
        # Re-implement this to trigger as desired in bluesky
        status = DeviceStatus(self)
        status._finished()
        return status


class Zebra(ZebraBase):
    MASTERS = ('x', 'y', 'z', 'o')

    master = Cpt(Signal, value='o',
                 doc="Master motor. Valid values: {}".format(MASTERS))
    master_start = Cpt(Signal, value=0,
                       doc="Starting position of the master positioner")
    master_end = Cpt(Signal, value=100,
                     doc="Ending position of the master positioner")
    num_frames = Cpt(Signal, value=100,
                     doc="Number of frames to be acquired")
    exposure = Cpt(Signal, value=0.1,
                     doc="Exposure, in ms")
    dead_time = Cpt(Signal, value=0.01,
                    doc="Detector dead time, in ms")

    def __init__(self, prefix, *args, **kwargs):
        cfg_attrs = ['master', 'master_start', 'master_end',
                     'num_frames', 'exposure', 'dead_time']

        self._collection_ts = None
        self._armed_status = None
        self._disarmed_status = None
        self._dl_status = None
        super().__init__(prefix, configuration_attrs=cfg_attrs, *args, **kwargs)

    def stage(self):
        print(self.name, "stage")
        if self.master.get() not in self.MASTERS:
            fmt = 'Invalid master positioner {}, must be one of {}'
            raise ValueError(fmt.format(self.master.get(), self.MASTERS))

        if self.dead_time.get() > self.exposure.get():
            raise ValueError('Dead time is greater than exposure')

        # Reset Zebra state
        self.reset.put(1, wait=True)
        time.sleep(0.1)

        pos_capt_source = self.MASTERS.index(self.master.get())

        master_start = self.master_start.get()
        master_width = abs(self.master_start.get() - self.master_end.get())
        master_dir = int(self.master_end.get() < self.master_start.get())  # 0: Positive, 1: Negative
        
        pulse_step = self.exposure.get()
        pulse_width = self.exposure.get() - self.dead_time.get()
        num_frames = self.num_frames.get()

        # Synchronize encoders
        for encoder in self.encoder.values():
            encoder.copy_position()
            
        # Set it with settle time, buggy otherwise
        #self.pos_capt.time_units.set("ms", settle_time=1.0)
        #self.pos_capt.gate.source.set("Position", settle_time=1.0)
        #self.pos_capt.pulse.source.set("Time", settle_time=1.0)
        
        self.pos_capt.time_units.put("ms", wait=True)
        self.pos_capt.gate.source.put("Position", wait=True)
        self.pos_capt.pulse.source.put("Time", wait=True)
        self.pos_capt.source.put(pos_capt_source, wait=True)

        self.stage_sigs.update({
            # Configure Position Capture
            self.pos_capt.direction: master_dir,

            self.pos_capt.capture_enc1: 1,
            self.pos_capt.capture_enc2: 1,
            self.pos_capt.capture_enc3: 1,
            self.pos_capt.capture_enc4: 1,

            # Configure Position Capture Arm
            self.pos_capt.arm.source: "Soft",

            # Configure Position Capture Gate
            self.pos_capt.gate.start: master_start,
            self.pos_capt.gate.width: master_width,
            self.pos_capt.gate.step: master_width,
            self.pos_capt.gate.num_gates: 1,

            # Configure Position Capture Pulses
            self.pos_capt.pulse.step: pulse_step,
            self.pos_capt.pulse.width: pulse_width,
            self.pos_capt.pulse.delay: 0,
            self.pos_capt.pulse.max_pulses: num_frames,
        })
        return super().stage()

    def kickoff(self):
        print(self.name, "kickoff")
        self._armed_status = DeviceStatus(self)
        self._disarmed_status = DeviceStatus(self)
        self.pos_capt.arm.output.subscribe(self._armed_status_changed, run=False)
        self.download_status.subscribe(self._disarmed_status_changed, run=False)

        self.pos_capt.arm.arm.put(1)
        self._collection_ts = time.time()
        return self._armed_status

    def complete(self):
        print(self.name, "complete")
        return self._disarmed_status

    def collect(self):
        print(self.name, "collect")
        ts = self.pos_capt.data.time.get()
        x = self.pos_capt.data.enc1.get()
        y = self.pos_capt.data.enc2.get()
        z = self.pos_capt.data.enc3.get()
        o = self.pos_capt.data.enc4.get()
        
        #ts = [1, 2, 3, 4]
        #x = [10, 20, 40, 30]
        #y = [20, 40, 30, 10]
        #z = [30, 10, 20, 40]
        #o = [40, 30, 10, 20]
        
        for timestamp, x_pos, y_pos, z_pos, o_pos in zip(ts, x, y, z, o):
            timestamp += self._collection_ts
            yield {
                'data': {'x': x_pos, 'y': y_pos, 'z': z_pos, 'o': o_pos},
                'timestamps': {'x': timestamp, 'y': timestamp, 'z': timestamp, 'o': timestamp},
                'time': timestamp,
            }

    def describe_collect(self):
        return {
            self.name: {
                'x': {
                    'source': 'Gonio Stack X',
                    'shape': 1,
                    'dtype': 'number',
                    'units': 'um',
                    'precision': 3,
                    'object_name': 'x'
                },
                'y': {
                    'source': 'Gonio Pin Y',
                    'shape': 1,
                    'dtype': 'number',
                    'units': 'um',
                    'precision': 3
                },
                'z': {
                    'source': 'Gonio Pin Z',
                    'shape': 1,
                    'dtype': 'number',
                    'units': 'um',
                    'precision': 3
                },
                'o': {
                    'source': 'Gonio Omega',
                    'shape': 1,
                    'dtype': 'number',
                    'units': 'deg',
                    'precision': 3
                }
            }
        }
    
    def decribe(self):
        return self.describe_collect()
    
    def _armed_status_changed(self, value=None, old_value=None, obj=None, *args, **kwargs):
        if old_value == 0 and value == 1:
            if self._armed_status is not None:
                self._armed_status._finished()
                print(self.name, "armed")
            obj.clear_sub(self._armed_status_changed)

    def _disarmed_status_changed(self, value=None, old_value=None, obj=None, *args, **kwargs):
        if old_value == 1 and value == 0:
            if self._disarmed_status is not None:
                self._disarmed_status._finished()
                print(self.name, "disarmed")
            obj.clear_sub(self._disarmed_status_changed)


def test_zebra(start=0, end=2, frame_time=0.2, dead_time=0.05, num_frames=10):
    # zebra.pos_capt.gate.source.set("Position", settle_time=1.0)
    zebra.pos_capt.gate.source.set("Time", settle_time=1.0)
    zebra.pos_capt.pulse.source.set("Time", settle_time=1.0)

    zebra.master_start.set(start)
    zebra.master_end.set(end)
    zebra.frame_time.set(frame_time)
    zebra.dead_time.set(dead_time)
    zebra.num_frames.set(num_frames)

    zebra.stage()
    yield from fly([zebra])
    zebra.unstage()

zebra = Zebra('XF:17IDC-ES:FMX{Zeb:3}:', name='zebra')
