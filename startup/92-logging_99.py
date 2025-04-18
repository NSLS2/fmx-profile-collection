def slit1_flux_reference_legacy(flux_df,slit1Gap):
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
    
    slits1.x_gap.move(slit1Gap)
    slits1.y_gap.move(slit1Gap, wait=True)
    time.sleep(1.0)
    
    flux_df.at[slit1Gap, 'Slit 1 X gap [um]'] = slit1Gap
    flux_df.at[slit1Gap, 'Slit 1 Y gap [um]'] = slit1Gap
    flux_df.at[slit1Gap, 'Keithley current [A]'] = keithley.get()
    flux_df.at[slit1Gap, 'Keithley flux [ph/s]'] = get_fluxKeithley()
    flux_df.at[slit1Gap, 'BPM1 sum [A]'] = bpm1.sum_all.get()
    # TEMP FIX: flux_df.at[slit1Gap, 'BPM4 sum [A]'] = bpm4.sum_all.get()
    flux_df.at[slit1Gap, 'BPM4 sum [A]'] = 0
    

def fmx_flux_reference_legacy(slit1GapList = [2000, 1000, 600, 400], slit1GapDefault = 1000):
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
    
    print(datetime.datetime.now())
    msgStr = "Energy = " + "%.1f" % get_energy() + " eV"
    print(msgStr)
    log_fmx(msgStr)
    
    flux_df = pd.DataFrame(columns=['Slit 1 X gap [um]',
                                    'Slit 1 Y gap [um]',
                                    'Keithley current [A]',
                                    'Keithley flux [ph/s]',
                                    'BPM1 sum [A]',
                                    'BPM4 sum [A]',
                                   ])
    
    for slit1Gap in slit1GapList:
        slit1_flux_reference_legacy(flux_df,slit1Gap)
    
    # Move back to default slit width
    # TODO: save reference before and return to it later?
    slits1.x_gap.move(slit1GapDefault)
    slits1.y_gap.move(slit1GapDefault, wait=True)
    time.sleep(1.0)

    vFlux = get_fluxKeithley()
    set_fluxBeam(vFlux)
    msgStr = "Reference flux for Slit 1 gap = " + "%d" % slit1GapDefault + " um for T=1 set to " + "%.1e" % vFlux + " ph/s"
    print(msgStr)
    log_fmx(msgStr)
    
    # TEMP FIX: # BPM4 in repair 
    # TEMP FIX: msgStr = 'BPM4 sum = {:.4g} A for Slit 1 gap = {:.1f} um'.format(bpm4.sum_all.get(), slit1GapDefault)
    # TEMP FIX: print(msgStr)
    # TEMP FIX: log_fmx(msgStr)
    
    return flux_df
