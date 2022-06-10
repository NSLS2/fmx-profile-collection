import numpy as np
import matplotlib.pyplot as plt
import time
import os
import bluesky.plan_stubs as bps


def xrf_spectrum_read(dataDir = '/tmp', filename=0):
    """
    Read the current XIA Mercury spectrum from the MCA ophyd object
    
    Example:
    xrf_spectrum_read(dataDir='/nsls2/data/fmx/legacy/pass-310080', filename='20220609_01.csv')
    """
    
    xrfSpectrum = mercury.mca.spectrum.get()
    
    if filename: np.savetxt(os.path.join(dataDir, filename), xrfSpectrum, delimiter=",")
    
    return xrfSpectrum


def xrf_spectrum_plot(xrfSpectrum, ax=0, figsizeX=9.5, figsizeY=5, label='XRF spectrum', showLegend=True):
    """
    Plot a XIA Mercury XRF spectrum
    
    Examples:
    xrf_spectrum_plot(xrfSpectrum, label='Spectrum 01')
    """
    
    if not ax: fig, ax = plt.subplots(figsize=(figsizeX,figsizeY))
    
    ax.plot(xrfSpectrum, label=label)
        
    ax.set_xlabel('Index')    
    ax.set_ylabel('Counts')    
    if showLegend: ax.legend(loc=1)


def xrf_file_plot(specFile, dataDir = '/tmp', ax=0, figsizeX=9.5, figsizeY=5, showLegend=True):
    """
    Plot a XIA Mercury XRF spectrum from a file
    
    Examples:
    xrf_file_plot('test.csv')
    xrf_file_plot('20220317_01.csv', dataDir = '/GPFS/CENTRAL/xf17id2/FMX-999999_17Mar2022')
    xrf_file_plot('20220317_01.csv', dataDir=dataDir, ax=ax, figsizeX=6)
    """
    
    if not ax: fig, ax = plt.subplots(figsize=(figsizeX,figsizeY))
    
    datafileName = dataDir + '/' + specFile
    xrfSpectrum = np.loadtxt(datafileName, delimiter=',', skiprows=0)
    
    xrf_spectrum_plot(xrfSpectrum, ax=ax, figsizeX=figsizeX, figsizeY=figsizeY, label=specFile, showLegend=showLegend)
    
    
def xrf_spectrum_acquire():
    """
    Acquire an X-ray Fluorescence spectrum from the XIA Mercury MCA
    
    Open shutter, Erase and Start Mercury, close shutter
    
    Examples:
    RE(xrf_spectrum_acquire())
    """
    
    yield from bps.mv(shutter_bcu.open, 0)
    
    # Mecury Erase and Start
    mercury.erase_start.put(1)
    
    # Mecury Real Time preset
    t_real = mercury.mca.preset_real_time.get()
    print(f'Mecury Real Time preset = {t_real:.2f} s')
    time.sleep(t_real)
    
    yield from bps.mv(shutter_bcu.close, 1)
    
    return


def xrf_spectrum_collect(dataDir = '/tmp', filename=0, label='XRF spectrum'):
    """
    Collect an X-ray Fluorescence spectrum from the XIA Mercury MCA
    
    Transition from Governor SA to XF state, acquire, return to SA, save to csv and plot
    
    Examples:
    RE(xrf_spectrum_collect(dataDir='/nsls2/data/fmx/legacy/pass-310080', filename='20220609_01.csv'))
    
    TODO
    * Spectrum to databroker
    * Newest Bluesky RE to return the spectrum directly
      * from bluesky.run_engine import RunEngine
        RE_returns = RunEngine({}, call_returns_result=True)
    """
  
    if not govStatusGet('SA'):
        print('Not in Governor state SA, exiting')
        return
    
    # Transition to Governor state XF (X-ray Fluorescence)
    govStateSet('XF')
    
    yield from xrf_spectrum_acquire()
    
    # Transition to Governor state SA
    govStateSet('SA')
    
    xrfSpectrum = xrf_spectrum_read(dataDir = dataDir, filename=filename)
    
    xrf_spectrum_plot(xrfSpectrum, label=label)