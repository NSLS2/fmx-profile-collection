import bluesky.preprocessors as bpp
import bluesky.plans as bp
import bluesky.plan_stubs as bps
import epics
import pandas as pd


def simple_ascan(camera, stats, motor, start, end, steps):
    """ Simple absolute scan of a single motor against a single camera.

    Automatically plots the results.
    """

    stats_name = "_".join((camera.name,stats)) if stats else camera.name
    try:
        motor_name = motor.readback.name
    except AttributeError:
        try:
            motor_name = motor.gap.name
        except AttributeError:
            motor_name = motor.name

    @bpp.subs_decorator([LivePlot(stats_name, motor_name), LiveTable([motor_name, stats_name])])
    @bpp.reset_positions_decorator([motor])
    def inner():
        yield from bp.scan([camera], motor, start, end, steps)

    yield from inner()


def mirror_scan(mir, start, end, steps, gap=None, speed=None, camera=None, filepath=None, filename=None):
    """Scans a slit aperture center over a mirror against a camera

    Parameters
    ----------

    mir: str
        One of "hfm", "kbh" or "kbv". This is what is scanned:

         mirror |    slits    |    camera
        --------+-------------+--------------
          hfm   | slt:1 horiz | Scr:4 SSA US
          kbh   | slt:3 horiz |   Low Mag
          kbv   | slt:3 vert  |   Low Mag

    start: float
        The starting position (um) of the aperture center

    end: float
        The ending position (um) of the aperture center

    steps: int
        The number of steps (number of points) to take

    speed: float (default=None)
        The speed (um/s) with which to move the aperture. If `None`, this
        scan will try to calculate the maximum theoretical speed based on
        the current frame rate of the camera. Failing that, the speed will
        be arbitrarily set to 15 um/s.

    gap: float (default=None)
        The size of the gap in um. If `None`, the current gap will be used.

    camera: camera object (default=None)
        The camera to be used in this scan. If `None`, the camera listed
        in the table above will be used depending on the selected mirror.

    filepath and filename: strings (default=None)
        Where to save the generated TIFF files and with which name prefix.
        If any of these are set to None, TIFF files won't be saved.
        The path refers to the filesystem on the IOC machine that runs the
        respective camera IOC:
            AMX: xf17id2b-ioc2
            FMX: xf17id1c-ioc2

    """
    mirrors = {
        'hfm': {
            'name': "Horizontal Focusing Mirror",
            'zebra': zebra1,
            'slt_minus': slits1.i,
            'slt_ctr': slits1.x_ctr,
            'slt_gap': slits1.x_gap,
            'camera': cam_fs4, # SSA US
            'encoder_idx': 3,
        },
        'kbh': {
            'name': "Horizontal KB Mirror",
            'zebra': zebra2,
            'slt_minus': slits3.i,
            'slt_ctr': slits3.x_ctr,
            'slt_gap': slits3.x_gap,
            'camera': cam_7, # Lo-Mag
            'encoder_idx': 2,
        },
        'kbv': {
            'name': "Vertical KB Mirror",
            'zebra': zebra2,
            'slt_minus': slits3.b,
            'slt_ctr': slits3.y_ctr,
            'slt_gap': slits3.y_gap,
            'camera': cam_7, # Lo-mag
            'encoder_idx': 3,
        },
    }

    m = mirrors[mir]
    name        = m['name']
    zebra       = m['zebra']
    slt_minus   = m['slt_minus']
    slt_ctr     = m['slt_ctr']
    slt_gap     = m['slt_gap']
    cam         = camera.cam if camera else m['camera'].cam
    tiff        = camera.tiff if camera else m['camera'].tiff
    stats       = camera.stats4 if camera else m['camera'].stats4
    encoder_idx = m['encoder_idx']

    # Calculate parameters
    abs_move = abs(end - start)
    move_slack = abs_move*0.02

    requested_time = cam.acquire_time.value*steps
    time_slack = requested_time
    total_time = requested_time + time_slack

    gap = slt_gap.position if gap is None else gap
    minus_start = start - gap / 2
    minus_end = end + gap / 2

    if speed is None:
        fps = cam.array_rate.value
        if fps:
            speed = 0.9*abs_move*fps/steps
        else:
            speed = 15

    print("speed:", speed, "um/s")

    encoders = [False]*4
    encoders[encoder_idx] = True

    zebra.setup(
        master=encoder_idx,
        arm_source=0, # soft
        gate_start=minus_start,
        gate_width=abs_move/steps/2,
        gate_step=abs_move/steps,
        num_gates=steps,
        direction=int(start > end),

        # Pulse configuration is irrelevant
        # Pulse width must be less than pulse step
        pulse_width=0.5,
        pulse_step=1,
        capt_delay=0,
        max_pulses=1,

        # Only collect the relevant encoder
        collect=encoders
    )

    class CustomFlyer(Device):
        def __init__(self, *args, **kwargs):
            self._last_point = 0
            self._collection_ts = None

            self._ts = zebra.pos_capt.data.time
            self._centroid_x = stats.ts_centroid.x
            self._centroid_y = stats.ts_centroid.y
            self._enc = getattr(zebra.pos_capt.data, f'enc{encoder_idx+1}')

            self._data_sources = (self._centroid_x, self._centroid_y, self._enc)

            super().__init__(*args, **kwargs)

        def kickoff(self):
            self._collection_ts = time.time()
            return zebra.kickoff()

        def complete(self):
            return zebra.complete()

        def collect(self):
            data = {
                sig: sig.get(use_monitor=False) for sig in self._data_sources
            }

            timestamps = self._ts.get(use_monitor=False) + self._collection_ts

            min_len = min([len(d) for d in data.values()])
            cur_time = time.time()

            for i in range(self._last_point, min_len):
                yield {
                    'data': { sig.name: data[sig][i] for sig in data },
                    'timestamps': { sig.name: timestamps[i] for sig in data },
                    'time': cur_time
                }

            self._last_point = min_len

        def describe_collect(self):
            return {
                'primary': {
                    sig.name: {
                        'source': 'PV:' + sig.pvname,
                        'shape': [],
                        'dtype': 'number'
                    } for sig in self._data_sources
                }
            }

    flyer = CustomFlyer('', name='flyer')

    # Setup plot
    y1 = stats.ts_centroid.x.name
    y2 = stats.ts_centroid.y.name
    x = getattr(zebra.pos_capt.data, f'enc{encoder_idx+1}').name

    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    lp1 = LivePlot(y1, x, ax=ax1, color='r')
    lp2 = LivePlot(y2, x, ax=ax2, color='b')

    # Set axes labels after creating LivePlots
    ax1.set_title(name)
    ax1.set_xlabel('Center Position')
    ax1.set_ylabel('Centroid X', color='r')
    ax2.set_ylabel('Centroid Y', color='b')

    @bpp.subs_decorator([lp1, lp2, LiveTable([y1, y2])])
    @bpp.reset_positions_decorator([cam.acquire, cam.trigger_mode, slt_gap, #slt_ctr, <- this fails with FailedStatus
                                    stats.enable, stats.compute_centroid])
    @bpp.reset_positions_decorator([tiff.enable, tiff.auto_increment, tiff.file_path, tiff.file_name,
                                    tiff.file_template, tiff.file_write_mode, tiff.num_capture])
    @bpp.reset_positions_decorator([slt_ctr.velocity]) # slt_ctr.velocity has to be restored before slt_ctr
    @bpp.run_decorator()
    def inner():
        # Prepare TIFF plugin
        if filepath is not None and filename is not None:
            fp = filepath

            if fp[-1] != '/':
                fp+= '/'

            print("Saving files as", "".join((fp, filename, "_XXX.tif")))
            print("First file number:", cam_8.tiff.file_number.get())

            yield from bps.mv(
                tiff.enable, 1,
                tiff.auto_increment, 1,
                tiff.file_path, fp,
                tiff.file_name, filename,
                tiff.file_template, "%s%s_%3.3d.tif",
                tiff.file_write_mode, 1, # Capture mode
                tiff.num_capture, steps,
            )

        # Prepare statistics plugin
        yield from bps.mv(
            stats.enable, 1,
            stats.compute_centroid, 1
        )

        # Prepare Camera
        yield from bps.mv(cam.acquire, 0)   # Stop camera...

        yield from bps.sleep(.5)               # ...and wait for the pipeline to empty.
        yield from bps.mv(
            cam.trigger_mode, "Sync In 1",    # External Trigger
            cam.array_counter, 0,
        )
        yield from bps.abs_set(cam.acquire, 1) # wait=False
        # DAMA (mrakitin) comment 2019-08-20: the tiff plugin is not used (images are not saved)
        # (see https://github.com/NSLS-II-FMX/profile_collection/issues/3 for details), so commenting it out
        # yield from bps.abs_set(tiff.capture, 1)

        # Move to the starting positions
        yield from bps.mv(
            slt_gap, gap,                     # Move gap to desired position
            slt_ctr, start - move_slack,      # Move slits to the beginning of the motion
            stats.ts_control, "Erase/Start",  # Prepare statistics Time Series
        )

        # Set Slits Center velocity for the scan
        yield from bps.mv(slt_ctr.velocity, speed)

        # Go
        yield from bps.kickoff(flyer, wait=True, group='kickoff')
        st = (yield from bps.complete(flyer))
        yield from bps.abs_set(slt_ctr, end + move_slack)

        while not st.done:
            yield from bps.collect(flyer, stream=True)
            yield from bps.sleep(0.2)

        yield from bps.sleep(1)
        yield from bps.collect(flyer, stream=True)

        yield from bps.mv(stats.ts_control, "Stop")

        # Stop the camera after the scan
        yield from bps.mv(cam.acquire, 0)   # Stop camera...

    yield from inner()


