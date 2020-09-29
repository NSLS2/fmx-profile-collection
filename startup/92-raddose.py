# Raddose3D interface

import epics
import numpy as np
import subprocess
from numpy.lib import recfunctions as rfn  # needs to be imported separately
from shutil import copyfile
import fileinput
import sys
import os.path


def replaceLine(file,searchExp,replaceExp):
    for line in fileinput.input(file, inplace=1):
        if searchExp in line:
            line = replaceExp
        sys.stdout.write(line)

def run_rd3d(inputFileName):
    prc = subprocess.Popen(["java", "-jar", "rd3d/raddose3d.jar", "-i", inputFileName, "-p", "rd3d/rd3d_"],
        stdout=subprocess.PIPE,
        universal_newlines=True)
    out = prc.communicate()[0]
    return out

def rd3d_calc(flux=3.5e12, energy=12.66,
              beamType='GAUSSIAN', fwhmX=1, fwhmY=2, collimationX=10, collimationY=10,
              wedge=0, exposureTime=1,
              translatePerDegX=0, translatePerDegY=0, translatePerDegZ=0,
              startOffsetX=0, startOffsetY=0, startOffsetZ=0,
              dimX=20, dimY=20, dimZ=20,
              pixelsPerMicron=2, angularResolution=2,
              templateFileName = 'rd3d_input_template.txt',
              verbose=True,
             ):
    """
    RADDOSE3D dose estimate
    
    This version calculates dose values for an average protein crystal.
    The estimates need to be adjusted proportionally for a crystal if it is more/less sensitive.
    
    All paramaters listed below can be set. If they are not set explicitly, RADDOSE3D will use
    the listed default value.
    
    A complete manual with explanations is available at
    https://github.com/GarmanGroup/RADDOSE-3D/blob/master/doc/user-guide.pdf
    
    Photon flux [ph/s]: flux=3.5e12
    Photon energy [keV]: energy=12.66,
    Beamtype (GAUSSIAN | TOPHAT): beamType='GAUSSIAN'
    Vertical beamsize FHWM [um]: fwhmX=1
    Horizontal beamsize FHWM [um]: fwhmY=2
    Vertical collimation (for TOPHAT beams this is the size) [um]: collimationX=10
    Horizontal collimation (for TOPHAT beams this is the size) [um]: collimationY=10
    Omega range [deg]: wedge=0
    Exposure time for the complete wedge [s]: exposureTime=1
    Translation per degree V [um]: translatePerDegX=0
    Translation per degree H [um]: translatePerDegY=0
    Translation along beam per degree [um]: translatePerDegZ=0
    Crystal position offset V [um]: startOffsetX=0
    Crystal position offset H [um]: startOffsetY=0
    Crystal position offset along beam [um]: startOffsetZ=0
    Crystal dimension V [um]: dimX=20
    Crystal dimension H [um]: dimY=20
    Crystal dimension along beam [um]: dimZ=20
    Pixels per micron: pixelsPerMicron=2
    Angular resolution: angularResolution=2
    Template file (in 'rd3d' subdir of active notebook): templateFileName = 'rd3d_input_template.txt'
    
    Return value is a structured numpy array. You can use it for follow-up calculations
    of the results returned by RADDOSE3D in "output-Summary.csv". Call the return variable
    to find the field names.
    
    Examples:
    rd3d_out = rd3d_calc(flux=1.35e12, exposuretime=0.01, dimx=1, dimy=1, dimz=1)
    rd3d_calc(flux=1e12, energy=12.7, fwhmX=3, fwhmY=5, collimationX=9, collimationY=15, wedge=180,
           exposureTime=8, translatePerDegX=0, translatePerDegY=0.27, startOffsetY=-25,
           dimX=3, dimY=80, dimZ=3, pixelsPerMicron=0.5, angularResolution=2, verbose=False)
           
    Setup:
    * rd3d_input_template.txt and raddose.jar in subdir rd3d/
    * PDB file 2vb1.pdb in notebook dir
    2vb1.pdb
    rd3d/raddose.jar
    rd3d/rd3d_input_template.txt
    
    Todo:
    * Cannot call PDB file in subdir or active dir, i.e. only 'PDB 2vb1.pdb' works in rd3d_input_template.txt
    * run_rd3d() with subdir option
      * Is the subdir really worth it? Use 'raddose' prefix instead? (Tentative: yes)
      * If subdir: Clean code (run_rd3d()), subdir name as option, description in help text
        (how if it's an option?)
    * Keep template file as option? Then it should be in same dir as PDB file (notebook dir)
    * Protein option PDB (on xf17id1 cannot reach PDB URL) or JJDUMMY (how to cite?)
    """
    
    rd3d_dir = "rd3d"
    inputFileName = "rd3d_input.txt"
    outputFileName = "rd3d_Summary.csv"

    templateFilePath=os.path.join(rd3d_dir,templateFileName)
    inputFilePath=os.path.join(rd3d_dir,inputFileName)
    outputFilePath=os.path.join(rd3d_dir,outputFileName)
    
    copyfile(templateFilePath, inputFilePath)
        
    replaceLine(inputFilePath,"FLUX",'FLUX {:.2e}\n'.format(flux))
    replaceLine(inputFilePath,"ENERGY",'ENERGY {:.2f}\n'.format(energy))
    replaceLine(inputFilePath,"TYPE GAUSSIAN",'TYPE {:s}\n'.format(beamType))
    replaceLine(inputFilePath,"FWHM",'FWHM {:.1f} {:.1f}\n'.format(fwhmX,fwhmY))
    replaceLine(inputFilePath,"COLLIMATION",'COLLIMATION RECTANGULAR {:.1f} {:.1f}\n'.format(collimationX,collimationY))
    replaceLine(inputFilePath,"WEDGE",'WEDGE 0 {:0.1f}\n'.format(wedge))
    replaceLine(inputFilePath,"EXPOSURETIME",'EXPOSURETIME {:0.3f}\n'.format(exposureTime))
    replaceLine(inputFilePath,"TRANSLATEPERDEGREE",
                'TRANSLATEPERDEGREE {:0.4f} {:0.4f} {:0.4f}\n'.format(translatePerDegX,translatePerDegY,translatePerDegZ))
    replaceLine(inputFilePath,"DIMENSION",'DIMENSION {:0.1f} {:0.1f} {:0.1f}\n'.format(dimX,dimY,dimZ))
    replaceLine(inputFilePath,"PIXELSPERMICRON",'PIXELSPERMICRON {:0.1f}\n'.format(pixelsPerMicron))
    replaceLine(inputFilePath,"ANGULARRESOLUTION",'ANGULARRESOLUTION {:0.1f}\n'.format(angularResolution))
    replaceLine(inputFilePath,"STARTOFFSET",
                'STARTOFFSET {:f} {:f} {:f}\n'.format(startOffsetX,startOffsetY,startOffsetZ))    
    
    out = run_rd3d(inputFilePath)
    if verbose:
        print(out)
    
    rd3d_out = np.genfromtxt(outputFilePath, delimiter=',', names=True)
    print("\n=== rd3d_calc summary ===")
    # append_fields has issues with 1d arrays, use reshape() and [] to make len() work on size 1 array:
    # https://stackoverflow.com/questions/53137822/adding-a-field-to-a-structured-numpy-array-4
    rd3d_out = rd3d_out.reshape(1)
    print("Diffraction weighted dose = " + "%.3f" % rd3d_out['DWD'] + " MGy")
    print("Max dose = " + "%.3f" % rd3d_out['Max_Dose'] + " MGy")  
    t2gl = exposureTime * 30 / rd3d_out['DWD']  # Time to Garman limit based on diffraction weighted dose
    rd3d_out = rfn.append_fields(rd3d_out,'t2gl',[t2gl],usemask=False)
    print("Time to Garman limit = " + "%.3f" % rd3d_out['t2gl'] + " s")
    
    return rd3d_out


