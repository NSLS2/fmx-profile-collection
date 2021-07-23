from ophyd import PVPositioner, PVPositionerPC, Device, Component as Cpt, EpicsMotor, EpicsSignal, EpicsSignalRO

class YMotor(Device):
	y = Cpt(EpicsMotor, '-Ax:Y}Mtr', labels=['fmx'])

class XYMotor(Device):
	x = Cpt(EpicsMotor, '-Ax:X}Mtr', labels=['fmx'])
	y = Cpt(EpicsMotor, '-Ax:Y}Mtr', labels=['fmx'])

class XYZMotor(XYMotor):
	z = Cpt(EpicsMotor, '-Ax:Z}Mtr', labels=['fmx'])

class XZXYMotor(Device):
	x = Cpt(EpicsMotor, '-Ax:X}Mtr', labels=['fmx'])
	z = Cpt(EpicsMotor, '-Ax:Z}Mtr', labels=['fmx'])

class XYZfMotor(Device):
	x = Cpt(EpicsMotor, '-Ax:Xf}Mtr')
	y = Cpt(EpicsMotor, '-Ax:Yf}Mtr')
	z = Cpt(EpicsMotor, '-Ax:Zf}Mtr')

class Slits(Device):
	b = Cpt(EpicsMotor, '-Ax:B}Mtr', labels=['fmx'])
	i = Cpt(EpicsMotor, '-Ax:I}Mtr', labels=['fmx'])
	o = Cpt(EpicsMotor, '-Ax:O}Mtr', labels=['fmx'])
	t = Cpt(EpicsMotor, '-Ax:T}Mtr', labels=['fmx'])
	x_ctr = Cpt(EpicsMotor, '-Ax:XCtr}Mtr', labels=['fmx'])
	x_gap = Cpt(EpicsMotor, '-Ax:XGap}Mtr', labels=['fmx'])
	y_ctr = Cpt(EpicsMotor, '-Ax:YCtr}Mtr', labels=['fmx'])
	y_gap = Cpt(EpicsMotor, '-Ax:YGap}Mtr', labels=['fmx'])

class VirtualCenter(PVPositioner):
	setpoint = Cpt(EpicsSignal, 'center')
	readback = Cpt(EpicsSignalRO, 't2.D')
	done = Cpt(EpicsSignalRO, 'DMOV')
	done_value = 1

class VirtualGap(PVPositioner):
	setpoint = Cpt(EpicsSignal, 'size')
	readback = Cpt(EpicsSignalRO, 't2.C')
	done = Cpt(EpicsSignalRO, 'DMOV')
	done_value = 1

class HorizontalDCM(Device):
	b = Cpt(EpicsMotor, '-Ax:B}Mtr', labels=['fmx'])
	g = Cpt(EpicsMotor, '-Ax:G}Mtr', labels=['fmx'])
	p = Cpt(EpicsMotor, '-Ax:P}Mtr', labels=['fmx'])
	r = Cpt(EpicsMotor, '-Ax:R}Mtr', labels=['fmx'])
	e = Cpt(EpicsMotor, '-Ax:E}Mtr', labels=['fmx'])
	w = Cpt(EpicsMotor, '-Ax:W}Mtr', labels=['fmx'])

class VerticalDCM(Device):
    b = Cpt(EpicsMotor, '-Ax:B}Mtr')
    g = Cpt(EpicsMotor, '-Ax:G}Mtr')
    p = Cpt(EpicsMotor, '-Ax:P}Mtr')
    r = Cpt(EpicsMotor, '-Ax:R}Mtr')
    e = Cpt(EpicsMotor, '-Ax:E}Mtr')
    w = Cpt(EpicsMotor, '-Ax:W}Mtr')

class Cover(Device):
    close = Cpt(EpicsSignal, 'Cmd:Cls-Cmd')
    open = Cpt(EpicsSignal, 'Cmd:Opn-Cmd')
    status = Cpt(EpicsSignalRO, 'Pos-Sts') # status: 0 (Not Open), 1 (Open)

class Shutter(Device):
    close = Cpt(EpicsSignal, 'Cmd:Cls-Cmd.PROC')
    open = Cpt(EpicsSignal, 'Cmd:Opn-Cmd.PROC')
    status = Cpt(EpicsSignalRO, 'Pos-Sts') # status: 0 (Open), 1 (Closed), 2 (Undefined)
    
