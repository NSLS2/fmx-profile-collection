# Plans to align beam and goniometer

import epics
import bluesky.preprocessors as bpp
import bluesky.plans as bp
import bluesky.plan_stubs as bps
import numpy as np


# Goniometer align functions

def center_pin(cam=cam_8):
    """
    Centers a pin in Y
    
    Requirements
    ------------
    * Alignment pin mounted. Pin should be aligned in X to within 0.25 of the Mag3 width
    
    Parameters
    ----------
    cam: ophyd camera device. Should be cam_7 or cam_8 (default)
    
    Examples
    --------
    RE(center_pin())
    RE(center_pin(cam_7))
    """
    
    if cam not in [cam_7, cam_8]:
        print('cam must be one of: [cam_7, cam_8]')
        return -1
    
    # Copy ROI2 geometry (HiMag Mag3 and LoMag Mag1) to ROI4 and use ROI4 centroid plugin
    cam.roi4.min_xyz.min_x.put(cam.roi2.min_xyz.min_x.get())
    cam.roi4.min_xyz.min_y.put(cam.roi2.min_xyz.min_y.get())
    cam.roi4.size.x.put(cam.roi2.size.x.get() * 0.25)
    cam.roi4.size.y.put(cam.roi2.size.y.get())
    cam.roi4.min_xyz.min_x.put(cam.roi2.min_xyz.min_x.get() + cam.roi2.size.x.get()/2 - cam.roi4.size.x.get()/2)
    
    # Invert camera image, so dark pin on light image becomes a peak
    cam.proc1.scale.put(-1)
    
    # High threshold, so AD centroid doesn't interpret background
    camThresholdOld = cam.stats4.centroid_threshold.get()
    cam.stats4.centroid_threshold.put(150)
    
    # Get centroids at Omega = 0, 90, 180, 270 deg
    yield from bps.mv(gonio.o,0)
    time.sleep(2)
    c0 = centroid_avg(cam.stats4)[1]
    
    yield from bps.mv(gonio.o,90)
    time.sleep(2)
    c90 = centroid_avg(cam.stats4)[1]
    
    yield from bps.mv(gonio.o,180)
    time.sleep(2)
    c180 = centroid_avg(cam.stats4)[1]
    
    yield from bps.mv(gonio.o,270)
    time.sleep(2)
    c270 = centroid_avg(cam.stats4)[1]
    
    # Camera calibration [um/px]
    if cam==cam_8:
        camCal = BL_calibration.HiMagCal.get()
    elif cam==cam_7:
        camCal = BL_calibration.LoMagCal.get()
    
    # Center offset Y
    offsY = ((c180 - c0))/2 * camCal
    print('Y offset = {:.6g} um'.format(offsY))
    
    # Center offset Z
    offsZ = ((c270 - c90))/2 * camCal
    print('Z offset = {:.6g} um'.format(offsZ))
    
    # Move pin to center
    yield from bps.mvr(gonio.py,offsY)
    yield from bps.mvr(gonio.pz,offsZ)
    
    # De-invert image
    cam.proc1.scale.put(1)
    
    # Set thresold to previous value
    cam.stats4.centroid_threshold.put(camThresholdOld)
    
    
