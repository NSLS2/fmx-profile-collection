from databroker import DataBroker as db, get_table

def my_macro():
    print('Hi')
    wh_pos()
    print('Hello 4')

"""
Example:
data = simple_scan(cam_fs2, "stats1_total", hdcm.p, -2, 2, 100)
print data.values
"""
def simple_ascan(camera, stats, motor, start, end, steps):
    gs.DETS = [camera]
    gs.MASTER_DET = camera
 
    stats_name = "_".join((camera.name,stats)) 
    gs.PLOT_Y = stats_name

    uid = RE(ascan(motor, start, end, steps))[0]
    table = get_table(db[uid])
    try:
        return table[[motor.name, stats_name]]
    except:
        return table[[motor.name+"_readback", stats_name]]