def find_peak(det, mot, start, stop, steps):
    print(f"Scanning {mot.name} vs {det.name}...")

    uid = yield from bp.relative_scan([det], mot, start, stop, steps)

    sp = '_gap_user_setpoint' if mot is ivu_gap else '_user_setpoint'
    output = '_sum_all' if det is bpm1 else ''
    data = np.array(db[uid].table()[[det.name+output, mot.name+sp]])[1:]

    peak_idx = np.argmax(data[:, 0])
    peak_x = data[peak_idx, 1]
    peak_y = data[peak_idx, 0]

    if mot is ivu_gap:
        m = mot.gap
    else:
        m = mot
    print(f"Found peak for {m.name} at {peak_x} {m.egu} [BPM reading {peak_y}]")
    return peak_x, peak_y


def wire_scan(detector, motor, start, stop, steps, sleep_time=1):
    """
    Use with Cr nanowire to determine beam size

    Motors to be scanned for FMX beam size
    Vertical: Gonio Y (around 24830), with Gonio X = 214370 um
    Horizontal: Gonio X (around 206270), with Gonio Y = 16420 um

    Cr ROIs for Mercury MCA: 510 570

    Examples
    RE(wire_scan(mercury, gonio.gx, 206260, 206280, 50, sleep_time=0.5))
    RE(wire_scan(mercury, gonio.gy, 24820, 24840, 50, sleep_time=1))
    """
    last_reading = None
    def dwell(detectors, motor, step):
        yield from bps.checkpoint()
        yield from bps.abs_set(motor, step, wait=True)
        yield from bps.sleep(sleep_time)

        return (yield from bps.trigger_and_read(list(detectors)+[motor]))

    table = LiveTable([detector, motor])
    y_name = detector.name
    if y_name == 'mercury':
        y_name += '_mca_rois_roi0_count'
    plot = LivePlot(y_name, motor.name)

    @bpp.subs_decorator([table, plot])
    def inner():
        yield from bps.abs_set(motor, start, wait=True)
        yield from bps.sleep(sleep_time)
        yield from scan([detector], motor, start, stop, steps, per_step=dwell)

    yield from inner()

