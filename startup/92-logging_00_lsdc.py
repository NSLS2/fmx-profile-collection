# Logging and reference routines

import pandas as pd
import datetime
import epics
import time

# Global variable flux_df
"""
    flux_df: pandas DataFrame with fields
        Slit 1 X gap [um]
        Slit 1 Y gap [um]
        Keithley current [A]
        Keithley flux [ph/s]
        BPM1 sum [A]
        BPM4 sum [A]
"""
flux_df = None


def log_fmx(msgStr):
    """
    Appends msgStr to a logfile '/epics/iocs/notebook/notebooks/00_fmx_notebook.log'
    
    Parameters
    ----------
    
    msgStr: Message String
    """
    LOG_FILENAME_FMX = '/epics/iocs/notebook/notebooks/00_fmx_notebook.log'
    logStr = '{},{},'.format(time.strftime('%Y-%m-%d,%H:%M:%S'), time.time()) + msgStr + '\n'
    with open(LOG_FILENAME_FMX, "a") as myfile:
        myfile.write(logStr)


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


def get_fluxKeithley():
    """
    Returns Keithley diode current derived flux.
    """
    
    keithFlux = epics.caget('XF:17IDA-OP:FMX{Mono:DCM-dflux}')
    
    return keithFlux


def set_fluxBeam(flux):
    """
    Sets the flux reference field.
    
    flux: Beamline flux at sample position for transmisison T = 1.  [ph/s]
    """
    
    error = epics.caput('XF:17IDA-OP:FMX{Mono:DCM-dflux-M}', flux)
    
    return error


def slit1_flux_reference(flux_df,slit1Gap):
    """
    Sets Slit 1 X gap and Slit 1 Y gap to a specified position,
    and returns flux reference values to a provided pandas DataFrame.
    
    Supporting function for fmx_flux_reference()
    
    Parameters
    ----------
    
    slit1Gap: float
        Gap value for Slit 1 X and Y [um]
    
    flux_df: pandas DataFrame with fields:
        Slit 1 X gap [um]
        Slit 1 Y gap [um]
        Keithley current [A]
        Keithley flux [ph/s]
        BPM1 sum [A]
        BPM4 sum [A]
        
    """
    yield from bps.mv(slits1.x_gap, slit1Gap, slits1.y_gap, slit1Gap, wait=True)
    time.sleep(2.0) # wait so the slits are definitely done moving and the Keithley reading is stable
    
    flux_df.at[slit1Gap, 'Slit 1 X gap [um]'] = slit1Gap
    flux_df.at[slit1Gap, 'Slit 1 Y gap [um]'] = slit1Gap
    flux_df.at[slit1Gap, 'Keithley current [A]'] = keithley.get()
    flux_df.at[slit1Gap, 'Keithley flux [ph/s]'] = get_fluxKeithley()
    flux_df.at[slit1Gap, 'BPM1 sum [A]'] = bpm1.sum_all.get()
    # TEMP FIX: flux_df.at[slit1Gap, 'BPM4 sum [A]'] = bpm4.sum_all.get()
    flux_df.at[slit1Gap, 'BPM4 sum [A]'] = 0
    

def fmx_flux_reference(slit1GapList = [2000, 1000, 600, 400], slit1GapDefault = 1000, transSet='All'):
    """
    Sets Slit 1 X gap and Slit 1 Y gap to a list of settings,
    and returns flux reference values in a pandas DataFrame.
    
    Parameters
    ----------
    
    slit1GapList: float (default=[2000, 1000, 600, 400])
        A list of gap values [um] for Slit 1 X and Y
    slit1GapDefault: Gap value [um] to set as default after getting references
        Default slit1GapDefault = 1000
    
    Returns
    -------
    
    flux_df: pandas DataFrame with fields
        Slit 1 X gap [um]
        Slit 1 Y gap [um]
        Keithley current [A]
        Keithley flux [ph/s]
        BPM1 sum [A]
        BPM4 sum [A]
        
    Examples
    --------
    fmx_flux_reference()
    flux_df=fmx_flux_reference()
    flux_df
    fmx_flux_reference(slit1GapList = [2000, 1500, 1000])
    fmx_flux_reference(slit1GapList = [2000, 1500, 1000], slit1GapDefault = 600)
        
    """
    
    # Store current transmission, then set full transmission
    if transSet != 'None':
        if transSet in ['All', 'BCU']:
            transOrgBCU = trans_get(trans=trans_bcu)
        if transSet in ['All', 'RI']:
            transOrgRI = trans_get(trans=trans_ri)
            yield from trans_set(1.0, trans=trans_ri)
        if transSet == 'BCU':
            yield from trans_set(1.0, trans=trans_bcu)
        if transSet == 'All':
            yield from trans_set(1.0, trans=trans_bcu)
            
    print(datetime.datetime.now())
    msgStr = "Energy = " + "%.1f" % get_energy() + " eV"
    print(msgStr)
    log_fmx(msgStr)
    
    global flux_df
    flux_df = pd.DataFrame(columns=['Slit 1 X gap [um]',
                                    'Slit 1 Y gap [um]',
                                    'Keithley current [A]',
                                    'Keithley flux [ph/s]',
                                    'BPM1 sum [A]',
                                    'BPM4 sum [A]',
                                   ])
    
    # Put in diode
    yield from bps.mv(light.y,govPositionGet('li', 'Diode'))
    
    # Retract gonio X by 200 um
    yield from bps.mvr(gonio.gx, -200)
    
    # Open BCU shutter
    yield from bps.mv(shutter_bcu.open, 1)
    time.sleep(1)
    
    for slit1Gap in slit1GapList:
        yield from slit1_flux_reference(flux_df,slit1Gap)
    
    # Move back to default slit width
    # TODO: save reference before and return to it later?
    yield from bps.mv(slits1.x_gap, slit1GapDefault, slits1.y_gap, slit1GapDefault, wait=True)
    time.sleep(2.0) # wait so the slits are definitely done moving and the Keithley reading is stable

    vFlux = get_fluxKeithley()
    set_fluxBeam(vFlux)
    msgStr = "Reference flux for Slit 1 gap = " + "%d" % slit1GapDefault + " um for T=1 set to " + "%.1e" % vFlux + " ph/s"
    print(msgStr)
    log_fmx(msgStr)
    
    # TEMP FIX: # BPM4 in repair 
    #msgStr = 'BPM4 sum = {:.4g} A for Slit 1 gap = {:.1f} um'.format(bpm4.sum_all.get(), slit1GapDefault)
    #print(msgStr)
    #log_fmx(msgStr)
    
    # Close shutter
    yield from bps.mv(shutter_bcu.close, 1)
    
    # Put back gonio X
    yield from bps.mvr(gonio.gx, 200)
    
    # Retract diode
    yield from bps.mv(light.y,govPositionGet('li', 'In'))
    
    # Set previous beam transmission
    if transSet != 'None':
        if transSet in ['All', 'RI']:
            yield from trans_set(transOrgRI, trans=trans_ri)
        if transSet in ['All', 'BCU']:
            yield from trans_set(transOrgBCU, trans=trans_bcu)
            


