import bluesky.preprocessors as bpp
import bluesky.plans as bp
import bluesky.plan_stubs as bps
import epics


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

    #@bpp.subs_decorator([LivePlot(stats_name, motor_name), LiveTable([motor_name, stats_name])])
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

    requested_time = cam.acquire_time.get()*steps
    time_slack = requested_time
    total_time = requested_time + time_slack

    gap = slt_gap.position if gap is None else gap
    minus_start = start - gap / 2
    minus_end = end + gap / 2

    if speed is None:
        fps = cam.array_rate.get()
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
        fps = cam.array_rate.get()
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