def fmx_dose(flux = -1, energy = 12.66,
             beamsizeV = 1.0, beamsizeH = 2.0,
             oscRange = 180, oscWidth = 0.1, exposureTimeFrame=0.02,
             vectorL = 50,
             verbose = False
            ):
    
    """
    Calculate the average diffraction weighted dose for a vector or standard (vectorL = 0) data
    collection, given the parameters a users enters in LSDC: Energy, flux, beamsize, total
    oscillation range, oscillation width, exposure time per frame and the vector length.
    
    Assumptions made: Crystal is similar to lysozyme, and not much larger than the beam.
    
    Parameters
    ----------
    
    flux: float
    Flux at sample position [ph/s]. By default this value is copied from the beamline's
    flux-at-sample PV. Can also be set explicitly.
    
    energy: float
    Photon energy [keV]. Default 12.66 keV
    
    beamsizeV, beamsizeH: float
    Beam size (V, H) [um]. Default 1x2 (VxH). For now, set explicitly.
    
    vectorL: float
    Vector length [um]: Make assumption that the vector is completely oriented along X-axis.
    Default 0 um.
    
    oscRange: float
    Crystal rotation for complete experiment [deg]. Start at 0, end at oscRange
    
    oscWidth: float
    Crystal rotation for one frame [deg].
    
    exposureTimeFrame: float
    Exposure time per frame [s]

    verbose: boolean
    True: Print out RADDOSE3D output. Default False
    
    
    Internal parameters
    -------------------
    
    Crystal size XYZ: Match to beam size perpendicular to (XZ), and to vector length along the
    rotation axis (Y)
    
    
    Returns
    -------
    
    dose: float
    Average Diffraction Weighted Dose [MGy]
    
    Examples
    --------
    
    fmx_dose()
    fmx_dose(beamsizeV = 1.6, beamsizeH = 2,
             oscRange = 180, oscWidth = 0.2, exposureTimeFrame=0.1,
             vectorL = 100)
    fmx_dose(energy = 12.66, beamsizeV = 10, beamsizeH = 10, vectorL = 100, verbose = True)
    
    Todo
    ----
    
    * Beamsize: Read from a beamsize PV, or get from a get_beamsize() function
      - Check CRL settings
      - Check BCU attenuator
      - If V1H1 then 10x10 (dep on E)
        - If V0H0 then 
          - If BCU-Attn-T < 1.0 then 3x5
          - If BCU-Attn-T = 1.0 then 1x2
    * Vector length: Use the real projections
    """
    
    # Beam size, assuming rd3d_calc() uses Gaussian default
    fwhmX = beamsizeV
    fwhmY = beamsizeH
    collimationX = 3*beamsizeV
    collimationY = 3*beamsizeH
    
    # Adjust pixelsPerMicron for RD3D to beamsize
    if fwhmX < 1.5 or fwhmY < 1.5:
        pixelsPerMicron = 2
    elif fwhmX < 3.0 or fwhmY < 3.0:
        pixelsPerMicron = 1
    else: 
        pixelsPerMicron = 0.5
    
    # Set explicitly or use current flux
    if flux == -1:
        # Current flux [ph/s]: From flux-at-sample PV
        fluxSample = epics.caget('XF:17IDA-OP:FMX{Mono:DCM-dflux-MA}')
        print('Flux at sample = {:.4g} ph/s'.format(fluxSample))
    else:
        fluxSample = flux            
    
    # RADDSE3D uses translation per deg; LSDC gives vector length
    translatePerDegY = vectorL / oscRange
    
    # Crystal offset along rotation axis
    startOffsetY = -vectorL / 2
    exposureTimeTotal = exposureTimeFrame * oscRange / oscWidth
    
    # Crystal size [um]: Match to beam size in V, longer than vector in H
    dimX = beamsizeV  # Crystal dimension V [um]
    dimY = vectorL + beamsizeH  # Crystal dimension H [um]
    dimZ = dimX  # Crystal dimension along beam [um]
    
    rd3d_out = rd3d_calc(flux=fluxSample, energy=energy,
                         fwhmX=fwhmX, fwhmY=fwhmY,
                         collimationX=collimationX, collimationY=collimationY,
                         wedge=oscRange,
                         exposureTime=exposureTimeTotal,
                         translatePerDegX=0, translatePerDegY=translatePerDegY,
                         startOffsetY=startOffsetY,
                         dimX=dimX, dimY=dimY, dimZ=dimZ,
                         #pixelsPerMicron=0.5, angularResolution=2,
                         pixelsPerMicron=pixelsPerMicron, angularResolution=2,
                         verbose = verbose
                        )
    
    print("\n=== fmx_dose summary ===")
    print('Total exposure time = {:1.3f} s'.format(exposureTimeTotal))
    dose = rd3d_out['DWD'].item()  # .item() to convert 1d array to scalar
    print('Average Diffraction Weighted Dose = {:f} MGy'.format(dose))
    
    return dose