#
# Helper functions for set_energy
#

LUT_fmt = "XF:17ID-ES:FMX{{Misc-LUT:{}}}{}-Wfm"
LGP_fmt = "XF:17ID-ES:FMX{{Misc-LGP:{}}}Pos-SP"

LUT_valid = (ivu_gap.gap, hdcm.g, hdcm.r, hdcm.p, hfm.y, hfm.x, hfm.pitch, kbm.hy, kbm.vx, atten)
LGP_valid = (kbm.hp, kbm.hx, kbm.vp, kbm.vy)

LUT_valid_names = [m.name for m in LUT_valid] + ['ivu_gap_off']
LGP_valid_names = [m.name for m in LGP_valid]

def read_lut(name):
    """
    Reads the LookUp table values for a specific motor
    """
    if name not in LUT_valid_names:
        raise ValueError('name must be one of {}'.format(LUT_valid_names))

    x, y = [epics.caget(LUT_fmt.format(name, axis)) for axis in 'XY']
    return pd.DataFrame({'Energy':x, 'Position': y})


def write_lut(name, energy, position):
    """
    Writes to the LookUp table for a specific motor
    """
    if name not in LUT_valid_names:
        raise ValueError('name must be one of {}'.format(LUT_valid_names))

    if len(energy) != len(position):
        raise ValueError('energy and position must have the same number of points')

    epics.caput(LUT_fmt.format(name, 'X'), energy)
    epics.caput(LUT_fmt.format(name, 'Y'), position)


