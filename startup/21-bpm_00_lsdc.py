from mxtools.fmx.bpm import Bpm

bpm1 = Bpm('XF:17IDA-BI:FMX{BPM:1}', name='bpm1')
bpm4 = Bpm('XF:17IDC-BI:FMX{BPM:4}', name='bpm4')

bpm1.sum_all.kind = 'hinted'
bpm4.sum_all.kind = 'hinted'

bpm1.sum_all_precision.put(10)
bpm4.sum_all_precision.put(10)
