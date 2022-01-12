import ophyd.areadetector.cam as cam # Is this used anywhere?

from ophyd.areadetector.filestore_mixins import (FileStoreTIFFIterativeWrite,
                                                 FileStoreHDF5IterativeWrite)

class TIFFPluginWithFileStore(TIFFPlugin, FileStoreTIFFIterativeWrite):
    pass

class StandardProsilicaWithTIFF(StandardProsilica):
    tiff = Cpt(TIFFPluginWithFileStore,
               suffix='TIFF1:',
               write_path_template='/tmp/',
               root='/tmp')

#cam_fs1_tiff = StandardProsilicaWithTIFF('XF:17IDA-BI:FMX{FS:1-Cam:1}', name='cam_fs1_tiff')
#cam_mono_tiff = StandardProsilicaWithTIFF('XF:17IDA-BI:FMX{Mono:DCM-Cam:1}', name='cam_mono_tiff')
#cam_fs2_tiff = StandardProsilicaWithTIFF('XF:17IDA-BI:FMX{FS:2-Cam:1}', name='cam_fs2_tiff')
#cam_fs3_tiff = StandardProsilicaWithTIFF('XF:17IDA-BI:FMX{FS:3-Cam:1}', name='cam_fs3_tiff')
#cam_fs4_tiff = StandardProsilicaWithTIFF('XF:17IDC-BI:FMX{FS:4-Cam:1}', name='cam_fs4_tiff')
#cam_fs5_tiff = StandardProsilicaWithTIFF('XF:17IDC-BI:FMX{FS:5-Cam:1}', name='cam_fs5_tiff')
#cam_7_tiff = StandardProsilicaWithTIFF('XF:17IDC-ES:FMX{Cam:7}', name='cam_7_tiff')
#cam_8_tiff = StandardProsilicaWithTIFF('XF:17IDC-ES:FMX{Cam:8}', name='cam_8_tiff')

#all_standard_pros_tiff = [cam_fs1_tiff, cam_mono_tiff, cam_fs2_tiff, cam_fs3_tiff, cam_fs4_tiff, cam_fs5_tiff, cam_7_tiff, cam_8_tiff]
#for camera in all_standard_pros_tiff:
#    camera.read_attrs = ['stats1', 'stats2', 'stats3', 'stats4', 'stats5', 'tiff']
#    camera.stats1.read_attrs = ['total', 'centroid']
#    camera.stats2.read_attrs = ['total', 'centroid']
#    camera.stats3.read_attrs = ['total', 'centroid']
#    camera.stats4.read_attrs = ['total', 'centroid']
#    camera.stats5.read_attrs = ['total', 'centroid']
#    camera.tiff.read_attrs = []  # leaving just the 'image'