def read_lgp(name):
    """
    Reads the Last Good Position value for a specific motor
    """
    if name not in LGP_valid_names:
        raise ValueError('name must be one of {}'.format(LGP_valid_names))

    return epics.caget(LGP_fmt.format(name))

def write_lgp(name, position):
    """
    Writes to the Last Good Position value for a specific motor
    """
    if name not in LGP_valid_names:
        raise ValueError('name must be one of {}'.format(LGP_valid_names))

    return epics.caput(LGP_fmt.format(name), position)


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
            while motor.gap.user_setpoint.value + start < motor.gap.low_limit:
                start += 5*step_size
                stop += 5*step_size

            while motor.gap.user_setpoint.value + stop > motor.gap.high_limit:
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
    
    
def setE_motors_FMX(energy):
    """
    Sets undulator, HDCM, HFM and KB settings for a certain energy from a lookup table

    energy: Photon energy [eV]

    Lookup tables and variables are set in a settings notebook:
    settings/set_energy setup FMX.ipynb

    Examples:
    setE_motors_FMX(12660)
    """

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
        print('HDCM cr2 pitch = {:.3f} mrad'.format(hdcm.p.user_readback.value))
        print('BPM1 sum = {:.4g} A'.format(bpm1.sum_all.value))
        
    plt.close()
    
    
def dcm_rock(dcm_p_range=0.03, dcm_p_points=51, logging=True, altDetector=False):
    """
    Scan DCM crystal 2 pitch to maximize flux on BPM1
    dcm_rock() runs both with the AMX VDCM and the FMX HDCM

    Parameters
    ----------
    
    Optional arguments:
    dcm_p_range: DCM rocking curve range [mrad]. Default 0.03 mrad
    dcm_p_points: DCM rocking curve points. Default 51
    altDetector: If True, uses alternate detector, BPM1 at AMX and Keithley at FMX

    Examples
    --------
    
    RE(dcm_rock())
    RE(dcm_rock(altDetector = True))
    RE(dcm_rock(dcm_p_range=0.035, dcm_p_points=71))
    """
    blStr = blStrGet()
    if blStr == -1: return -1
    
    if blStr == 'AMX':
        rock_mot = vdcm.p
        rock_det = bpm1 if altDetector is True else keithley
    elif blStr == 'FMX':
        rock_mot = hdcm.p
        rock_det = keithley if altDetector is True else bpm1
    
    energy = get_energy()
        
    LUT = {m: [epics.caget(LUT_fmt.format(m.name, axis))
           for axis in 'XY']
           for m in (rock_mot, )}

    # Lookup Table
    def lut(motor):
        return motor, np.interp(energy, *LUT[motor])

    yield from bps.mv(
        *lut(rock_mot)    # Set Pitch interpolated position
    )

    # Setup plots
    ax1 = plt.subplot(111)
    ax1.grid(True)
    plt.tight_layout()
    
    # Decorate find_peaks to play along with our plot and plot the peak location
    def find_peak_inner(detector, motor, start, stop, num, ax):
        if detector == bpm1:
            det_name = detector.name+'_sum_all'
        else:
            det_name = detector.name                
        mot_name = motor.name+'_user_setpoint'

        @bpp.subs_decorator(LivePlot(det_name, mot_name, ax=ax))
        def inner():
            peak_x, peak_y = yield from find_peak(detector, motor, start, stop, num)
            ax.plot([peak_x], [peak_y], 'or')
            return peak_x, peak_y
        return inner()

    # Scan DCM Pitch
    peak_x, peak_y = yield from find_peak_inner(rock_det, rock_mot, -dcm_p_range, dcm_p_range, dcm_p_points, ax1)
    yield from bps.mv(rock_mot, peak_x)

    if logging:
        print('Energy = {:.1f} eV'.format(energy))       
        print('HDCM cr2 pitch = {:.3f} mrad'.format(rock_mot.user_readback.value))
        if rock_det == bpm1:
            print('BPM1 sum = {:.4g} A'.format(bpm1.sum_all.value))
        elif  rock_det == keithley:
            time.sleep(2.0)  # Range switching is slow
            print('Keithley current = {:.4g} A'.format(keithley.value))
        
    plt.close()
        
    
