class FESlits(Device):
	i = Cpt(EpicsMotor, '{Slt:3-Ax:I}Mtr')
	t = Cpt(EpicsMotor, '{Slt:3-Ax:T}Mtr')
	o = Cpt(EpicsMotor, '{Slt:4-Ax:O}Mtr')
	b = Cpt(EpicsMotor, '{Slt:4-Ax:B}Mtr')
	x_ctr = Cpt(VirtualCenter, '{Slt:34-Ax:X}')
	y_ctr = Cpt(VirtualCenter, '{Slt:34-Ax:Y}')
	x_gap = Cpt(VirtualGap,    '{Slt:34-Ax:X}')
	y_gap = Cpt(VirtualGap,    '{Slt:34-Ax:Y}')

class XYPitchMotor(XYMotor):
	pitch = Cpt(EpicsMotor, '-Ax:P}Mtr')

class KBMirror(Device):
	hp = Cpt(EpicsMotor, ':KBH-Ax:P}Mtr')
	hr = Cpt(EpicsMotor, ':KBH-Ax:R}Mtr')
	hx = Cpt(EpicsMotor, ':KBH-Ax:X}Mtr')
	hy = Cpt(EpicsMotor, ':KBH-Ax:Y}Mtr')
	vp = Cpt(EpicsMotor, ':KBV-Ax:P}Mtr')
	vx = Cpt(EpicsMotor, ':KBV-Ax:X}Mtr')
	vy = Cpt(EpicsMotor, ':KBV-Ax:Y}Mtr')

#######################################################
### FMX
#######################################################

## FE Slits
fe = FESlits('FE:C17A-OP', name='fe')

## High Heat Load Slits
hhls = Slits('XF:17IDA-OP:FMX{Slt:0', name='hhls', labels=['fmx'])

## Horizontal Focusing Mirror - XYPitchMotor
hfm = XYPitchMotor('XF:17IDA-OP:FMX{Mir:HFM', name='hfm')

## KB Mirror
kbm = KBMirror('XF:17IDC-OP:FMX{Mir', name='kbm')

