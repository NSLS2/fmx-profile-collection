 # Plans to align beam and goniometer for LSDC

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
        centroidXArr[i] = stats.centroid.x.get()
        centroidYArr[i] = stats.centroid.y.get()
        # print('Centroid X = {:.6g} px'.format(centroidXArr[i]), ', Centroid Y = {:.6g} px'.format(centroidYArr[i]))
        time.sleep(0.2)
    CentroidX = centroidXArr.mean()
    CentroidY = centroidYArr.mean()
    print('Mean centroid X = {:.6g} px'.format(CentroidX))
    print('Mean centroid Y = {:.6g} px'.format(CentroidY))

    return CentroidX, CentroidY


def detectorCoverClose():
    """
    Closes the Detector Cover
    """
    yield from bps.mv(cover_detector.close, 1)
    
    while cover_detector.status.get() == 1:
        #print(cover_detector.status.get())
        time.sleep(0.5)
    
    return

def detectorCoverOpen():
    """
    Opens the Detector Cover
    """
    yield from bps.mv(cover_detector.open, 1)
    
    while cover_detector.status.get() != 1:
        #print(cover_detector.status.get())
        time.sleep(0.5)
    
    return


def trans_set(transmission, trans = trans_bcu):
    """
    Sets the Attenuator transmission
    """
    
    e_dcm = get_energy()
    if e_dcm < 5000 or e_dcm > 30000:
        print('Monochromator energy out of range. Must be within 5000 - 30000 eV. Exiting.')
        return
    
    yield from bps.mv(trans.energy, e_dcm) # This energy PV is only used for debugging
    yield from bps.mv(trans.transmission, transmission)
    yield from bps.mv(trans.set_trans, 1)
    
    if trans == trans_bcu:
        while atten_bcu.done.get() != 1:
            time.sleep(0.5)
    
    print('Attenuator = ' + trans.name + ', Transmission set to %.3f' % trans.transmission.get())
    return


def trans_get(trans = trans_bcu):
    """
    Returns the Attenuator transmission
    """
    
    transmission = trans.transmission.get()
    
    print('Attenuator = ' + trans.name + ', Transmission = %.3f' % transmission)
    return transmission


def transDefaultGet(energy):
    """
    Returns the default transmission to avoid saturation of the scintillator
    
    energy: X-ray energy [eV]
    
    The look up table is set in settings/set_energy setup FMX.ipynb
    """
    
    # This reads from:
    # XF:17ID-ES:FMX{Misc-LUT:atten}X-Wfm
    # XF:17ID-ES:FMX{Misc-LUT:atten}Y-Wfm
    # 
    # atten is a dummy motor just for this purpose.
    # To be replaced by trans_bcu and corresponding new PVs
    
    transLUT = read_lut('atten')
    transDefault = np.interp(energy,transLUT['Energy'],transLUT['Position'])
    
    return transDefault
    
    