def ivu_gap_scan(start, end, steps, detector=bpm1, goToPeak=True):
    """
    Scans the IVU21 gap against a detector, and moves the gap to the peak plus a
    energy dependent look-up table set offset

    Parameters
    ----------
    
    start: float
        The starting position (um) of the VU21 undulator gap scan
    
    end: float
        The end position (um) of the VU21 undulator gap scan
        
    steps: int
        Number of steps in the scan
    
    detector: ophyd detector
        The ophyd detector for the scan. Default is bpm1. Only setup up for the quad BPMs right now
    
    goToPeak: boolean
        If True, go to the peak plus energy-tabulated offset. If False, go back to pre-scan value.
    
    Examples
    --------
    
    RE(ivu_gap_scan(7350, 7600, 70))
    RE(ivu_gap_scan(7350, 7600, 70, goToPeak=False))
    RE(ivu_gap_scan(7350, 7600, 70, detector=bpm4))
    """
        
    energy = get_energy()
    
    motor=ivu_gap
    if start-1 < motor.gap.low_limit:
        start = motor.gap.low_limit + 1
        print('start violates lowest limit, set to %.1f' % start + ' um')
    
    LUT_offset = [epics.caget(LUT_fmt.format('ivu_gap_off', axis)) for axis in 'XY']
    
    # Setup plots
    ax = plt.subplot(111)
    ax.grid(True)
    plt.tight_layout()

    # Decorate find_peaks to play along with our plot and plot the peak location
    def find_peak_inner(detector, motor, start, stop, num, ax):
        det_name = detector.name+'_sum_all'
        mot_name = motor.gap.name+'_user_setpoint' if motor is ivu_gap else motor.name+'_user_setpoint'

        # Prevent going below the lower limit or above the high limit
        if motor is ivu_gap:
            step_size = (stop - start) / (num - 1)
            while motor.gap.user_setpoint.value + start < motor.gap.low_limit:
                start += 5*step_size
                stop += 5*step_size

            while motor.gap.user_setpoint.value + stop > motor.gap.high_limit:
                start -= 5*step_size
                stop -= 5*step_size

        @bpp.subs_decorator(LivePlot(det_name, mot_name, ax=ax))
        def inner():
            peak_x, peak_y = yield from find_peak(detector, motor, start, stop, num)
            ax.plot([peak_x], [peak_y], 'or')
            return peak_x, peak_y
        return inner()
    
    # Remember pre-scan value
    gapPreStart=motor.gap.user_readback.value
    
    # Move to start
    yield from bps.mv(motor, start)
    
    # Scan IVU Gap
    peak_x, peak_y = yield from find_peak_inner(detector, ivu_gap, 0, (end-start), steps, ax)
    
    # Go to peak
    if goToPeak==True:
        peakoffset_x = (peak_x + np.interp(energy, *LUT_offset))
        yield from bps.mv(ivu_gap, peakoffset_x)
        print('Gap set to peak + tabulated offset: %.1f' % peakoffset_x + ' um')
    else:
        yield from bps.mv(ivu_gap, gapPreStart)
        print('Gap set to pre-scan value: %.1f' % gapPreStart + ' um')
    
    plt.close()
    

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

    
def setE(energy,
         dcm_p_range=0.03, dcm_p_points=51, altDetector=False,
         ivuGapStartOff=70, ivuGapEndOff=70, ivuGapSteps=31,
         attenSet='All', beamCenterAlign=True):
    """
    Automated photon energy change. Master function calling four subroutines:
    * setE_motors_FMX():    Set photon delivery system motor positions for a chosen energy
    * dcm_rock():           Go to peak of monochromator rocking curve
    * ivu_gap_scan():       Go to peak of undulator gap
    * beam_center_align():  Set LSDC crosshair to beam center
                            Move rotation axis to beam heightS
                            Set governor Gonio Y Work position
    
    Requirements
    ------------
    Governor in state SA
    FOE and hutch photon shutter open
    
    
    Parameters
    ----------
    
    energy: Photon energy [eV]
    
    dcm_p_range: Scan range of DCM Crystal 2 Pitch [mrad], default = 0.03
    dcm_p_points: Number of scan points of SCM rocking curve, default = 51
    altDetector: Rocking curve to use alternate detector between BPM1 and endstation diode, default = False
    
    ivuGapStartOff: IVU gap scan start offset from tabulated position [um], default = 70
    ivuGapEndOff: IVU gap scan end offset from tabulated position [um], default = 70
    ivuGapSteps: IVU gap scan steps, default = 31
    
    attenSet: FMX only: Set to 'RI' if there is a problem with the BCU attenuator.
              FMX only: Set to 'BCU' if there is a problem with the RI attenuator.
              Set to 'None' if there are problems with all = attenuators.
              Operator then has to choose a flux by hand that will not saturate scinti
              default = 'All'
    
    beamCenterAlign: Set to False to skip beam_center_align() step (like the old set_energy() routine)
                     Default True
    
    Examples
    --------
    
    RE(setE(7110))
    RE(setE(10000, attenSet='None'))
    RE(setE(12660, attenSet='RI'))
    RE(setE(20000, ivuGapStartOff=100, ivuGapEndOff=150, ivuGapSteps=91))
    RE(setE(9000, beamCenterAlign=False))
    """
    
    # Store initial Slit 1 gap positions
    slits1XGapOrg = slits1.x_gap.user_readback.value
    slits1YGapOrg = slits1.y_gap.user_readback.value
    
    print('Setting FMX motor positions')
    try:
        yield from setE_motors_FMX(energy)
    except:
        print('setE_motors_FMX() failed')
        raise
    else:
        print('setE_motors_FMX() successful')
        time.sleep(1)
    
    # Check for pre-conditions for dcm_rock() and ivu_gap_scan()
    if shutter_foe_position_status_get():
        print('FOE shutter closed. Has to be open for this to work. Exiting')
        return -1
        
    print('Rocking monochromator')
    yield from dcm_rock(dcm_p_range=dcm_p_range, dcm_p_points=dcm_p_points, altDetector=altDetector)
    time.sleep(1)
        
    print('Scanning undulator gap')
    start = ivu_gap.gap.user_readback.value - ivuGapStartOff
    end = ivu_gap.gap.user_readback.value + ivuGapEndOff
    try:
        yield from ivu_gap_scan(start, end, ivuGapSteps, goToPeak=True)
    except:
        print('ivu_gap_scan() failed')
        raise
    else:
        print('ivu_gap_scan() successful')
        time.sleep(1)
    
    if beamCenterAlign:
        # Check for pre-conditions for beam_center_align()
        if shutter_eshutch_position_status_get():
            print('Experiment hutch shutter closed. Has to be open for this to work. Exiting')
            return -1
        if not govStatusGet('SA'):
            print('Not in Governor state SA, exiting')
            return -1
        
        print('Aligning beam center')
        yield from beam_center_align(attenSet=attenSet)
    
    # Restore initial Slit 1 gap positions
    yield from bps.mv(slits1.x_gap, slits1XGapOrg)  # Move Slit 1 X to original position
    yield from bps.mv(slits1.y_gap, slits1YGapOrg)  # Move Slit 1 Y to original position

    
    
