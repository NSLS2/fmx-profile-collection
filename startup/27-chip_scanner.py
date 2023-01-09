# https://nsls-ii.github.io/ophyd/positioners.html#pseudopositioner
from ophyd import (PseudoPositioner, PseudoSingle, EpicsMotor)
from ophyd import (Component as Cpt)
from ophyd.pseudopos import (pseudo_position_argument,
                             real_position_argument)


class ChipScanner(PseudoPositioner):
    # The pseudo positioner axes:
    x = Cpt(PseudoSingle, limits=(-20000, 20000))
    y = Cpt(PseudoSingle, limits=(-20000, 20000))
    z = Cpt(PseudoSingle, limits=(-20000, 20000))

    # The real (or physical) positioners:
    pz1 = Cpt(EpicsMotor, 'XF:17IDC-ES:FMX{Gon:1-Ax:PZ}Mtr')
    py1 = Cpt(EpicsMotor, 'XF:17IDC-ES:FMX{Gon:1-Ax:PY}Mtr')
    pz2 = Cpt(EpicsMotor, 'XF:17IDC-ES:FMX{Gon:2-Ax:PZ}Mtr')

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        '''Run a forward (pseudo -> real) calculation'''
        return self.RealPosition(pz1 = -pseudo_pos.x,
                                 py1 = -pseudo_pos.y,
                                 pz2 =  pseudo_pos.z)

    @real_position_argument
    def inverse(self, real_pos):
        '''Run an inverse (real -> pseudo) calculation'''
        return self.PseudoPosition(x = -real_pos.pz1,
                                   y = -real_pos.py1,
                                   z =  real_pos.pz2)
    
chipsc = ChipScanner(name='chipsc')


def autofocus(camera, stats, motor, start, end, steps, move2Focus=True):
    """
    Chip scanner autofocus
    
    Scan axis, e.g. chipsc.z vs ROI stats sigma_x, and drive to position that minimizes sigma_x
    
    The scan is relative to the current position
    
    Examples:
    RE(autofocus(cam_8, 'stats4_sigma_x', chipsc4.z, -400,400,15))
    RE(autofocus(cam_7, 'stats4_sigma_x', chipsc4.z, -600,600,15, move2Focus=False))
    """
    # Best-Effort Callback table will interfere with LiveTable
    # Check if set, if yes store current setting, disable for scan, reset at end
    try:
        bec
    except NameError:
        bec_exists = False
    else:
        bec_exists = True
        bec_table_enabled = bec._table_enabled
        bec.disable_table()
    
    fig, ax1 = plt.subplots()
    ax1.grid(True)

    stats_name = "_".join((camera.name,stats))
    @bpp.subs_decorator(LivePlot(stats_name, motor.name, ax=ax1))
    @bpp.subs_decorator(LiveTable([motor.name, stats_name], default_prec=5))
    def inner(camera, motor, start, end, steps):
        uid = yield from bp.relative_scan([camera], motor, start, end, steps)
        return uid
    
    # Find minimum
    uid = yield from inner(camera, motor, start, end, steps)
    data = np.array(db[uid].table()[[stats_name, motor.name]])[1:]
    min_idx = np.argmin(data[:, 0])
    min_x = data[min_idx, 1]
    min_y = data[min_idx, 0]

    print(f"Found focus for {motor.name} at {min_x} {motor.egu} [{stats_name} = {min_y:0.2f}]")
    ax1.plot([min_x], [min_y], 'or')
    
    if move2Focus:
        yield from bps.mv(motor, min_x)
    
    # Reset Best-Effort Callback table settings to previous settings
    if bec_exists and bec_table_enabled:
        bec.enable_table()