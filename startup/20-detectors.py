from ophyd import (SingleTrigger, TIFFPlugin,
                   ImagePlugin, StatsPlugin, ROIPlugin, DetectorBase, HDF5Plugin,
                   AreaDetector)

import ophyd.areadetector.cam as cam

from ophyd.areadetector.filestore_mixins import (FileStoreTIFFIterativeWrite,
                                                 FileStoreHDF5IterativeWrite)

from ophyd import Component as Cpt

class FMXProsilicaDetector(DetectorBase):
    _html_docs = ['prosilicaDoc.html']
    cam = Cpt(cam.ProsilicaDetectorCam, '')

class StandardProsilica(SingleTrigger, FMXProsilicaDetector):
    #tiff = Cpt(TIFFPluginWithFileStore,
    #           suffix='TIFF1:',
    #           write_path_template='/XF16ID/data/')
    image = Cpt(ImagePlugin, 'image1:')
    roi1 = Cpt(ROIPlugin, 'ROI1:')
    roi2 = Cpt(ROIPlugin, 'ROI2:')
    roi3 = Cpt(ROIPlugin, 'ROI3:')
    roi4 = Cpt(ROIPlugin, 'ROI4:')
    roi5 = Cpt(ROIPlugin, 'ROI5:')
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats2 = Cpt(StatsPlugin, 'Stats2:')
    stats3 = Cpt(StatsPlugin, 'Stats3:')
    stats4 = Cpt(StatsPlugin, 'Stats4:')
    stats5 = Cpt(StatsPlugin, 'Stats5:')

cam_fs1 = StandardProsilica('XF:17IDA-BI:FMX{FS:1-Cam:1}', name='cam_fs1')
cam_mono = StandardProsilica('XF:17IDA-BI:FMX{Mono:DCM-Cam:1}', name='cam_mono')

cam_fs2 = StandardProsilica('XF:17IDA-BI:FMX{FS:2-Cam:1}', name='cam_fs2')
cam_fs3 = StandardProsilica('XF:17IDA-BI:FMX{FS:3-Cam:1}', name='cam_fs3')
cam_fs5 = StandardProsilica('XF:17IDC-BI:FMX{FS:5-Cam:1}', name='cam_fs5')

cam_7 = StandardProsilica('XF:17IDC-ES:FMX{Cam:7}', name='cam_7')
cam_8 = StandardProsilica('XF:17IDC-ES:FMX{Cam:8}', name='cam_8')

all_standard_pros = [cam_fs1, cam_mono, cam_fs2, cam_fs3, cam_fs5, cam_7, cam_8]

for camera in all_standard_pros:
    camera.read_attrs = ['stats1', 'stats2','stats3','stats4','stats5']  #, 'tiff']
    #camera.tiff.read_attrs = []  # leaving just the 'image'
    camera.stats1.read_attrs = ['total', 'centroid']
    camera.stats2.read_attrs = ['total', 'centroid']
    camera.stats3.read_attrs = ['total', 'centroid']
    camera.stats4.read_attrs = ['total', 'centroid']
    camera.stats5.read_attrs = ['total', 'centroid']
