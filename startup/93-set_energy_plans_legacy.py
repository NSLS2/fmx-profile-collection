## Set energy legacy plans

def hdcm_rock(hdcm_p_range=0.03, hdcm_p_points=51, logging=True):
    """
    Scan HDCM crystal 2 pitch to maximize flux on BPM1

    Optional arguments:
    hdcm_p_range: HDCM rocking curve range [mrad]. Default 0.03 mrad
    hdcm_p_points: HDCM rocking curve points. Default 51

    Examples:
    RE(hdcm_rock())
    RE(hdcm_rock(hdcm_p_range=0.035, hdcm_p_points=71))
    """

    energy = get_energy()

    LUT = {m: [epics.caget(LUT_fmt.format(m.name, axis))
           for axis in 'XY']
           for m in (hdcm.p, )}

    # Lookup Table
    def lut(motor):
        return motor, np.interp(energy, *LUT[motor])

    yield from bps.mv(
        *lut(hdcm.p)    # Set Pitch interpolated position
    )

    # Setup plots
    ax1 = plt.subplot(111)
    ax1.grid(True)
    plt.tight_layout()

    # Decorate find_peaks to play along with our plot and plot the peak location
    def find_peak_inner(detector, motor, start, stop, num, ax):
        det_name = detector.name+'_sum_all'
        mot_name = motor.name+'_user_setpoint'

        @bpp.subs_decorator(LivePlot(det_name, mot_name, ax=ax))
        def inner():
            peak_x, peak_y = yield from find_peak(detector, motor, start, stop, num)
            ax.plot([peak_x], [peak_y], 'or')
            return peak_x, peak_y
        return inner()

    # Scan DCM Pitch
    peak_x, peak_y = yield from find_peak_inner(bpm1, hdcm.p, -hdcm_p_range, hdcm_p_range, hdcm_p_points, ax1)
    yield from bps.mv(hdcm.p, peak_x)

    if logging:
        print('Energy = {:.1f} eV'.format(energy))       
        print('HDCM cr2 pitch = {:.3f} mrad'.format(hdcm.p.user_readback.get()))
        print('BPM1 sum = {:.4g} A'.format(bpm1.sum_all.get()))
        
    plt.close()
    
    
@bpp.reset_positions_decorator([slits1.x_gap, slits1.y_gap])
def set_energy(energy, hdcm_p_range=0.03, hdcm_p_points=51):
    """
    Sets undulator, HDCM, HFM and KB settings for a certain energy

    energy: Photon energy [eV]

    Optional arguments:
    hdcm_p_range: HDCM rocking curve range [mrad]. Default 0.03 mrad
    hdcm_p_points: HDCM rocking curve points. Default 51

    Lookup tables and variables are set in a settings notebook:
    settings/set_energy setup FMX.ipynb

    Examples:
    RE(set_energy(12660))
    RE(set_energy(7110, hdcm_p_range=0.035, hdcm_p_points=71))
    """

    # MF 20180331: List lacked hdcm.r. Added by hand. Consider using LUT_valid here (set above).
    # Order is also different, probably irrelevant
    LUT = {m: [epics.caget(LUT_fmt.format(m.name, axis))
           for axis in 'XY']
           for m in (ivu_gap.gap, hdcm.g, hdcm.r, hdcm.p, hfm.y, hfm.x, hfm.pitch, kbm.hy, kbm.vx)}

    LUT_offset = [epics.caget(LUT_fmt.format('ivu_gap_off', axis)) for axis in 'XY']

    LGP = {m: epics.caget(LGP_fmt.format(m.name))
           for m in (kbm.hp, kbm.hx, kbm.vp, kbm.vy)}

    # Open Slits 1
    yield from bps.mv(
        slits1.x_gap, 3000,
        slits1.y_gap, 2000
    )
    
    # Remove CRLs if going to energy < 9 keV
    if energy < 9001:
        set_beamsize('V0','H0')
    
    # Lookup Table
    def lut(motor):
        if motor is ivu_gap:
            return motor, np.interp(energy, *LUT[motor.gap])
        else:
            return motor, np.interp(energy, *LUT[motor])

    # Last Good Position
    def lgp(motor):
        return motor, LGP[motor]

    yield from bps.mv(
        *lut(ivu_gap),   # Set IVU Gap interpolated position
        hdcm.e, energy,  # Set Bragg Energy pseudomotor
        *lut(hdcm.g),    # Set DCM Gap interpolated position
        *lut(hdcm.r),    # Set DCM Roll interpolated position # MF 20180331
        *lut(hdcm.p),    # Set Pitch interpolated position

        # Set HFM from interpolated positions
        *lut(hfm.x),
        *lut(hfm.y),
        *lut(hfm.pitch),

        # Set KB from interpolated positions
        *lut(kbm.vx),
        *lut(kbm.hy),

        # Set KB from known good setpoints
        *lgp(kbm.vy), *lgp(kbm.vp),
        *lgp(kbm.hx), *lgp(kbm.hp)
    )

    # Setup plots
    ax1 = plt.subplot(311)
    ax1.grid(True)
    ax2 = plt.subplot(312)
    ax2.grid(True)
    ax3 = plt.subplot(313)
    plt.tight_layout()

    # Decorate find_peaks to play along with our plot and plot the peak location
    def find_peak_inner(detector, motor, start, stop, num, ax):
        det_name = detector.name+'_sum_all'
        mot_name = motor.gap.name+'_user_setpoint' if motor is ivu_gap else motor.name+'_user_setpoint'

        # Prevent going below the lower limit or above the high limit
        if motor is ivu_gap:
            step_size = (stop - start) / (num - 1)
            while motor.gap.user_setpoint.get() + start < motor.gap.low_limit:
                start += 5*step_size
                stop += 5*step_size

            while motor.gap.user_setpoint.get() + stop > motor.gap.high_limit:
                start -= 5*step_size
                stop -= 5*step_size

        @bpp.subs_decorator(LivePlot(det_name, mot_name, ax=ax))
        def inner():
            peak_x, peak_y = yield from find_peak(detector, motor, start, stop, num)
            ax.plot([peak_x], [peak_y], 'or')
            return peak_x, peak_y
        return inner()

    # Scan DCM Pitch
    peak_x, peak_y = yield from find_peak_inner(bpm1, hdcm.p, -hdcm_p_range, hdcm_p_range, hdcm_p_points, ax1)
    yield from bps.mv(hdcm.p, peak_x)

    # Scan IVU Gap
    peak_x, peak_y = yield from find_peak_inner(bpm1, ivu_gap, -100, 100, 41, ax2)
    yield from bps.mv(ivu_gap, (peak_x + np.interp(energy, *LUT_offset)))

    # Get image
    prefix = 'XF:17IDA-BI:FMX{FS:2-Cam:1}image1:'
    image = epics.caget(prefix+'ArrayData')
    width = epics.caget(prefix+'ArraySize0_RBV')
    height = epics.caget(prefix+'ArraySize1_RBV')
    ax3.imshow(image.reshape(height, width), cmap='jet')

    
    
