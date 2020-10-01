# Plans to align beam and goniometer

import epics
import bluesky.preprocessors as bpp
import bluesky.plans as bp
import bluesky.plan_stubs as bps
import numpy as np


def centroid_avg(stats):
    """
    Read centroid X and Y 10x and return mean of centroids.
    
    stats : stats method of ophyd camera object to use, e.g. cam_8.stats4
    
    Examples
    --------
    centroid_avg(cam_8.stats4)
    centroidY = centroid_avg(cam_8.stats4)[1]
    """
    
    centroidXArr = np.zeros(10)
    centroidYArr = np.zeros(10)
    for i in range(0, 10):
        centroidXArr[i] = stats.centroid.x.value
        centroidYArr[i] = stats.centroid.y.value
        # print('Centroid X = {:.6g} px'.format(centroidXArr[i]), ', Centroid Y = {:.6g} px'.format(centroidYArr[i]))
        time.sleep(0.2)
    CentroidX = centroidXArr.mean()
    CentroidY = centroidYArr.mean()
    print('Mean centroid X = {:.6g} px'.format(CentroidX))
    print('Mean centroid Y = {:.6g} px'.format(CentroidY))

    return CentroidX, CentroidY


def beam_center_align(transSet='All'):
    """
    Corrects alignment of goniometer and LSDC center point after a beam drift
    
    Requirements
    ------------
    * No sample mounted. Goniometer will be moved inboard out of sample position
    * Governor in SA state
    
    Parameters
    ----------
    transSet: FMX only: Set to 'RI' if there is a problem with the BCU attenuator.
              FMX only: Set to 'BCU' if there is a problem with the RI attenuator.
              Set to 'None' if there are problems with all attenuators.
              Operator then has to choose a flux by hand that will not saturate scinti
              default = 'All'
              
    Examples
    --------
    RE(beam_center_align())
    RE(beam_center_align(transSet='None'))
    RE(beam_center_align(transSet='RI'))
    """
    # Which beamline?
    blStr = blStrGet()
    if blStr == -1: return -1

    if blStr == 'FMX':
        if transSet not in ['All', 'None', 'BCU', 'RI']:
            print('transSet must be one of: All, None, BCU, RI')
            return -1
    else:
        if transSet not in ['All', 'None']:
            print('transSet must be one of: All, None')
            return -1
        
    if not govStatusGet('SA'):
        print('Not in Governor state SA, exiting')
        return -1
    
    print('Closing detector cover')
    detectorCoverClose()
    
    # Transition to Governor state AB (Auto-align Beam)
    govStateSet('AB')
    
    # Set beam transmission that avoids scintillator saturation
    # Default values are defined in settings as lookup table
    if transSet != 'None':
        transDefault = transDefaultGet( get_energy() )
        if blStr == 'FMX':
            if transSet in ['All', 'BCU']:
                transOrgBCU = trans_get(trans=trans_bcu)
            if transSet in ['All', 'RI']:
                transOrgRI = trans_get(trans=trans_ri)
                yield from trans_set(transDefault, trans=trans_ri)
            if transSet == 'BCU':
                yield from trans_set(transDefault, trans=trans_bcu)
            if transSet == 'All':
                yield from trans_set(1, trans=trans_bcu)
        else:
            transOrgBCU = trans_get(trans=trans_bcu)
            yield from trans_set(transDefault, trans=trans_bcu)
            
    # Retract backlight
    yield from bps.mv(light.y,govPositionGet('li', 'Out'))
    print('Light Y Out')
    
    # ROI1 centroid plugin does not work
    # Copy ROI1 geometry to ROI4 and use ROI4 centroid plugin
    cam_8.roi4.min_xyz.min_x.value = cam_8.roi1.min_xyz.min_x.value
    cam_8.roi4.min_xyz.min_y.value = cam_8.roi1.min_xyz.min_y.value
    cam_8.roi4.size.x.value = cam_8.roi1.size.x.value
    cam_8.roi4.size.y.value = cam_8.roi1.size.y.value
    
    yield from bps.mv(shutter_bcu.open, 1)
    print('BCU Shutter Open')
    
    # Camera calibration [um/px]
    hiMagCal = BL_calibration.HiMagCal.value
    loMagCal = BL_calibration.LoMagCal.value
    
    # Read centroids
    beamHiMagCentroidX = centroid_avg(cam_8)[0]
    beamHiMagCentroidY = centroid_avg(cam_8)[1]

    # Get beam shift on Hi Mag
    # Assume the LSDC centering crosshair is in the center of the FOV
    # This works as long as cam_8 ROI1 does not hit the edge of the cam_8 image
    beamHiMagDiffX = beamHiMagCentroidX - (cam_8.roi4.size.x.value/2)
    beamHiMagDiffY = beamHiMagCentroidY - (cam_8.roi4.size.y.value/2)
    
    # Correct Mag 4 (cam_8 ROI1)
    # Adjust cam_8 ROI1 min_y, LSDC uses this for the Mag4 FOV.
    # This works as long as cam_8 ROI1 does not hit the edge of the cam_8 image
    cam_8.roi1.min_xyz.min_x.value = cam_8.roi1.min_xyz.min_x.value + beamHiMagDiffX
    cam_8.roi1.min_xyz.min_y.value = cam_8.roi1.min_xyz.min_y.value + beamHiMagDiffY
    
    # Correct Mag 3 (cam_8 ROI2)
    cam_8.roi2.min_xyz.min_x.value = cam_8.roi2.min_xyz.min_x.value + beamHiMagDiffX
    cam_8.roi2.min_xyz.min_y.value = cam_8.roi2.min_xyz.min_y.value + beamHiMagDiffY
    
    # Get beam shift on Lo Mag from Hi Mag shift and calibration factor ratio
    beamLoMagDiffX = beamHiMagDiffX * hiMagCal/loMagCal
    beamLoMagDiffY = beamHiMagDiffY * hiMagCal/loMagCal
    
    # Correct Mag 1 (cam_7 ROI2)
    cam_7.roi2.min_xyz.min_x.value = cam_7.roi2.min_xyz.min_x.value + beamLoMagDiffX
    cam_7.roi2.min_xyz.min_y.value = cam_7.roi2.min_xyz.min_y.value + beamLoMagDiffY
    
    # Correct Mag 2 (cam_7 ROI3)
    cam_7.roi3.min_xyz.min_x.value = cam_7.roi3.min_xyz.min_x.value + beamLoMagDiffX
    cam_7.roi3.min_xyz.min_y.value = cam_7.roi3.min_xyz.min_y.value + beamLoMagDiffY
    
    yield from bps.mv(shutter_bcu.close, 1)
    print('BCU Shutter Closed')
    
    # Transition to Governor state SA (Sample Alignment)
    govStateSet('SA')
    
    # Adjust Gonio Y so rotation axis is again aligned to beam
    gonioYDiff = beamHiMagDiffY * hiMagCal
    posGyOld = govPositionGet('gy', 'Work')
    posGyNew = posGyOld + gonioYDiff
    yield from bps.mv(gonio.gy, posGyNew)   # Move Gonio Y to new position
    govPositionSet(posGyNew, 'gy', 'Work')  # Set Governor Gonio Y Work position to new value
    print('Gonio Y difference = %.3f' % gonioYDiff)
    
    # Set previous beam transmission
    if transSet != 'None':
        if blStr == 'FMX':
            if transSet in ['All', 'RI']:
                yield from trans_set(transOrgRI, trans=trans_ri)
            if transSet in ['All', 'BCU']:
                yield from trans_set(transOrgBCU, trans=trans_bcu)
        else:
            yield from trans_set(transOrgBCU, trans=trans_bcu)
    
    
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
    cam.roi4.min_xyz.min_x.value = cam.roi2.min_xyz.min_x.value
    cam.roi4.min_xyz.min_y.value = cam.roi2.min_xyz.min_y.value
    cam.roi4.size.x.value = cam.roi2.size.x.value * 0.25
    cam.roi4.size.y.value = cam.roi2.size.y.value
    cam.roi4.min_xyz.min_x.value = cam.roi2.min_xyz.min_x.value + cam.roi2.size.x.value/2 - cam.roi4.size.x.value/2
    
    # Invert camera image, so dark pin on light image becomes a peak
    cam.proc1.scale.value = -1
    
    # High threshold, so AD centroid doesn't interpret background
    camThresholdOld = cam.stats4.centroid_threshold.value
    cam.stats4.centroid_threshold.value = 150
    
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
    cam.proc1.scale.value = 1
    
    # Set thresold to previous value
    cam.stats4.centroid_threshold.value = camThresholdOld
    
    
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
    cam_7.proc1.scale.value = -1
    cam_8.proc1.scale.value = -1
    
    # High threshold, so AD centroid doesn't interpret background
    cam_8ThresholdOld = cam_8.stats4.centroid_threshold.value
    cam_8.stats4.centroid_threshold.value = 150
    cam_7ThresholdOld = cam_7.stats4.centroid_threshold.value
    cam_7.stats4.centroid_threshold.value = 150
    
    # HiMag
    # Copy ROI2 geometry (HiMag Mag3) to ROI4 and use ROI4 centroid plugin
    cam_8.roi4.min_xyz.min_x.value = cam_8.roi2.min_xyz.min_x.value
    cam_8.roi4.min_xyz.min_y.value = cam_8.roi2.min_xyz.min_y.value
    cam_8.roi4.size.x.value = cam_8.roi2.size.x.value * 0.20
    cam_8.roi4.size.y.value = cam_8.roi2.size.y.value
    cam_8.roi4.min_xyz.min_x.value = cam_8.roi2.min_xyz.min_x.value + cam_8.roi2.size.x.value/2 - cam_8.roi4.size.x.value/2
    
    # LoMag
    # Copy ROI2 geometry (LoMag Mag1) to ROI4 and use ROI4 centroid plugin
    cam_7.roi4.min_xyz.min_x.value = cam_7.roi2.min_xyz.min_x.value
    cam_7.roi4.min_xyz.min_y.value = cam_7.roi2.min_xyz.min_y.value
    cam_7.roi4.size.x.value = cam_7.roi2.size.x.value * 0.05
    cam_7.roi4.size.y.value = cam_7.roi2.size.y.value
    cam_7.roi4.min_xyz.min_x.value = cam_7.roi2.min_xyz.min_x.value + cam_7.roi2.size.x.value/2 - cam_7.roi4.size.x.value/2
    
    centerPinYHiMag0 = centroid_avg(cam_8.stats4)[1]
    centerPinYLoMag0 = centroid_avg(cam_7.stats4)[1]
    yield from bps.mvr(gonio.o,180)
    time.sleep(2)
    centerPinYHiMag180 = centroid_avg(cam_8.stats4)[1]
    centerPinYLoMag180 = centroid_avg(cam_7.stats4)[1]
    centerPinYHiMag = (centerPinYHiMag0 + centerPinYHiMag180)/2
    centerPinYLoMag = (centerPinYLoMag0 + centerPinYLoMag180)/2

    centerPinOffsYHiMag = centerPinYHiMag - cam_8.roi4.size.y.value / 2
    centerPinOffsYLoMag = centerPinYLoMag - cam_7.roi4.size.y.value / 2
    
    # Correct Mag 3 (cam_8 ROI2)
    cam_8.roi2.min_xyz.min_y.value = cam_8.roi2.min_xyz.min_y.value + centerPinOffsYHiMag
    # Correct Mag 4 (cam_8 ROI1)
    cam_8.roi1.min_xyz.min_y.value = cam_8.roi2.min_xyz.min_y.value + (cam_8.roi2.size.y.value-cam_8.roi1.size.y.value)/2
    
    # Correct Mag 1 (cam_7 ROI2)
    cam_7.roi2.min_xyz.min_y.value = cam_7.roi2.min_xyz.min_y.value + centerPinOffsYLoMag
    # Correct Mag 2 (cam_7 ROI3)
    cam_7.roi3.min_xyz.min_y.value = cam_7.roi2.min_xyz.min_y.value + (cam_7.roi2.size.y.value-cam_7.roi3.size.y.value)/2

    # De-invert image
    cam_7.proc1.scale.value = -1
    cam_8.proc1.scale.value = -1
    
    # Set thresold to previous value
    cam_8.stats4.centroid_threshold.value = cam_8ThresholdOld
    cam_7.stats4.centroid_threshold.value = cam_7ThresholdOld
    
    return
