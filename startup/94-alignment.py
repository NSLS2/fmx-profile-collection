# Plans to align beam and goniometer

import epics
import bluesky.preprocessors as bpp
import bluesky.plans as bp
import bluesky.plan_stubs as bps
import numpy as np


def centroid_avg(cam):
    # Read centroids 10x and use mean
    centroidXArr = np.zeros(10)
    centroidYArr = np.zeros(10)
    for i in range(0, 10):
        centroidXArr[i] = cam.stats4.centroid.x.value
        centroidYArr[i] = cam.stats4.centroid.y.value
        # print('Centroid X = {:.6g} px'.format(centroidXArr[i]), ', Centroid Y = {:.6g} px'.format(centroidYArr[i]))
        time.sleep(0.2)
    CentroidX = centroidXArr.mean()
    CentroidY = centroidYArr.mean()
    print('Mean centroid X = {:.6g} px'.format(CentroidX))
    print('Mean centroid Y = {:.6g} px'.format(CentroidY))

    return CentroidX, CentroidY


def beam_center_align(attenSet='All'):
    """
    Corrects alignment of goniometer and LSDC center point after a beam drift
    
    Requirements
    ------------
    * No sample mounted. Goniometer will be moved inboard out of sample position
    * Governor in SA state
    
    Parameters
    ----------
    attenSet: FMX only: Set to 'RI' if there is a problem with the BCU attenuator.
              FMX only: Set to 'BCU' if there is a problem with the RI attenuator.
              Set to 'None' if there are problems with all = attenuators.
              Operator then has to choose a flux by hand that will not saturate scinti
              default = 'All'
              
    Examples
    --------
    RE(beam_center_align())
    RE(beam_center_align(attenSet='None'))
    RE(beam_center_align(attenSet='RI'))
    """
    # Which beamline?
    blStr = blStrGet()
    if blStr == -1: return -1

    if blStr == 'FMX':
        if attenSet not in ['All', 'None', 'BCU', 'RI']:
            print('attenSet must be one of: All, None, BCU, RI')
            return -1
    else:
        if attenSet not in ['All', 'None']:
            print('attenSet must be one of: All, None')
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
    if attenSet != 'None':
        attenDefault = attenDefaultGet( get_energy() )
        if blStr == 'FMX':
            if attenSet in ['All', 'BCU']:
                attenOrgBCU = atten_get(attenuator='BCU')
            if attenSet in ['All', 'RI']:
                attenOrgRI = atten_get(attenuator='RI')
                atten_set(attenDefault, attenuator='RI')
            if attenSet == 'BCU':
                atten_set(attenDefault, attenuator='BCU')
            if attenSet == 'All':
                atten_set(1, attenuator='BCU')
        else:
            attenOrgBCU = atten_get(attenuator='BCU')
            atten_set(attenDefault, attenuator='BCU')
            
    # Retract backlight
    yield from bps.mv(light.y,govPositionGet('li', 'Out'))
    print('Light Y Out')
    
    # ROI1 centroid plugin does not work
    # Copy ROI1 geometry to ROI4 and use ROI4 centroid plugin
    cam_8.roi4.min_xyz.min_x.value = cam_8.roi1.min_xyz.min_x.value
    cam_8.roi4.min_xyz.min_y.value = cam_8.roi1.min_xyz.min_y.value
    cam_8.roi4.size.x.value = cam_8.roi1.size.x.value
    cam_8.roi4.size.y.value = cam_8.roi1.size.y.value
    
    shutterBCUOpen()
    print('BCU Shutter Open')
    
    # Camera calibration [um/px]
    hiMagCal = cameraCalGet('HiMag')
    loMagCal = cameraCalGet('LoMag')
    
    # Read centroids 10x and use mean
    centroidXArr = np.zeros(10)
    centroidYArr = np.zeros(10)
    for i in range(0, 10):
        centroidXArr[i] = cam_8.stats4.centroid.x.value
        centroidYArr[i] = cam_8.stats4.centroid.y.value
        # print('Centroid X = {:.6g} px'.format(centroidXArr[i]), ', Centroid Y = {:.6g} px'.format(centroidYArr[i]))
        time.sleep(0.2)
    beamHiMagCentroidX = centroidXArr.mean()
    beamHiMagCentroidY = centroidYArr.mean()
    print('Mean centroid X = {:.6g} px'.format(beamHiMagCentroidX))
    print('Mean centroid Y = {:.6g} px'.format(beamHiMagCentroidY))

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
    
    shutterBCUClose()
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
    if attenSet != 'None':
        if blStr == 'FMX':
            if attenSet in ['All', 'RI']:
                atten_set(attenOrgRI, attenuator='RI')
            if attenSet in ['All', 'BCU']:
                atten_set(attenOrgBCU, attenuator='BCU')
        else:
            atten_set(attenOrgBCU, attenuator='BCU')
    
    
def center_pin():
    """
    Centers a pin in Y
    
    Requirements
    ------------
    * Alignment pin mounted. Pin should be aligned in X to within 0.25 of the Mag3 width
    
    Examples
    --------
    RE(center_pin())
    """
    
    # Copy ROI2 geometry (HiMag Mag3) to ROI4 and use ROI4 centroid plugin
    cam_8.roi4.min_xyz.min_x.value = cam_8.roi2.min_xyz.min_x.value
    cam_8.roi4.min_xyz.min_y.value = cam_8.roi2.min_xyz.min_y.value
    cam_8.roi4.size.x.value = cam_8.roi2.size.x.value * 0.25
    cam_8.roi4.size.y.value = cam_8.roi2.size.y.value
    cam_8.roi4.min_xyz.min_x.value = cam_8.roi2.min_xyz.min_x.value + cam_8.roi2.size.x.value/2 - cam_8.roi4.size.x.value/2
    
    # Invert camera image, so dark pin on light image becomes a peak
    pvStr = 'XF:17IDC-ES:FMX{Cam:8}Proc1:Scale'
    epics.caput(pvStr,'-1')
    
    # High threshold, so AD centroid doesn't interpret background
    cam_8ThresholdOld = cam_8.stats4.centroid_threshold.value
    cam_8.stats4.centroid_threshold.value = 150
    
    # Get centroids at Omega = 0, 90, 180, 270 deg
    yield from bps.mv(gonio.o,0)
    time.sleep(2)
    c0 = centroid_avg(cam_8)[1]
    
    yield from bps.mv(gonio.o,90)
    time.sleep(2)
    c90 = centroid_avg(cam_8)[1]
    
    yield from bps.mv(gonio.o,180)
    time.sleep(2)
    c180 = centroid_avg(cam_8)[1]
    
    yield from bps.mv(gonio.o,270)
    time.sleep(2)
    c270 = centroid_avg(cam_8)[1]
    
    # Calculate offsets
    hiMagCal = cameraCalGet('HiMag')
    
    # Center offset Y
    offsY = ((c180 - c0))/2 * hiMagCal
    print('Y offset = {:.6g} um'.format(offsY))
    
    # Center offset Z
    offsZ = ((c270 - c90))/2 * hiMagCal
    print('Z offset = {:.6g} um'.format(offsZ))
    
    # Move pin to center
    yield from bps.mvr(gonio.py,offsY)
    yield from bps.mvr(gonio.pz,offsZ)
    
    # De-invert image
    pvStr = 'XF:17IDC-ES:FMX{Cam:8}Proc1:Scale'
    epics.caput(pvStr,'1')
    
    # Set thresold to previous value
    cam_8.stats4.centroid_threshold.value = cam_8ThresholdOld
