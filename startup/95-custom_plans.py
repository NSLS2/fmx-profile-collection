from bluesky import plans as bp

def mirror_scan(mir, start, end, steps, gap=None, speed=None, camera=None):
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

    @subs_decorator([lp1, lp2, LiveTable([y1, y2])])
    @reset_positions_decorator([cam.acquire, cam.trigger_mode, slt_ctr, slt_gap,
                                stats.enable, stats.compute_centroid])
    @reset_positions_decorator([slt_ctr.velocity]) # slt_ctr.velocity has to be restored before slt_ctr
    @run_decorator()
    def inner():
        # Prepare statistics plugin
        yield from bp.mv(
            stats.enable, 1,
            stats.compute_centroid, 1
        )

        # Prepare Camera
        yield from bp.mv(cam.acquire, 0)      # Stop camera...
        yield from bp.sleep(.5)               # ...and wait for the pipeline to empty.
        yield from bp.mv(
            cam.trigger_mode, "Sync In 1",    # External Trigger
            cam.array_counter, 0,
        )
        yield from bp.abs_set(cam.acquire, 1) # wait=False

        # Move to the starting positions
        yield from bp.mv(
            slt_gap, gap,                     # Move gap to desired position
            slt_ctr, start - move_slack,      # Move slits to the beginning of the motion
            stats.ts_control, "Erase/Start",  # Prepare statistics Time Series
        )

        # Set Slits Center velocity for the scan
        yield from bp.mv(slt_ctr.velocity, speed)

        # Go
        yield from bp.kickoff(flyer, wait=True)
        st = yield from bp.complete(flyer)
        yield from bp.abs_set(slt_ctr, end + move_slack)

        while not st.done:
            yield from bp.collect(flyer, stream=True)
            RE._uncollected.add(flyer)        # TODO: This is a hideous hack until the next bluesky version. Remove this line
            yield from bp.sleep(0.5)

        yield from bp.sleep(1)
        yield from bp.collect(flyer, stream=True)

        yield from bp.mv(stats.ts_control, "Stop")

    yield from inner()

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

    @reset_positions_decorator([cam.acquire, cam.trigger_mode, cam.min_x, cam.min_y,
                                cam.size.size_x, cam.size.size_y, gonio.py, gonio.pz,
                                tiff.file_write_mode, tiff.num_capture, tiff.auto_save,
                                tiff.auto_increment, tiff.file_path, tiff.file_name,
                                tiff.file_number, tiff.enable])
    @reset_positions_decorator([gonio.py.velocity, gonio.pz.velocity])
    @run_decorator()
    def inner():
        # Prepare Camera
        yield from bp.mv(cam.acquire, 0)      # Stop camera...
        yield from bp.sleep(.5)               # ...and wait for the pipeline to empty.
        yield from bp.mv(
            cam.trigger_mode, "Sync In 1",    # External Trigger
            cam.array_counter, 0,
        )

        if use_roi4:
            yield from bp.mv(
                cam.min_x, roi.min_xyz.min_x.get(),
                cam.min_y, roi.min_xyz.min_y.get(),
                cam.size.size_x, roi.size.x.get(),
                cam.size.size_y, roi.size.y.get()
            )

        # Prepare TIFF Plugin
        yield from bp.mv(
            tiff.file_write_mode, "Stream",
            tiff.num_capture, steps,
            tiff.auto_save, 1,
            tiff.auto_increment, 1,
            tiff.file_path, folder,
            tiff.file_name, filename,
            tiff.file_template, "%s%s_%d.tif",
            tiff.file_number, 1,
            tiff.enable, 1)

        yield from bp.abs_set(tiff.capture, 1)

        yield from bp.abs_set(cam.acquire, 1) # wait=False

        # Move to the starting positions
        yield from bp.mv(
            gonio.py, start_y - slack_y,
            gonio.pz, start_z - slack_z,
        )

        # Set velocity for the scan
        yield from bp.mv(
            gonio.py.velocity, speed_y,
            gonio.pz.velocity, speed_z
        )

        # Arm Zebra
        yield from bp.abs_set(zebra.pos_capt.arm.arm, 1)

        # Wait Zebra armed
        while not zebra2.download_status.get():
            time.sleep(0.1)

        # Go
        yield from bp.mv(
            gonio.py, end_y + slack_y,
            gonio.pz, end_z + slack_z
        )

        yield from abs_set(tiff.capture, 0)

        print(f"{cam.array_counter.get()} images captured")

    yield from inner()
    
