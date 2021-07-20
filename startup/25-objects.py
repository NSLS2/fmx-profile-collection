from mxtools.vector_program import VectorProgram
from mxtools.zebra import Zebra
from mxtools.flyer import MXFlyer, actual_scan

vector = VectorProgram('XF:17IDC-ES:FMX{Gon:1-Vec}', name='vector')
zebra = Zebra('XF:17IDC-ES:FMX{Zeb:3}:', name='zebra')
mx_flyer = MXFlyer(vector=vector, zebra=zebra, eiger=eiger_single)
