def set_beamsize(sizeV, sizeH):
    """
    Sets Compound Refractive Lenses (CRL) to defocus the beam
    
    sizeV: Vertical expansion
      'V0' no expansion
      'V1': 1 V CRL, for a V beam size of ~10um
      
    sizeH: Horizontal expansion
      'H0': no expansion
      'H1': 2 H CRLs, for a H beam size of ~10um
    
    Examples
    set_beamsize('V1','H1')
    set_beamsize('V1','H0')
    """
    
    if get_energy()<9000.0:
        print('Warning: For energies < 9 keV, use KB mirrors to defocus, not CRLs')
    
    if sizeV == 'V0':
        yield from bps.mv(transfocator.vs.mv_out, 1)
        yield from bps.mv(transfocator.v2a.mv_out, 1)
        yield from bps.mv(transfocator.v1a.mv_out, 1)
        yield from bps.mv(transfocator.v1b.mv_out, 1)
    elif sizeV == 'V1':
        yield from bps.mv(transfocator.vs.mv_in, 1)
        yield from bps.mv(transfocator.v2a.mv_out, 1)
        yield from bps.mv(transfocator.v1a.mv_out, 1)
        yield from bps.mv(transfocator.v1b.mv_in, 1)
    else:
        print("Error: Vertical size argument has to be \'V0\' or  \'V1\'")
    
    if sizeH == 'H0':
        yield from bps.mv(transfocator.h4a.mv_out, 1)
        yield from bps.mv(transfocator.h2a.mv_out, 1)
        yield from bps.mv(transfocator.h1a.mv_out, 1)
        yield from bps.mv(transfocator.h1b.mv_out, 1)
    elif sizeH == 'H1':
        yield from bps.mv(transfocator.h4a.mv_out, 1)
        yield from bps.mv(transfocator.h2a.mv_in, 1)
        yield from bps.mv(transfocator.h1a.mv_in, 1)
        yield from bps.mv(transfocator.h1b.mv_in, 1)
    else:
        print("Error: Horizontal size argument has to be \'H0\' or  \'H1\'")
    
    return