@bp.reset_positions_decorator([hhls.x_gap, hhls.y_gap])
def set_energy(energy):
    
    # Values on 2017-07-20
    energies = [ 5000, 6000,  6539,  7110,  7200,  7500,  7600,  8052,  8331,  
                 8979, 9660, 10000, 10400, 10500, 10871, 11564, 11919, 12284, 
                12660, 13400, 13474, 13500]
    
    # LookUp Tables
    LUT = {
        ivu_gap: (energies, [6.895, 7.865, 8.385, 9.025, 9.062, 9.367, 6.490, 
                             6.758, 6.925, 7.303, 7.698, 7.905, 8.139, 6.447, 
                             6.615, 6.908, 7.065, 7.219, 7.375, 6.440, 6.462, 
                             6.476]),
        
        hdcm.g: (energies, [16.331, 15.887, 15.737, 15.616, 15.600, 15.550, 
                            15.535, 15.474, 15.430, 15.378, 15.324, 15.302, 
                            15.279, 15.273, 15.254, 15.224, 15.211, 15.198, 
                            15.186, 15.166, 15.164, 15.163]),
        
        hfm.y: ([5000, 10400, 10400.001, 13500], [0, 0, -8, -8]),
        hfm.x: ([5000, 13500], [1.3, 1.3]),
        hfm.pitch: ([5000, 13500], [-2.547, -2.547])
    }
    
    # Last Good Position
    LGP = {
        hdcm.p: 1.396,
        kbm.vx:  4500,
        kbm.vy:  -494,
        kbm.vp: -2547,
        kbm.hx:   506,
        kbm.hy:  7000,
        kbm.hp: -2402
    }
 
    # Open HHL Slits
    yield from bp.mv(
        hhls.x_gap, 3,
        hhls.y_gap, 2
    )
    
    # Lookup Table
    def lut(motor):
        return motor, np.interp(energy, *LUT[motor])
    
    # Last Good Position
    def lgp(motor):
        return motor, LGP[motor]
    
    yield from bp.mv(
        *lut(ivu_gap),   # Set IVU Gap interpolated position
        hdcm.e, energy,  # Set Bragg Energy pseudomotor
        *lut(hdcm.g),    # Set DCM Gap interpolated position
        *lgp(hdcm.p),    # Set Pitch to last known good position
        
        # Set HFM from interpolated positions
        *lut(hfm.x),
        *lut(hfm.y),
        *lut(hfm.pitch),
        
        # Set KB from known good setpoints
        *lgp(kbm.vx), *lgp(kbm.vy), *lgp(kbm.vp), 
        *lgp(kbm.hx), *lgp(kbm.hy), *lgp(kbm.hp)
    )

    # Setup plots
    ax1 = plt.subplot(211)
    ax1.grid(True)
    ax2 = plt.subplot(212)
    ax2.grid(True)
    plt.tight_layout()
    
    # Decorate find_peaks to play along with our plot and plot the peak location
    def find_peak_inner(detector, motor, start, stop, num, ax):
        @bp.subs_decorator(LivePlot(detector, motor, ax=ax))
        def inner():
            peak_x, peak_y = yield from find_peak(detector, motor, start, stop, num)
            ax.plot([peak_x], [peak_y], 'or')
            return peak_x, peak_y
        return inner()
    
    # Scan DCM Pitch
    peak_x, peak_y = yield from find_peak_inner(bpm1, hdcm.p, -.02, .02, 41, ax1)
    yield from bp.mv(hdcm.p, peak_x)

    # Scan IVU Gap
    peak_x, peak_y = yield from find_peak_inner(bpm1, ivu_gap, -.1, .1, 41, ax2)
    yield from bp.mv(ivu_gap, peak_x)