def fmx_beamline_reference():
    """
    Prints reference values and appends to the FMX log file
    
   
    Examples
    --------
    fmx_beamline_reference()
        
    """
    
    print(datetime.datetime.now())
    msgStr = "Energy = " + "%.2f" % get_energy() + " eV"
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "Beam current = " + "%.2f" % beam_current.get() + " mA"
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "IVU gap = " + "%.1f" % ivu_gap.gap.user_readback.get() + " um"
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "XBPM2 posX = " + "%.2f" % xbpm2.x.get() + " um"
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "XBPM2 posY = " + "%.2f" % xbpm2.y.get() + " um"
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "XBPM2 total current = " + "%.2f" % xbpm2.total.get() + " uA"
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "HDCM pitch = " + "%.4f" % hdcm.p.user_readback.get() + " mrad"
    print(msgStr)
    log_fmx(msgStr)

    msgStr = "HDCM roll = " + "%.4f" % hdcm.r.user_readback.get() + " mrad"
    print(msgStr)
    log_fmx(msgStr)

    msgStr = "BPM1 posX = " + "%.2f" % bpm1.x.get()
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "BPM1 posY = " + "%.2f" % bpm1.y.get()
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "BPM1 total current = " + "%.3g" % bpm1.sum_all.get() + " A"
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "HFM pitch = " + "%.4f" % hfm.pitch.user_readback.get() + " mrad"
    print(msgStr)
    log_fmx(msgStr)

    msgStr = "VKB tweak voltage = " + "%.3f" % vkb_piezo_tweak.get() + " V"
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "VKB pitch = " + "%.4f" % kbm.vp.user_readback.get() + " urad"
    print(msgStr)
    log_fmx(msgStr)

    msgStr = "HKB tweak voltage = " + "%.3f" % hkb_piezo_tweak.get() + " V"
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "HKB pitch = " + "%.4f" % kbm.hp.user_readback.get() + " urad"
    print(msgStr)
    log_fmx(msgStr)

    msgStr = "Gonio X = " + "%.1f" % gonio.gx.user_readback.get() + " um"
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "Gonio Y = " + "%.1f" % gonio.gy.user_readback.get() + " um"
    print(msgStr)
    log_fmx(msgStr)
    
    msgStr = "Gonio Z = " + "%.1f" % gonio.gz.user_readback.get() + " um"
    print(msgStr)
    log_fmx(msgStr)
    
    return


def fmx_reference(slit1GapDefault = 1000, transSet='All'):
    """
    Calls fmx_flux_reference, then fmx_beamline_reference.
    setE will do the same after the beam alignment.
   
    Parameters
    ----------
    transSet: FMX only: Set to 'RI' if there is a problem with the BCU attenuator.
              FMX only: Set to 'BCU' if there is a problem with the RI attenuator.
              Set to 'None' if there are problems with all attenuators.
              Operator then has to choose a flux by hand that will not saturate scinti
              default = 'All'
              
    Examples
    --------
    fmx_reference()
        
    """
    if not govStatusGet('SA'):
        print('Not in Governor state SA, exiting')
        return
    
    # Transition to Governor state BL
    govStateSet('BL')
    
    RE(fmx_flux_reference(slit1GapDefault = slit1GapDefault, transSet = transSet))
    
    # Transition to Governor state SA
    govStateSet('SA')
    
    fmx_beamline_reference()
    
    global flux_df
    
    return flux_df
    
    
   