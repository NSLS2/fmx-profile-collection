# from databroker import DataBroker as db, get_table

#def my_macro():
#    print('Hi')
#    wh_pos()
#    print('Hello 4')

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
        return (yield from trigger_and_read(list(detectors)+[motor]))
    
    plan = scan([detector], motor, start, stop, steps, per_step=dwell)

    s = RE(plan, [LiveTable([detector, motor]), LivePlot(detector.name, motor.name)])
    data = get_table(db[s])
    y = data[detector.name]
    dy = np.diff(y)
    x = data[motor.name]

    plt.plot(x[1:], dy)
    
