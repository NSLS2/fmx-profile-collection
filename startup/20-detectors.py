from ophyd import (SingleTrigger, TIFFPlugin, ProsilicaDetector,
                   ImagePlugin, StatsPlugin, ROIPlugin, DetectorBase, HDF5Plugin,
                   AreaDetector)

import ophyd.areadetector.cam as cam

from ophyd.areadetector.filestore_mixins import (FileStoreTIFFIterativeWrite,
                                                 FileStoreHDF5IterativeWrite)

from ophyd import Component as Cpt

class TIFFPluginWithFileStore(TIFFPlugin, FileStoreTIFFIterativeWrite):
    pass

class StandardProsilica(SingleTrigger, ProsilicaDetector):
    image = Cpt(ImagePlugin, 'image1:')
    roi1 = Cpt(ROIPlugin, 'ROI1:')
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats5 = Cpt(StatsPlugin, 'Stats5:')

class StandardProsilicaWithTIFF(StandardProsilica):
    tiff = Cpt(TIFFPluginWithFileStore,
               suffix='TIFF1:',
               write_path_template='/tmp/')

cam_fs1 = StandardProsilicaWithTIFF('XF:17IDA-BI:FMX{FS:1-Cam:1}', name='cam_fs1')
cam_mono = StandardProsilicaWithTIFF('XF:17IDA-BI:FMX{Mono:DCM-Cam:1}', name='cam_mono')

cam_fs2 = StandardProsilicaWithTIFF('XF:17IDA-BI:FMX{FS:2-Cam:1}', name='cam_fs2')
cam_fs3 = StandardProsilicaWithTIFF('XF:17IDA-BI:FMX{FS:3-Cam:1}', name='cam_fs3')
cam_fs4 = StandardProsilicaWithTIFF('XF:17IDC-BI:FMX{FS:4-Cam:1}', name='cam_fs4')
cam_fs5 = StandardProsilicaWithTIFF('XF:17IDC-BI:FMX{FS:5-Cam:1}', name='cam_fs5')

cam_7 = StandardProsilicaWithTIFF('XF:17IDC-ES:FMX{Cam:7}', name='cam_7')
cam_8 = StandardProsilicaWithTIFF('XF:17IDC-ES:FMX{Cam:8}', name='cam_8')

all_standard_pros = [cam_fs1, cam_mono, cam_fs2, cam_fs3, cam_fs4, cam_fs5, cam_7, cam_8]

for camera in all_standard_pros:
    camera.read_attrs = ['stats1', 'stats5', 'tiff']
    camera.stats1.read_attrs = ['total', 'centroid']
    camera.stats5.read_attrs = ['total', 'centroid']
    camera.tiff.read_attrs = []  # leaving just the 'image'

keithley = EpicsSignalRO('XF:17IDC-BI:FMX{Keith:1}readFloat', name='keithley')