def focus_scan(steps, step_size=2, speed=None, cam=cam_7, filename='test', folder='/tmp/', use_roi4=False):
    """ Scans a sample along Z against a camera, taking pictures in the process.

    Parameters
    ----------

    steps: int
        The number of steps (number of points) to take

    step_size: float
        The size of each step (um). Default: 2 um

    speed: float (default=None)
        The speed (um/s) with which to move. If `None`, this
        scan will try to calculate the maximum theoretical speed based on
        the current frame rate of the camera. Failing that, the speed will
        be arbitrarily set to 15 um/s.

    cam: camera object (default=cam_7 (Low Mag))
        The camera that will take the pictures.

    filename: str
        The file name for the acquired pictures. Default: 'test'

    folder: str
        The folder where to write the images to. Default: '/tmp'

    use_roi4: bool
        If True, temporarily set the camera ROI to the same dimensions as the ROI4
        plugin during the acquisition. Default: False
    """
    if folder[-1] != '/':
        folder += '/'

    # Devices
    py = gonio.py
    pz = gonio.pz
    zebra = zebra3
    tiff = cam.tiff
    roi = cam.roi4
    cam = cam.cam

    # Calculate parameters
    total_move = steps*step_size
    move_slack = total_move*0.02

    if speed is None:
        fps = cam.array_rate.value
        if fps:
            speed = 0.9*total_move*fps/steps
        else:
            speed = 15

    print("speed:", speed, "um/s")

    omega = gonio.o.user_setpoint.get()

    def calc_params(mtr):
        f = sin(radians(-omega)) if mtr == py else cos(radians(omega))
        cur = mtr.position
        start = cur - f*total_move/2
        end = cur + f*total_move/2
        total = abs(end-start)
        slack = move_slack*f if f else 0
        spd = abs(speed*f) if f else 0
        return start, end, total, slack, spd

    start_y, end_y, total_y, slack_y, speed_y = calc_params(py)
    start_z, end_z, total_z, slack_z, speed_z = calc_params(pz)

    # Choose master motor
    if(total_y > total_z):
        start, end, total, encoder_idx = start_y, end_y, total_y, 1
    else:
        start, end, total, encoder_idx = start_z, end_z, total_z, 2

    print("Master motor:", {1:"y", 2:"z"}[encoder_idx])

    zebra.setup(
        master=encoder_idx,
        arm_source=0, # soft
        gate_start=start,
        gate_width=total/steps/2,
        gate_step=total/steps,
        num_gates=steps,
        direction=int(start > end),

        # Pulse configuration is irrelevant
        # Pulse width must be less than pulse step
        pulse_width=0.5,
        pulse_step=1,
        capt_delay=0,
        max_pulses=1,

        # Only collect PY and PZ
        collect=[False, True, True, False]
    )

    @bpp.reset_positions_decorator([cam.acquire, cam.trigger_mode, cam.min_x, cam.min_y,
                                cam.size.size_x, cam.size.size_y, gonio.py, gonio.pz,
                                tiff.file_write_mode, tiff.num_capture, tiff.auto_save,
                                tiff.auto_increment, tiff.file_path, tiff.file_name,
                                tiff.file_number, tiff.enable])
    @bpp.reset_positions_decorator([gonio.py.velocity, gonio.pz.velocity])
    @bpp.run_decorator()
    def inner():
        # Prepare Camera
        yield from bps.mv(cam.acquire, 0)      # Stop camera...
        yield from bps.sleep(.5)               # ...and wait for the pipeline to empty.
        yield from bps.mv(
            cam.trigger_mode, "Sync In 1",    # External Trigger
            cam.array_counter, 0,
        )

        if use_roi4:
            yield from bps.mv(
                cam.min_x, roi.min_xyz.min_x.get(),
                cam.min_y, roi.min_xyz.min_y.get(),
                cam.size.size_x, roi.size.x.get(),
                cam.size.size_y, roi.size.y.get()
            )

        # Prepare TIFF Plugin
        yield from bps.mv(
            tiff.file_write_mode, "Stream",
            tiff.num_capture, steps,
            tiff.auto_save, 1,
            tiff.auto_increment, 1,
            tiff.file_path, folder,
            tiff.file_name, filename,
            tiff.file_template, "%s%s_%d.tif",
            tiff.file_number, 1,
            tiff.enable, 1)

        yield from bps.abs_set(tiff.capture, 1)

        yield from bps.abs_set(cam.acquire, 1) # wait=False

        # Move to the starting positions
        yield from bps.mv(
            gonio.py, start_y - slack_y,
            gonio.pz, start_z - slack_z,
        )

        # Set velocity for the scan
        yield from bps.mv(
            gonio.py.velocity, speed_y,
            gonio.pz.velocity, speed_z
        )

        # Arm Zebra
        yield from bps.abs_set(zebra.pos_capt.arm.arm, 1)

        # Wait Zebra armed
        while not zebra2.download_status.get():
            time.sleep(0.1)

        # Go
        yield from bps.mv(
            gonio.py, end_y + slack_y,
            gonio.pz, end_z + slack_z
        )

        yield from bps.abs_set(tiff.capture, 0)

        print(f"{cam.array_counter.get()} images captured")

    yield from inner()