def fmx_expTime_to_10MGy(beamsizeV = 1.0, beamsizeH = 2.0,
                         vectorL = 0,
                         energy = 12.66,
                         flux = -1,
                         oscRange = 180,
                         verbose = False
                        ):
    """
    Calculate the total exposure time to reach an average diffraction weighted dose of 10 MGy,
    given the beamsize, vector length, energy, flux, and total oscillation range.
    
    Use this function to compare this time with the total exposure time for the current settings
    as reported by LSDC. If these times are matched, users put 10 MGy on their sample, assuming the
    assumptions made - crystal is similar to lysozyme, and not much larger than the beam - are sensible.
    
    
    Parameters
    ----------
    
    beamsizeV, beamsizeH: float
    Beam size (V, H) [um]. Default 1x2 (VxH). For now, set explicitly.
    
    vectorL: float
    Vector length [um]: Default 0 um. Make assumption that the vector is completely oriented
    along X-axis.
    
    energy: float
    Photon energy [keV]. Default 12.66 keV
    
    oscRange: float
    Crystal rotation for complete experiment [deg]. Start at 0, end at oscRange
    
    flux: float
    Flux at sample position [ph/s]. By default this value is copied from the beamline's
    flux-at-sample PV. Can also be set explicitly.
    
    verbose: boolean
    True: Print out RADDOSE3D output. Default False
    
    
    Internal parameters
    -------------------
    
    Crystal size XYZ: Match to beam size perpendicular to (XZ), and to vector length along the
    rotation axis (Y)
    
    
    Returns
    -------
    
    Experiment time [s] to Average Diffraction Weighted Dose = 10 MGy
    
    Example
    -------
    
    fmx_expTime_to_10MGy(beamsizeV = 3.0, beamsizeH = 5.0, vectorL = 100, energy = 12.7,
                         oscRange = 180, flux = 1e12, verbose = True)
    fmx_expTime_to_10MGy(beamsizeV = 1.0, beamsizeH = 2.0, vectorL = 50, oscRange = 180, flux = 1e12)
    
    
    Todo
    ----
    
    * Beamsize: Read from a beamsize PV, or get from a get_beamsize() function
      - Check CRL settings
      - Check BCU attenuator
      - If V1H1 then 10x10 (dep on E)
        - If V0H0 then 
          - If BCU-Attn-T < 1.0 then 3x5
          - If BCU-Attn-T = 1.0 then 1x2
    * Vector length: Use the real projections
    """
    
    # Beam size [um]
    fwhmX = beamsizeV
    fwhmY = beamsizeH
    collimationX = 3*beamsizeV
    collimationY = 3*beamsizeH
    
    # Adjust pixelsPerMicron for RD3D to beamsize
    if fwhmX < 1.5 or fwhmY < 1.5:
        pixelsPerMicron = 5
    elif fwhmX < 3.0 or fwhmY < 3.0:
        pixelsPerMicron = 2.5
    else: 
        pixelsPerMicron = 0.5
    
    # Set explicitly or use current flux
    if flux == -1:
        # Current flux [ph/s]: From flux-at-sample PV
        fluxSample = epics.caget('XF:17IDA-OP:FMX{Mono:DCM-dflux-MA}')
        print('Flux at sample = {:.4g} ph/s'.format(fluxSample))
    else:
        fluxSample = flux            
    
    # Crystal size [um]: Match to beam size in V, longer than vector in H
    # XYZ as defined by Raddose3D
    dimX = beamsizeV  # Crystal dimension V [um]
    dimY = vectorL + beamsizeH  # Crystal dimension H [um]
    dimZ = dimX  # Crystal dimension along beam [um]
    
    # Start offset for horizontal vector to stay within crystal [um]
    startOffsetY = -vectorL / 2
    
    # Exposure time [s]
    exposureTime = 1.0
    
    # Avoid division by zero when calculating translatePerDegY
    if oscRange == 0: oscRange = 1e-3
    
    # Vector length [um]: Assume LSDC vector length is along X-axis (Raddose3D Y).
    # Translation per degree has to match total vector length
    translatePerDegY = vectorL / oscRange
    
    rd3d_out = rd3d_calc(flux=fluxSample, energy=energy,
                         fwhmX=fwhmX, fwhmY=fwhmY,
                         collimationX=collimationX, collimationY=collimationY,
                         wedge=oscRange,
                         exposureTime=exposureTime,
                         translatePerDegY=translatePerDegY,
                         startOffsetY=startOffsetY,
                         pixelsPerMicron=pixelsPerMicron, angularResolution=1,
                         dimX=dimX, dimY=dimY, dimZ=dimZ,
                         verbose=verbose
                        )
    
    print("\n=== fmx_expTime_to_10MGy summary ===")
    dose1s = rd3d_out['DWD'].item()  # .item() to convert 1d array to scalar
    print('Average Diffraction Weighted Dose for 1s exposure = {:f} MGy'.format(dose1s))
    expTime10MGy = 10 / dose1s  # Experiment time to reach an average DWD of 10 MGy
    print('Experiment time to reach an average diffraction weighted dose of 10 MGy = {:f} s'.format(expTime10MGy))
    
    return expTime10MGy


