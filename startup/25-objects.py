from mxtools.vector_program import VectorProgram
from mxtools.zebra import Zebra
from mxtools.flyer import MXFlyer
from mxtools.eiger import EigerSingleTriggerV26, set_eiger_defaults
from mxtools.handlers import EigerHandlerMX


db.reg.register_handler(EigerHandlerMX.spec, EigerHandlerMX)

vector = VectorProgram('XF:17IDC-ES:FMX{Gon:1-Vec}', name='vector')
zebra = Zebra('XF:17IDC-ES:FMX{Zeb:3}:', name='zebra')
eiger_single = EigerSingleTriggerV26("XF:17IDC-ES:FMX{Det:Eig16M}",
                                     name="eiger_single")
# TODO: uncomment for V33
# eiger_single.cam.ensure_nonblocking()
set_eiger_defaults(eiger_single)
mx_flyer = MXFlyer(vector=vector, zebra=zebra, detector=eiger_single)

# example call of the above flyer
#import bluesky.plans as bp
#mx_flyer.update_parameters(angle_start=1.0, scan_width=100, img_width=0.1, exposure_period_per_image=0.01, detector_dead_time=3.38e-6, num_images=1800, x_beam=500, y_beam=600, wavelength=1.0, det_distance_m=0.4, file_prefix="testmxflyer",data_directory_name="/GPFS/CENTRAL/xf17id2/jaishima/20211118/"file_number_start=1)
#RE(bp.fly([mx_flyer]))