# Beam align functions

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
    # TODO:
    #  * Check for Vis screen actuators out
    #  * Check for C-hutch shutter open
    #  * Check for ROI2 exceeding camera border.
    #    Check how this affects the ROI centering move, and whether we can correct for that
    
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
        print('Not in Governor state SA, exiting.')
        return -1
    
    # Check for beam after DCM: BPM1 total current
    if bpm1.sum_all.get() < 1e-7:
        print('Intensity after DCM low. BPM1 total current <1e-7 A.',
              'Check FOE shutter, and rocking curve, then repeat.',
              'Exiting.')
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
    
    # TODO: use "yield from bps.mv(...)" instead of .put(...) below.

    # ROI1 centroid plugin does not work
    # Copy ROI1 geometry to ROI4 and use ROI4 centroid plugin
    cam_8.roi4.min_xyz.min_x.put(cam_8.roi1.min_xyz.min_x.get())
    cam_8.roi4.min_xyz.min_y.put(cam_8.roi1.min_xyz.min_y.get())
    cam_8.roi4.size.x.put(cam_8.roi1.size.x.get())
    cam_8.roi4.size.y.put(cam_8.roi1.size.y.get())
    
    yield from bps.mv(shutter_bcu.open, 1)
    print('BCU Shutter Open')
    time.sleep(1)
    
    # Check for focused beam on scinti. Do nothing if stats 4 max intensity < 20 counts
    # TODO: Verify 20 counts threshold for more settings
    if cam_8.stats4.max_value.get() < 20:
        print('Max intensity < 20 counts.',
              'Check beam intensity and focus on scinti, then repeat.',
              'No changes made.')
    else:
        # Camera calibration [um/px]
        hiMagCal = BL_calibration.HiMagCal.get()
        loMagCal = BL_calibration.LoMagCal.get()
        
        # Read centroids
        beamHiMagCentroid = centroid_avg(cam_8.stats4)
        beamHiMagCentroidX = beamHiMagCentroid[0]
        beamHiMagCentroidY = beamHiMagCentroid[1]
        time.sleep(1)
        
        # Get beam shift on Hi Mag
        # Assume the LSDC centering crosshair is in the center of the FOV
        # This works as long as cam_8 ROI1 does not hit the edge of the cam_8 image
        beamHiMagDiffX = beamHiMagCentroidX - (cam_8.roi4.size.x.get()/2)
        beamHiMagDiffY = beamHiMagCentroidY - (cam_8.roi4.size.y.get()/2)
        
        # Do nothing if we see a too large shift
        if beamHiMagDiffX>100 or beamHiMagDiffY>100:
            print('Beam centroid change > 100 px detected.',
                  'No changes made. Manual beam center correction needed.')
            beamHiMagDiffX=0
            beamHiMagDiffY=0
        
        # Correct Mag 4 (cam_8 ROI1)
        # Adjust cam_8 ROI1 min_y, LSDC uses this for the Mag4 FOV.
        # This works as long as cam_8 ROI1 does not hit the edge of the cam_8 image
        cam_8.roi1.min_xyz.min_x.put(cam_8.roi1.min_xyz.min_x.get() + beamHiMagDiffX)
        cam_8.roi1.min_xyz.min_y.put(cam_8.roi1.min_xyz.min_y.get() + beamHiMagDiffY)
        
        # Correct Mag 3 (cam_8 ROI2)
        cam_8.roi2.min_xyz.min_x.put(cam_8.roi2.min_xyz.min_x.get() + beamHiMagDiffX)
        cam_8.roi2.min_xyz.min_y.put(cam_8.roi2.min_xyz.min_y.get() + beamHiMagDiffY)
        
        # Get beam shift on Lo Mag from Hi Mag shift and calibration factor ratio
        beamLoMagDiffX = beamHiMagDiffX * hiMagCal/loMagCal
        beamLoMagDiffY = beamHiMagDiffY * hiMagCal/loMagCal
        
        # Correct Mag 1 (cam_7 ROI2)
        cam_7.roi2.min_xyz.min_x.put(cam_7.roi2.min_xyz.min_x.get() + beamLoMagDiffX)
        cam_7.roi2.min_xyz.min_y.put(cam_7.roi2.min_xyz.min_y.get() + beamLoMagDiffY)
        
        # Correct Mag 2 (cam_7 ROI3)
        cam_7.roi3.min_xyz.min_x.put(cam_7.roi3.min_xyz.min_x.get() + beamLoMagDiffX)
        cam_7.roi3.min_xyz.min_y.put(cam_7.roi3.min_xyz.min_y.get() + beamLoMagDiffY)
        
        time.sleep(3)
        
        # Adjust Gonio Y so rotation axis is again aligned to beam
        gonioYDiff = beamHiMagDiffY * hiMagCal
        posGyOld = govPositionGet('gy', 'Work')
        posGyNew = posGyOld + gonioYDiff
        yield from bps.mv(gonio.gy, posGyNew)   # Move Gonio Y to new position
        govPositionSet(posGyNew, 'gy', 'Work')  # Set Governor Gonio Y Work position to new value
        print('Gonio Y difference = %.3f' % gonioYDiff)
            
    yield from bps.mv(shutter_bcu.close, 1)
    print('BCU Shutter Closed')
    
    # Transition to Governor state SA (Sample Alignment)
    govStateSet('SA')
    
    # Set previous beam transmission
    if transSet != 'None':
        if blStr == 'FMX':
            if transSet in ['All', 'RI']:
                yield from trans_set(transOrgRI, trans=trans_ri)
            if transSet in ['All', 'BCU']:
                yield from trans_set(transOrgBCU, trans=trans_bcu)
        else:
            yield from trans_set(transOrgBCU, trans=trans_bcu)
