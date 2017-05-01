# from databroker import DataBroker as db, get_table

from bluesky.plans import abs_set, trigger, trigger_and_read, read, sleep, subs_decorator

"""
Example:
data = simple_ascan(cam_fs2, "stats1_total", hdcm.p, -2, 2, 100)
# or
data = simple_ascan(keithley, "", hdcm.p, -2, 2, 100)
print data.values
"""
def simple_ascan(camera, stats, motor, start, end, steps):
    gs.DETS = [camera]
    gs.MASTER_DET = camera
 
    stats_name = "_".join((camera.name,stats)) if stats else camera.name
    gs.PLOT_Y = stats_name

    uid = RE(ascan(motor, start, end, steps))[0]
    table = get_table(db[uid])
    try:
        return table[[motor.name, stats_name]]
    except:
        return table[[motor.name+"_readback", stats_name]]

def wire_scan(detector, motor, start, stop, steps, sleep_time=1):
    gonio.py.move(start)
    time.sleep(sleep_time)

    def dwell(detectors, motor, step):
        yield from checkpoint()
        yield from abs_set(motor, step, wait=True)
        yield from sleep(sleep_time)
        
        # Do I need to bundle these?
        # How to get back the detector reading and return the difference to the previous one?
        # How to emit that difference?
        #yield from trigger(detector)
        #yield from wait(detector)
        #yield from read(detector)
        #yield from read(motor)
        
        return (yield from trigger_and_read(list(detectors)+[motor]))
        

    table = LiveTable([detector, motor])
    plot = LivePlot(detector.name, motor.name)

    @subs_decorator([table, plot])
    def inner():
        yield from abs_set(motor, start, wait=True)
        yield from sleep(sleep_time)
        yield from scan([detector], motor, start, stop, steps, per_step=dwell)
    
    uid = RE(inner)
    data = get_table(db[uid])
    y = data[detector.name]
    dy = np.diff(y)
    x = data[motor.name]

    plt.plot(x[1:], dy)
    return get_table(db[uid])
    
