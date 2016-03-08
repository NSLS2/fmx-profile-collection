from ophyd import Device, Component as Cpt, EpicsMotor, EpicsSignalRO


class XYMotor(Device):
	x = Cpt(EpicsMotor, '-Ax:X}Mtr')
	y = Cpt(EpicsMotor, '-Ax:Y}Mtr')


class XYPitchMotor(XYMotor):
	pitch = Cpt(EpicsMotor, '-Ax:P}Mtr')


class Slits(Device):
	b = Cpt(EpicsMotor, '-Ax:B}Mtr')
	i = Cpt(EpicsMotor, '-Ax:I}Mtr')
	o = Cpt(EpicsMotor, '-Ax:O}Mtr')
	t = Cpt(EpicsMotor, '-Ax:T}Mtr')
	x_ctr = Cpt(EpicsMotor, '-Ax:XCtr}Mtr')
	x_gap = Cpt(EpicsMotor, '-Ax:XGap}Mtr')
	y_ctr = Cpt(EpicsMotor, '-Ax:YCtr}Mtr')
	y_gap = Cpt(EpicsMotor, '-Ax:YGap}Mtr')


class HorizontalDCM(Device):
	b = Cpt(EpicsMotor, '-Ax:B}Mtr')
	g = Cpt(EpicsMotor, '-Ax:G}Mtr')
	p = Cpt(EpicsMotor, '-Ax:P}Mtr')
	r = Cpt(EpicsMotor, '-Ax:R}Mtr')


class KBMirror(Device):
	hp = Cpt(EpicsMotor, ':KBH-Ax:P}Mtr')
	hr = Cpt(EpicsMotor, ':KBH-Ax:R}Mtr')
	hx = Cpt(EpicsMotor, ':KBH-Ax:X}Mtr')
	hy = Cpt(EpicsMotor, ':KBH-Ax:Y}Mtr')
	vp = Cpt(EpicsMotor, ':KBV-Ax:P}Mtr')
	vx = Cpt(EpicsMotor, ':KBV-Ax:X}Mtr')
	vy = Cpt(EpicsMotor, ':KBV-Ax:Y}Mtr')


class GoniometerStack(Device):
	gx = Cpt(EpicsMotor, '-Ax:GX}Mtr')
	gy = Cpt(EpicsMotor, '-Ax:GY}Mtr')
	gz = Cpt(EpicsMotor, '-Ax:GZ}Mtr')
	o = Cpt(EpicsMotor, '-Ax:O}Mtr')
	py = Cpt(EpicsMotor, '-Ax:PY}Mtr')
	pz = Cpt(EpicsMotor, '-Ax:PZ}Mtr')

class ShutterTranslation(Device):
	x = Cpt(EpicsMotor, '-Ax:X}Mtr')

#######################################################
### FMX
#######################################################

## High Heat Load Slits
hhls = Slits('XF:17IDA-OP:FMX{Slt:0', name='hhls')

## Horizontal Double Crystal Monochromator
hdcm = HorizontalDCM('XF:17IDA-OP:FMX{Mono:DCM', name='hdcm')

## Horizontal Focusing Mirror - XYPitchMotor
hfm = XYPitchMotor('XF:17IDA-OP:FMX{Mir:HFM', name='hfm')

## BPM Motions
mbpm1 = XYMotor('XF:17IDA-BI:FMX{BPM:1', name='mbpm1')
mbpm2 = XYMotor('XF:17IDC-BI:FMX{BPM:2', name='mbpm2')
mbpm3 = XYMotor('XF:17IDC-BI:FMX{BPM:3', name='mbpm3')

## Slits Motions
slits1 = Slits('XF:17IDA-OP:FMX{Slt:1', name='slits1')
slits2 = Slits('XF:17IDC-OP:FMX{Slt:2', name='slits2')
slits3 = Slits('XF:17IDC-OP:FMX{Slt:3', name='slits3')

## KB Mirror
kbm = KBMirror('XF:17IDC-OP:FMX{Mir', name='kbm')

## Microscope
mic = XYMotor('XF:17IDC-ES:FMX{Mic:1', name='mic')

## Goniometer Stack
gonio = GoniometerStack('XF:17IDC-ES:FMX{Gon:1', name='gonio')

## Beam Conditioning Unit Shutter Translation
sht = ShutterTranslation('XF:17IDC-ES:FMX{Sht:1', name='sht')


