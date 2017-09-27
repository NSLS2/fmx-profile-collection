# from databroker import DataBroker as db, get_table

from bluesky.plans import abs_set, trigger, trigger_and_read, read, sleep, subs_decorator

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
    