def gonio_axis_align():
    """
    Center crosshair on pin
    
    Requirements
    ------------
    * Alignment pin mounted and centered. Pin should be aligned in X to within 0.25 of the Mag3 width
    * Governor in SA state
    * LoMag and HiMag Scale and Offset need to be enabled in Proc1
        * XF:17IDC-ES:FMX{Cam:7}Proc1:EnableOffsetScale
        * XF:17IDC-ES:FMX{Cam:8}Proc1:EnableOffsetScale
    """
    
    # Invert camera image, so dark pin on light image becomes a peak
    cam_7.proc1.scale.put(-1)
    cam_8.proc1.scale.put(-1)
    
    # High threshold, so AD centroid doesn't interpret background
    cam_8ThresholdOld = cam_8.stats4.centroid_threshold.get()
    cam_8.stats4.centroid_threshold.put(150)
    cam_7ThresholdOld = cam_7.stats4.centroid_threshold.get()
    cam_7.stats4.centroid_threshold.put(150)
    
    # HiMag
    # Copy ROI2 geometry (HiMag Mag3) to ROI4 and use ROI4 centroid plugin
    cam_8.roi4.min_xyz.min_x.put(cam_8.roi2.min_xyz.min_x.get())
    cam_8.roi4.min_xyz.min_y.put(cam_8.roi2.min_xyz.min_y.get())
    cam_8.roi4.size.x.put(cam_8.roi2.size.x.get() * 0.20)
    cam_8.roi4.size.y.put(cam_8.roi2.size.y.get())
    cam_8.roi4.min_xyz.min_x.put(cam_8.roi2.min_xyz.min_x.get() + cam_8.roi2.size.x.get()/2 - cam_8.roi4.size.x.get()/2)
    
    # LoMag
    # Copy ROI2 geometry (LoMag Mag1) to ROI4 and use ROI4 centroid plugin
    cam_7.roi4.min_xyz.min_x.put(cam_7.roi2.min_xyz.min_x.get())
    cam_7.roi4.min_xyz.min_y.put(cam_7.roi2.min_xyz.min_y.get())
    cam_7.roi4.size.x.put(cam_7.roi2.size.x.get() * 0.05)
    cam_7.roi4.size.y.put(cam_7.roi2.size.y.get())
    cam_7.roi4.min_xyz.min_x.put(cam_7.roi2.min_xyz.min_x.get() + cam_7.roi2.size.x.get()/2 - cam_7.roi4.size.x.get()/2)
    
    centerPinYHiMag0 = centroid_avg(cam_8.stats4)[1]
    centerPinYLoMag0 = centroid_avg(cam_7.stats4)[1]
    yield from bps.mvr(gonio.o,180)
    time.sleep(2)
    centerPinYHiMag180 = centroid_avg(cam_8.stats4)[1]
    centerPinYLoMag180 = centroid_avg(cam_7.stats4)[1]
    centerPinYHiMag = (centerPinYHiMag0 + centerPinYHiMag180)/2
    centerPinYLoMag = (centerPinYLoMag0 + centerPinYLoMag180)/2

    centerPinOffsYHiMag = centerPinYHiMag - cam_8.roi4.size.y.get() / 2
    centerPinOffsYLoMag = centerPinYLoMag - cam_7.roi4.size.y.get() / 2
    
    # Correct Mag 3 (cam_8 ROI2)
    cam_8.roi2.min_xyz.min_y.put(cam_8.roi2.min_xyz.min_y.get() + centerPinOffsYHiMag)
    # Correct Mag 4 (cam_8 ROI1)
    cam_8.roi1.min_xyz.min_y.put(cam_8.roi2.min_xyz.min_y.get() + (cam_8.roi2.size.y.get()-cam_8.roi1.size.y.get())/2)
    
    # Correct Mag 1 (cam_7 ROI2)
    cam_7.roi2.min_xyz.min_y.put(cam_7.roi2.min_xyz.min_y.get() + centerPinOffsYLoMag)
    # Correct Mag 2 (cam_7 ROI3)
    cam_7.roi3.min_xyz.min_y.put(cam_7.roi2.min_xyz.min_y.get() + (cam_7.roi2.size.y.get()-cam_7.roi3.size.y.get())/2)

    # De-invert image
    cam_7.proc1.scale.put(-1)
    cam_8.proc1.scale.put(-1)
    
    # Set thresold to previous value
    cam_8.stats4.centroid_threshold.put(cam_8ThresholdOld)
    cam_7.stats4.centroid_threshold.put(cam_7ThresholdOld)
    
    return