class ShutterTranslation(Device):
	x = Cpt(EpicsMotor, '-Ax:X}Mtr')

class GoniometerStack(Device):
	gx = Cpt(EpicsMotor, '-Ax:GX}Mtr', labels=['fmx'])
	gy = Cpt(EpicsMotor, '-Ax:GY}Mtr', labels=['fmx'])
	gz = Cpt(EpicsMotor, '-Ax:GZ}Mtr', labels=['fmx'])
	o  = Cpt(EpicsMotor, '-Ax:O}Mtr', labels=['fmx'])
	py = Cpt(EpicsMotor, '-Ax:PY}Mtr', labels=['fmx'])
	pz = Cpt(EpicsMotor, '-Ax:PZ}Mtr', labels=['fmx'])

class BeamStop(Device):
	fx = Cpt(EpicsMotor, '-Ax:FX}Mtr', labels=['fmx'])
	fy = Cpt(EpicsMotor, '-Ax:FY}Mtr', labels=['fmx'])
    
class Annealer(Device):
    air = Cpt(EpicsSignal, 'Air-Sel')
    status = Cpt(EpicsSignalRO, 'In-Sts') # status: 0 (Not In), 1 (In)
      

#######################################################
### FMX
#######################################################

## Horizontal Double Crystal Monochromator (FMX)
hdcm = HorizontalDCM('XF:17IDA-OP:FMX{Mono:DCM', name='hdcm')

# Vertical Double Crystal Monochromator (AMX)
vdcm = VerticalDCM('XF:17IDA-OP:AMX{Mono:DCM', name='vdcm')

## 17-ID-A FOE shutter
shutter_foe = Shutter('XF:17ID-PPS:FAMX{Sh:FE}', name='shutter_foe',
                 read_attrs=['status'])

## 17-ID-C experimental hutch shutter
shutter_hutch_c = Shutter('XF:17IDA-PPS:FMX{PSh}', name='shutter_hutch_c',
                 read_attrs=['status'])

## FMX BCU shutter
shutter_bcu = Shutter('XF:17IDC-ES:FMX{Gon:1-Sht}', name='shutter_bcu',
                 read_attrs=['status'])

## Beam Conditioning Unit Shutter Translation
sht = ShutterTranslation('XF:17IDC-ES:FMX{Sht:1', name='sht')

## Eiger16M detector cover
cover_detector = Cover('XF:17IDC-ES:FMX{Det:FMX-Cover}', name='cover_detector',
                 read_attrs=['status'])

## Slits Motions
slits1 = Slits('XF:17IDA-OP:FMX{Slt:1', name='slits1', labels=['fmx'])
slits2 = Slits('XF:17IDC-OP:FMX{Slt:2', name='slits2', labels=['fmx'])
slits3 = Slits('XF:17IDC-OP:FMX{Slt:3', name='slits3', labels=['fmx'])
slits4 = Slits('XF:17IDC-OP:FMX{Slt:4', name='slits4', labels=['fmx'])
slits5 = Slits('XF:17IDC-OP:FMX{Slt:5', name='slits5', labels=['fmx'])

## BPM Motions
mbpm1 = XYMotor('XF:17IDA-BI:FMX{BPM:1', name='mbpm1')
mbpm2 = XYMotor('XF:17IDC-BI:FMX{BPM:2', name='mbpm2')
mbpm3 = XYMotor('XF:17IDC-BI:FMX{BPM:3', name='mbpm3')

## Collimator
colli = XZXYMotor('XF:17IDC-ES:FMX{Colli:1', name='colli')

## Microscope
mic = XYMotor('XF:17IDC-ES:FMX{Mic:1', name='mic')
light = YMotor('XF:17IDC-ES:FMX{Light:1', name='lightY')

## Holey Mirror
hm = XYZMotor('XF:17IDC-ES:FMX{Mir:1', name='hm')

## Goniometer Stack
gonio = GoniometerStack('XF:17IDC-ES:FMX{Gon:1', name='gonio')

## PI Scanner Fine Stages
pif = XYZfMotor('XF:17IDC-ES:FMX{Gon:1', name='pif')

## Beam Stop
bs = BeamStop('XF:17IDC-ES:FMX{BS:1', name='bs')

## FMX annealer aka cryo blocker
annealer = Annealer('XF:17IDC-ES:FMX{Wago:1}Annealer', name='annealer',
                        read_attrs=[],
                        labels=['fmx'])


