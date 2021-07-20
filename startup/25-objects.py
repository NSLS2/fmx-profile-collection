from mxtools.vector_program import VectorProgram
from mxtools.zebra import Zebra
from mxtools.flyer import MXFlyer, actual_scan
from mxtools.eiger import EigerSingleTriggerV26, set_eiger_defaults

vector = VectorProgram('XF:17IDC-ES:FMX{Gon:1-Vec}', name='vector')
zebra = Zebra('XF:17IDC-ES:FMX{Zeb:3}:', name='zebra')
eiger_single = EigerSingleTriggerV26("XF:17IDC-ES:FMX{Det:Eig16M}", name="eiger_single")
# TODO: uncomment for V33
# eiger_single.cam.ensure_nonblocking()
set_eiger_defaults(eiger_single)
mx_flyer = MXFlyer(vector=vector, zebra=zebra, eiger=eiger_single)
