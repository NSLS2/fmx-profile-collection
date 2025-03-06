from ophyd import EpicsMotor
from ophyd import Component as Cpt
from ophyd import Device
from ophyd.signal import EpicsSignalRO, EpicsSignal
from ophyd.status import SubscriptionStatus
import bluesky.plan_stubs as bps
import numpy as np
import time
import re
import epics
import glob
import scipy
import pickle

from collections import namedtuple

from pathlib import Path


save_dir = '/epics/iocs/notebook/notebooks/chip_fiducials'
droplet_dir = '/epics/iocs/notebook/notebooks/chip_droplets'


Fiducial_Location = namedtuple('Fiducial_Location', ['motor_loc', 'encoder_loc', 'chip_loc'])
Save_Objects = namedtuple('Save_Objects', ['fiducials', 'additional_fiducials', 'droplet_references'])


def configure_zebra_for_chip_scanner():
    zebra.pc.encoder.put(0)
    zebra.pc.arm.trig_source.put(0)
    zebra.pc.gate.sel.put(0)
    zebra.pc.pulse.sel.put(1)
    zebra.pc.pulse.start.put(1)
    zebra.pc.pulse.width.put(4)
    zebra.pc.pulse.step.put(10)
    zebra.pc.pulse.max.put(1)
    epics.caput("XF:17IDC-ES:FMX{Zeb:3}:M1:MRES", 0.01)
    time.sleep(0.5)
    epics.caput("XF:17IDC-ES:FMX{Zeb:3}:M1:SETPOS.PROC", 1)


class ppmac_input(Device):
    prog = Cpt(EpicsSignal, 'Program')
    dwell = Cpt(EpicsSignal, 'Dwell')
    drop_dwell = Cpt(EpicsSignal, 'DropDwell')
    move_time = Cpt(EpicsSignal, 'Move')
    go = Cpt(EpicsSignal, 'Go')
    input_string = Cpt(EpicsSignal, 'Input')
    mode = Cpt(EpicsSignal, 'Mode')
    x_positions = Cpt(EpicsSignal, 'X_POSNS')
    y_positions = Cpt(EpicsSignal, 'Y_POSNS')
    dwell_times = Cpt(EpicsSignal, 'DWELLS')
    drop_bools = Cpt(EpicsSignal, 'DROPS')
    capture_bools = Cpt(EpicsSignal, 'IMAGES')
    x_0 = Cpt(EpicsSignal, 'X0')
    x_displacement = Cpt(EpicsSignal, 'X_VEC')
    y_displacement = Cpt(EpicsSignal, 'Y_VEC')
    end = Cpt(EpicsSignalRO, "End")

    def create_program_from_points(self, program_number, move_time, x_list, y_list, dwell_list, drop_list, capture_list, start_position, fiducial_x, fiducial_y):
        self.mode.put('POSITIONS')
        self.move_time.put(move_time)
        self.prog.put(program_number)
        self.x_0.put(start_position)
        self.x_displacement.put(fiducial_x*5/1016) # Distance between x wells = 25400*5/1016 = 125
        self.y_displacement.put(fiducial_y*5/1016) # Distance between y wells = 25400*5/1016 = 125
        self.x_positions.put(x_list)
        self.y_positions.put(y_list)
        self.dwell_times.put(dwell_list)
        self.drop_bools.put(drop_list)
        self.capture_bools.put(capture_list)
        setattr(self, f'ready{program_number}', True)

    def send_program(self, program_number, dwell_time, move_time, input_array, drop_dwell=None):
        self.mode.put('STRING')
        self.dwell.put(dwell_time)
        if drop_dwell:
            self.drop_dwell.put(drop_dwell)
        else:
            self.drop_dwell.put(dwell_time)
        self.move_time.put(move_time)
        self.prog.put(program_number)
        i_string = ""
        for row in input_array:
            i_string = i_string + f'x{row[0]}y{row[1]}_'
        self.input_string.put(i_string[:-1])
        setattr(self, f'ready{program_number}', True)

    def run_program(self, program_number):
        if hasattr(self, f'ready{program_number}'):
            self.go.put(1)
        else:
            print(f'Must create program {program_number} first!')

ppmac_channel = ppmac_input('XF:17ID-CT:FMX{MC17:Sender}', name='ppmac_channel')


class MotorWithEncoder(EpicsMotor):
    encoder_readback = Cpt(EpicsSignalRO, ".RRBV", kind="hinted", auto_monitor=True)


class ChipScanner(Device):
    x = Cpt(MotorWithEncoder, 'XF:17IDC-ES:FMX{Chip:1-Ax:CX}Mtr')
    y = Cpt(MotorWithEncoder, 'XF:17IDC-ES:FMX{Chip:1-Ax:CY}Mtr')
    z = Cpt(MotorWithEncoder, 'XF:17IDC-ES:FMX{Gon:2-Ax:GZ}Mtr')

    drpyz = Cpt(EpicsMotor, 'XF:17IDC-ES:FMX{Drp:1-Ax:YZ}Mtr')
    drpy = Cpt(EpicsMotor, 'XF:17IDC-ES:FMX{Drp:1-Ax:Y}Mtr')
    drpx = Cpt(EpicsMotor, 'XF:17IDC-ES:FMX{Drp:1-Ax:X}Mtr')

    def __init__(self, F0_x, F0_y, F1_x, F1_y, F2_x, F2_y,
                 BLnum_x, BLnum_y, BLgap_x, BLgap_y,
                 APnum_x, APnum_y, APgap_x, APgap_y,
                 lo_camera, hi_camera, **kwargs):
        super().__init__(**kwargs)

        self.F0_x = F0_x
        self.F0_y = F0_y
        self.F1_x = F1_x
        self.F1_y = F1_y
        self.F2_x = F2_x
        self.F2_y = F2_y

        self.BLnum_x = BLnum_x
        self.BLnum_y = BLnum_y
        self.BLgap_x = BLgap_x
        self.BLgap_y = BLgap_y

        self.APnum_x = APnum_x
        self.APnum_y = APnum_y
        self.APgap_x = APgap_x
        self.APgap_y = APgap_y

        self.lo_camera = lo_camera
        self.hi_camera = hi_camera

        self.lo_camera_ratios = (BL_calibration.LoMagCal.get(), BL_calibration.LoMagCal.get())
        self.hi_camera_ratios = (BL_calibration.HiMagCal.get(), BL_calibration.HiMagCal.get())

        self.filepath = None
        
        self.additional_fiducials = {}

    def set_droplet_reference_1(self):
        self.z_ref_1 = self.z.get().user_readback
        self.yz_ref_1 = self.drpyz.get().user_readback
        self.y_ref_1 = self.drpy.get().user_readback
        self.x_ref_1 = self.drpx.get().user_readback

    #def set_droplet_reference_2(self):
    #    self.z_ref_2 = self.z.get().user_readback
    #    self.yz_ref_2 = self.drpyz.get().user_readback
    #    self.y_ref_2 = self.drpy.get().user_readback
    #    self.x_ref_2 = self.drpx.get().user_readback

    def correct_droplet_offset(self, y_offset = 0):
        offset = -self.z.get().user_readback + self.z_ref_1
        #slope = (self.y_ref_1 - self.y_ref_2) / (self.z_ref_1 - self.z_ref_2)
        slope = 1
        y = -slope*offset + self.y_ref_1
        yield from bps.mv(self.drpy, y+y_offset)

    def manual_set_fiducial(self, location):
        x_loc = self.x.get().user_readback
        y_loc = self.y.get().user_readback
        z_loc = self.z.get().user_readback

        x_loc_enc = self.x.get().encoder_readback
        y_loc_enc = self.y.get().encoder_readback
        z_loc_enc = self.z.get().encoder_readback

        setattr(self, location+"_x_motor", x_loc)
        setattr(self, location+"_y_motor", y_loc)
        setattr(self, location+"_z_motor", z_loc)

        setattr(self, location+"_x_motor_enc", x_loc_enc)
        setattr(self, location+"_y_motor_enc", y_loc_enc)
        setattr(self, location+"_z_motor_enc", z_loc_enc)

        setattr(self, location, np.array([x_loc, y_loc, z_loc]))
        setattr(self, location + "_enc", np.array([x_loc_enc, y_loc_enc, z_loc_enc]))
        
    def override_fiducials(self, points = None):
        if points is not None:
            if len(points) != 3:
                print(f"Refiducialization currently only supports 3 points, {len(points)} were given.")
                return False
            for p in points:
                if p not in self.additional_fiducials:
                    print(f"Point {p} is not present in the additional_fiducials dictionary, failed to refiducialize.")
                    return False
        else:
            if len(self.additional_fiducials) < 3:
                print(f"At least 3 additional fiducials must be present in the additional_fiducials dictionary to refiducialize, but only {len(self.additional_fiducials)} are present.")
                return(False)
            elif len(self.additional_fiducials) > 3:
                print(f"More than 3 additional fiducials identified, refiducializing on {list(self.additional_fiducials.keys())[0:3]}.")
            points = list(self.additional_fiducials.keys())[0:3]

        p0_ns = self.additional_fiducials[points[0]][2]
        d1 = self.additional_fiducials[points[1]][2] - self.additional_fiducials[points[0]][2]
        d2 = self.additional_fiducials[points[2]][2] - self.additional_fiducials[points[0]][2]

        M = np.transpose(np.vstack([d1, d2]))
        Minv = np.linalg.inv(M)
        
        v1 = self.additional_fiducials[points[1]][0] - self.additional_fiducials[points[0]][0]
        v2 = self.additional_fiducials[points[2]][0] - self.additional_fiducials[points[0]][0]
        
        v1_enc = self.additional_fiducials[points[1]][1] - self.additional_fiducials[points[0]][1]
        v2_enc = self.additional_fiducials[points[2]][1] - self.additional_fiducials[points[0]][1]
        
        V = np.transpose(np.vstack([v1, v2]))

        V_enc = np.transpose(np.vstack([v1_enc, v2_enc]))
        tvecs = np.matmul(V, Minv)
        
        tvecs_enc = np.matmul(V_enc, Minv)

        self.f0t = np.squeeze(np.asarray(np.reshape(self.additional_fiducials[points[0]][0] - p0_ns[0]*tvecs[:,0] - p0_ns[1]*tvecs[:,1], (3,1))))
        self.f1t = np.squeeze(np.asarray(np.reshape(self.additional_fiducials[points[0]][0] - (p0_ns[0]-25400)*tvecs[:,0] - p0_ns[1]*tvecs[:,1], (3,1))))
        self.f2t = np.squeeze(np.asarray(np.reshape(self.additional_fiducials[points[0]][0] - p0_ns[0]*tvecs[:,0] - (p0_ns[1]-25400)*tvecs[:,1], (3,1))))
        
        self.f0t_enc = np.squeeze(np.asarray(np.reshape(self.additional_fiducials[points[0]][1] - p0_ns[0]*tvecs_enc[:,0] - p0_ns[1]*tvecs_enc[:,1], (3,1))))
        self.f1t_enc = np.squeeze(np.asarray(np.reshape(self.additional_fiducials[points[0]][1] - (p0_ns[0]-25400)*tvecs_enc[:,0] - p0_ns[1]*tvecs_enc[:,1], (3,1))))
        self.f2t_enc = np.squeeze(np.asarray(np.reshape(self.additional_fiducials[points[0]][1] - p0_ns[0]*tvecs_enc[:,0] - (p0_ns[1]-25400)*tvecs_enc[:,1], (3,1))))
        
        for i in range(3):
            setattr(self, f'F{i}', getattr(self,f'f{i}t'))
            setattr(self, f'F{i}_enc', getattr(self, f'f{i}t_enc'))
            
    def use_as_fiducial(self, location):
        chip_x, chip_y = self.name_to_fiducial_distances(location)
        motor_loc = self.fiducial_distances_to_location(chip_x, chip_y)

        x_loc = self.x.get().user_readback
        y_loc = self.y.get().user_readback
        z_loc = self.z.get().user_readback

        x_loc_enc = self.x.get().encoder_readback
        y_loc_enc = self.y.get().encoder_readback
        z_loc_enc = self.z.get().encoder_readback

        if not np.linalg.norm(np.array([x_loc, y_loc, z_loc]) - motor_loc) < 50:
            print("Current location is outside of allowed region for correction, please redo the manual_set_fiducial routine and retry.")
            return False

        mloc = np.array([x_loc, y_loc, z_loc])
        eloc = np.array([x_loc_enc, y_loc_enc, z_loc_enc])
        cloc = np.array(self.name_to_fiducial_distances(location))
        self.additional_fiducials[location] = Fiducial_Location(mloc, eloc, cloc)
        
    def calculate_fit(self):
        ab = self.F1 - self.F0
        ac = self.F2 - self.F0
        print(f"Distance between fiducial F0 and F1: {np.linalg.norm(ab):6.0f}um")
        print(f"Distance between fiducial F0 and F2: {np.linalg.norm(ac):6.0f}um")
        cos_theta = np.dot(ab, ac)/np.linalg.norm(ab)/np.linalg.norm(ac)
        theta = np.arccos(np.clip(cos_theta, -1, 1))
        print(f"Angle between vectors: {theta:6.4f}radians ({theta*180/np.pi:6.3f}deg)")
        return(np.linalg.norm(ab), np.linalg.norm(ac), np.arccos(np.clip(cos_theta, -1, 1)))

    def get_fiducials(self):
        return self.F0, self.F1, self.F2, self.F0_enc, self.F1_enc, self.F2_enc

    def save_fiducials(self, filepath=None):
        if not filepath:
            current_time = time.strftime("%Y%m%d-%H%M")
            filepath = save_dir+"/current_fiducials-"+current_time+"rs.txt"
        with open(filepath, 'ab') as f:
            for arr in self.get_fiducials():
                np.save(f, arr)

    def load_fiducials(self, filepath=None):
        if not filepath:
            list_of_files = glob.glob(f'{save_dir}/*')
            filepath = max(list_of_files, key=os.path.getctime)
        to_load = ['F0', 'F1', 'F2', 'F0_enc', 'F1_enc', 'F2_enc']
        with open(filepath, 'rb') as f:
            for prop in to_load:
                setattr(self, prop, np.load(f))

    def load_last_fiducials(self):
        list_of_files = glob.glob(f'{save_dir}/*')
        latest_file = max(list_of_files, key=os.path.getctime)
        self.load_fiducials(latest_file)

    def set_fiducials(self, F0, F1, F2, F0e, F1e, F2e):
        self.F0 = F0
        self.F1 = F1
        self.F2 = F2
        self.F0_enc = F0e
        self.F1_enc = F1e
        self.F2_enc = F2e

    def save_droplet_reference(self, filepath=None):
        params = ["z_ref_1", "yz_ref_1", "y_ref_1", "x_ref_1"]#, "z_ref_2", "yz_ref_2", "y_ref_2", "x_ref_2"]
        if not filepath:
            current_time = time.strftime("%Y%m%d-%H%M")
            filepath = droplet_dir+"/current_droplet_ref-"+current_time+"rs.txt"
        with open(filepath, 'ab') as f:
            for p in params:
                np.save(f,getattr(self, p))

    def load_droplet_reference(self, filepath=None):
        params = ["z_ref_1", "yz_ref_1", "y_ref_1", "x_ref_1"]#, "z_ref_2", "yz_ref_2", "y_ref_2", "x_ref_2"]
        if not filepath:
            list_of_files = glob.glob(f'{droplet_dir}/*')
            filepath = max(list_of_files, key=os.path.getctime)
        with open(filepath, 'rb') as f:
            for p in params:
                setattr(self, p, np.load(f))

    def save_all(self, filepath=None):
        if not filepath:
            current_time = time.strftime("%Y%m%d-%H%M")
            filepath = droplet_dir+"/fiducials_ref-"+current_time+".txt"
        fiducials = (self.F0, self.F1, self.F2, self.F0_enc, self.F1_enc, self.F2_enc)
        try:
            params = ["z_ref_1", "yz_ref_1", "y_ref_1", "x_ref_1"]
            droplets = [getattr(self, p) for p in params]
        except AttributeError as e:
            droplets = None
        to_save = Save_Objects(fiducials, self.additional_fiducials, droplets)
        with open(filepath, 'wb') as f:
            pickle.dump(to_save, f, protocol=pickle.HIGHEST_PROTOCOL)

    def load_all(self, filepath=None):
        if not filepath:
            list_of_files = glob.glob(f'{droplet_dir}/*')
            filepath = max(list_of_files, key=os.path.getctime)
        with open(filepath, 'rb') as f:
            to_load = pickle.load(f)
        fs = ['F0', 'F1', 'F2', 'F0_enc', 'F1_enc', 'F2_enc']
        for i, f in enumerate(fs):
            setattr(self, f, to_load[0][i])
        self.additional_fiducials = to_load[1]
        if to_load[2] is not None:
            params = ["z_ref_1", "yz_ref_1", "y_ref_1", "x_ref_1"]
            for i, f in enumerate(params):
                setattr(self, f, to_load[2][i])

    def center_on_point(self):
        yield from bps.sleep(0.5)
        focus_size = 200  # Size to cover large fiducial, not the small neighbors
        MagCal = BL_calibration.HiMagCal.get()

        if not hasattr(self, "ROI_centers"):
            mins = self.hi_camera.roi1.min_xyz.get()
            sizes = self.hi_camera.roi1.size.get()
            self.ROI_centers = [int(mins.min_y + sizes.y/2), int(mins.min_x + sizes.x/2)]

        hi_image = self.hi_camera.image.image
        with open(f'hi_pictures/hcam{int(time.time()*10)}.npy', 'wb') as f:
            np.save(f, hi_image)

        d2d = np.sum(hi_image, axis=2)[self.ROI_centers[0]-100:self.ROI_centers[0]+100, self.ROI_centers[1]-100:self.ROI_centers[1]+100]

        blurred_image = scipy.ndimage.gaussian_filter(d2d, 8, truncate=3.0)
        with open(f'hi_pictures/blurred{int(time.time()*10)}.npy', 'wb') as f:
            np.save(f, hi_image)
        center_y, center_x = np.unravel_index(np.argmax(blurred_image, axis=None), blurred_image.shape)

        dx_mot =  MagCal * (center_x - int(focus_size/2))
        dy_mot =  -MagCal * (center_y - int(focus_size/2))
        print(d2d, center_y, center_x, dx_mot, dy_mot)
        yield from bps.mvr(self.x, dx_mot, self.y, dy_mot)
        with open(f'hi_pictures/hcam{int(time.time()*10)}.npy', 'wb') as f:
            np.save(f, hi_image)
        yield from bps.sleep(0.5)
        with open(f'hi_pictures/hcam{int(time.time()*10)}.npy', 'wb') as f:
            np.save(f, hi_image)

    def name_to_fiducial_distances(self, location_name):
        """Given a location name of the form @#&& where @ is a capital
        letter from A-H, # is a number from 1-8 and &s are lower case
        letters from a-t, returns the x and y coordinates of the
        desired house on the chip, relative to the fiducials F0=(0,0).

        Only valid for the Oxford Chip."""

        Ny = ord(location_name[0])-65
        Nx = int(location_name[1])-1
        Hy = ord(location_name[2])-97
        Hx = ord(location_name[3])-97

        x_loc = (self.F0_x +
                 Nx*(self.BLgap_x + (self.APnum_x-1)*self.APgap_x) +
                 Hx*self.APgap_x)

        y_loc = (self.F0_y +
                 Ny*(self.BLgap_y + (self.APnum_y-1)*self.APgap_y) +
                 Hy*self.APgap_y)

        return x_loc, y_loc

    def fiducial_distances_to_location(self, x_loc, y_loc, original_fiducials = False):
        """Given distances to the fiducial from the starting point F0=(0,0),
        returns the x, y and z coordinates of the desired house on the chip.

        Only valid for the Oxford Chip."""

        M = np.array([self.F1-self.F0, self.F2-self.F0]).transpose()
        if original_fiducials:
            relative_x_loc = x_loc/self.F1_x
            relative_y_loc = y_loc/self.F2_y
            relative_loc = np.array([relative_x_loc, relative_y_loc])
            motor_coords = np.matmul(M, relative_loc) + self.F0
        else:
            location_options = {np.linalg.norm([x_loc-0, y_loc-0]):'F0', np.linalg.norm([x_loc-25400, y_loc-0]):'F1', np.linalg.norm([x_loc-0, y_loc-25400]):'F2'}
            for loc, pls in self.additional_fiducials.items():
                location_options[np.linalg.norm(pls.chip_loc - np.array([x_loc, y_loc]))] = loc
            closest_location = location_options[min(location_options)]
            if closest_location in ['F0', 'F1', 'F2']:
                motor_loc = self.F0
                chip_loc = [0,0]
            else:
                motor_loc, enc_loc, chip_loc = self.additional_fiducials[closest_location]
            relative_x_loc = (x_loc - chip_loc[0])/self.F1_x
            relative_y_loc = (y_loc - chip_loc[1])/self.F2_y
            relative_loc = np.array([relative_x_loc, relative_y_loc])
            motor_coords = np.matmul(M, relative_loc) + motor_loc

        return(motor_coords)


    def fiducial_distances_to_enc_location(self, x_loc, y_loc):
        """Given distances to the fiducial from the starting point F0=(0,0),
        returns the x, y and z encoder coordinates of the desired house on
        the chip.

        Only valid for the Oxford Chip."""

        relative_x_loc = x_loc/self.F1_x
        relative_y_loc = y_loc/self.F2_y

        relative_loc = np.array([relative_x_loc, relative_y_loc])

        M = np.array([self.F1_enc-self.F0_enc, self.F2_enc-self.F0_enc]).transpose()
        motor_coords = np.matmul(M, relative_loc) + self.F0_enc
        return(motor_coords)

    def drive_to_location(self, location_name):
        chip_x, chip_y = self.name_to_fiducial_distances(location_name)
        motor_loc = self.fiducial_distances_to_location(chip_x, chip_y)
        yield from bps.mv(self.x, motor_loc[0], self.y, motor_loc[1], self.z, motor_loc[2])

    def configure_detector(self, location, triggers, acquisition_time = 0.01):
        #path = '/nsls2/data/fmx/proposals/commissioning/pass-312064/312064-20230706-fuchs/mx312064-1'
        if not self.filepath:
            print(f'Must set filepath attribute for this chip scanner object before taking data, to determine location where the file will be saved.')
            raise Exception('Filepath not found')
        eiger_single.cam.acquire_time.put(acquisition_time)
        eiger_single.cam.fw_num_images_per_file.put(triggers)
        eiger_single.cam.file_path.put(self.filepath)
        if not eiger_single.cam.file_path_exists.get():
            print(f'Filepath {self.filepath} does not appear to be a valid directory recognized by the Eiger detector.')
            raise Exception('Filepath not found')
        eiger_single.cam.num_images.put(triggers)
        eiger_single.cam.num_triggers.put(triggers)
        eiger_single.cam.trigger_mode.put(3)
        my_time = int(time.time())
        eiger_single.cam.fw_name_pattern.put(f'CHIP{location}{my_time}')
        dist = getDetectorDist(configStr = 'Chip_Scanner')
        eiger_single.cam.omega_start.put(0)
        eiger_single.cam.omega_incr.put(0)
        eiger_single.cam.det_distance.put(dist/1000)
        eiger_single.cam.acquire.put(1)

    def pre_line_scan_setup(self, location, n_images, acquisition_time = 10, refocus = False, recenter = True, expose_to_beam=True, transition_before=True):
        self.configure_zebra_for_hare()
        #self.configure_detector(location, n_images, acquisition_time = acquisition_time/1000) # ms -> s
        yield from self.drive_to_location(location)
        if recenter and (transition_before or not expose_to_beam):
            yield from self.center_on_point()
        if refocus and transition_before:
            yield from autofocus(self.hi_camera, 'stats4_sigma_x', self.z, -10,10,15)
        enc_loc = np.array([self.x.get().encoder_readback, self.y.get().encoder_readback])
        return(enc_loc)
        
    def scan_and_cleanup(self, xl, yl, dwell_list, dl, cl, enc_loc, expose_to_beam=True, transition_before=True, transition_after=True):
        ppmac_channel.create_program_from_points(23, 10, xl, yl, dwell_list, dl, cl, enc_loc, self.F1_enc - self.F0_enc, self.F2_enc - self.F0_enc) ############ Might need a sleep here, let's try without first though
        if transition_before:
            govStateSet('CD', configStr = 'Chip_Scanner')
        if expose_to_beam:
            shutter_bcu.open.put(1)
        ppmac_channel.run_program(23)
        endpoint = ppmac_channel.end.get()
        while True:
            loc = np.array([self.x.get().encoder_readback, self.y.get().encoder_readback])
            if abs((loc-endpoint)[0]) < 10 and abs((loc-endpoint)[1]) < 10:
                sleep(0.5)
                break
            sleep(1)
        shutter_bcu.close.put(1)
        eiger_single.cam.acquire.put(0)
        if transition_after:
            govStateSet('CA', configStr = 'Chip_Scanner')

    def line_scan(self, line, acquisition_time = 10, location_offset_x = 0.0, location_offset_y = 0.0, refocus = False, recenter = True, expose_to_beam=True, transition_before=True, transition_after=True):
        pattern = re.compile("^([A-H][1-8][a-t])$")
        if not pattern.match(line):
            print(f"Hare scan requires input of form ex. A1d, got {line}. ")
            return(False)
        self.configure_detector(line, 20, acquisition_time = acquisition_time/1000)
        enc_loc = yield from self.pre_line_scan_setup(line+"a", 20, acquisition_time = acquisition_time, refocus = refocus, recenter = recenter, expose_to_beam=expose_to_beam, transition_before=transition_before)
        xl = list(range(-1,21))
        yl = [0]*22
        dl = [0]*22
        cl = [0] + [1]*20 + [0]
        dwell_list = [acquisition_time]*22
        self.scan_and_cleanup(xl, yl, dwell_list, dl, cl, enc_loc, expose_to_beam=expose_to_beam, transition_before=transition_before, transition_after=transition_after)

    def neighbourhood_scan(self, neighbourhood, acquisition_time = 10, location_offset_x = 0.0, location_offset_y = 0.0, refocus = False, recenter = True, expose_to_beam=True, transition_before=True, transition_after=True):
        pattern = re.compile("^([A-H][1-8])$")
        if not pattern.match(neighbourhood):
            print(f"Hare scan requires input of form ex. A1, got {neighbourhood}.")
            return(False)
        self.configure_detector(neighbourhood, 400, acquisition_time = acquisition_time/1000)
        enc_loc = yield from self.pre_line_scan_setup(neighbourhood+"aa", 400, acquisition_time = acquisition_time, refocus = refocus, recenter = recenter, expose_to_beam=expose_to_beam, transition_before=transition_before)
        xl = []
        yl = []
        dl = []
        cl = []
        dwell_list = []
        for y in range(10):
            xl = xl + list(range(-1,21))
            yl = yl + [y*2]*22
            dl = dl + [0]*22
            cl = cl + [0] + [1]*20 + [0]
            dwell_list = dwell_list + [acquisition_time]*22

            xl = xl + list(range(20,-2,-1))
            yl = yl + [y*2 + 1]*22
            dl = dl + [0]*22
            cl = cl + [0] + [1]*20 + [0]
            dwell_list = dwell_list + [acquisition_time]*22
        self.scan_and_cleanup(xl, yl, dwell_list, dl, cl, enc_loc, expose_to_beam=expose_to_beam, transition_before=transition_before, transition_after=transition_after)

    def calculate_hare(self, drop_to_det_time, droplet_offset_value = 0, acquisition_time = 10, post_drop_dwell_min_time = 10):
        if not post_drop_dwell_min_time >= acquisition_time:
            print(f"post_drop_dwell_min_time ({post_drop_dwell_min_time}) must be greater than or equal to acquisition_time ({acquisition_time}).")
            raise RuntimeError(f"post_drop_dwell_min_time ({post_drop_dwell_min_time}) must be greater than or equal to acquisition_time ({acquisition_time}).")
        motor_speed = epics.caget('XF:17IDC-ES:FMX{Chip:1-Ax:CX}Mtr.VELO')
        well_move_time = 1000/(motor_speed/125)
        min_time = well_move_time/2 + post_drop_dwell_min_time
        if drop_to_det_time < min_time:
            print(f'Minimum available time is {min_time} determined by the delay after the drop trigger prior to a move ({post_drop_dwell_min_time}) and the motor speed ({motor_speed} um/s).')
            raise RuntimeError(f'Minimum available time is {min_time} determined by the delay after the drop trigger prior to a move ({post_drop_dwell_min_time}) and the motor speed ({motor_speed} um/s).')
        steps_ahead = int((drop_to_det_time + 2*well_move_time)/(2*well_move_time+post_drop_dwell_min_time))
        print(f"HARE #{steps_ahead}")
        if steps_ahead == 1:
            pdd = int(drop_to_det_time - .5*drop_to_det_time)
        else:
            pdd = int((drop_to_det_time + 2*well_move_time)/steps_ahead - 2*well_move_time)
        if steps_ahead == 1:
            yield from self.correct_droplet_offset(y_offset=droplet_offset_value)
        else:
            yield from self.correct_droplet_offset(y_offset=-62.5+droplet_offset_value)
        return well_move_time, steps_ahead, pdd

    def line_scan_hare(self, line, drop_to_det_time, droplet_offset_value = 0, acquisition_time = 10, post_drop_dwell_min_time = 10, location_offset_x = 0.0, location_offset_y = 0.0, refocus = False, recenter = True, expose_to_beam=True, transition_before=True, transition_after=True):
        pattern = re.compile("^([A-H][1-8][a-t])$")
        if not pattern.match(line):
            print(f"Hare scan requires input of form ex. A1d, got {line}.")
            return(False)
        self.configure_detector(line, 20, acquisition_time = acquisition_time/1000)
        enc_loc = yield from self.pre_line_scan_setup(line+"a", 20, acquisition_time = acquisition_time, refocus = refocus, recenter = recenter, expose_to_beam=expose_to_beam, transition_before=transition_before)
        well_move_time, steps_ahead, pdd = yield from self.calculate_hare(drop_to_det_time, droplet_offset_value = droplet_offset_value, acquisition_time = acquisition_time, post_drop_dwell_min_time = post_drop_dwell_min_time)
        n_scans, remains = divmod(20, steps_ahead)
        xl = []
        yl = []
        dl = []
        cl = []
        dwell_list = []
        if steps_ahead == 1:
            for n in range(20):
                xl = xl + [-.5 + n] + [n]
                yl = yl + [0] + [0]
                dl = dl + [1] + [0]
                cl = cl + [0] + [1]
                dwell_list = dwell_list + [pdd] + [pdd]
        else:
            for n in range(n_scans):
                xl = xl + [i-.5 + n*steps_ahead for i in range(0,steps_ahead)] + [n*steps_ahead] + [i + n*steps_ahead for i in range(0,steps_ahead)]
                yl = yl + [-.5]*steps_ahead + [-.5] + [0]*steps_ahead
                dl = dl + [1]*steps_ahead + [0] + [0]*steps_ahead
                cl = cl + [0]*steps_ahead + [0] + [1]*steps_ahead
                dwell_list = dwell_list + [pdd]*steps_ahead + [0] + [pdd]*steps_ahead
            if remains != 0:
                xl = xl + [i-.5 + n_scans*steps_ahead for i in range(0,remains)] + [n_scans*steps_ahead] + [i + n_scans*steps_ahead for i in range(0,remains)]
                yl = yl + [-.5]*remains + [-.5] + [0]*remains
                dl = dl + [1]*remains + [0] + [0]*remains
                cl = cl + [0]*remains + [0] + [1]*remains
                dwell_list = dwell_list + [pdd]*remains + [int(drop_to_det_time - well_move_time*2*(remains-1) - pdd*remains)] + [pdd]*remains
        self.scan_and_cleanup(xl, yl, dwell_list, dl, cl, enc_loc, expose_to_beam=expose_to_beam, transition_before=transition_before, transition_after=transition_after)

    def neighbourhood_scan_hare(self, neighbourhood, drop_to_det_time, droplet_offset_value = 0, acquisition_time = 10, post_drop_dwell_min_time = 10, location_offset_x = 0.0, location_offset_y = 0.0, refocus = False, recenter = True, expose_to_beam=True, transition_before=True, transition_after=True):
        ''' drop_to_det_time = pump-probe-delay'''
        pattern = re.compile("^([A-H][1-8])$")
        if not pattern.match(neighbourhood):
            print(f"Hare scan requires input of form ex. A1, got {neighbourhood}.")
            return(False)
        self.configure_detector(neighbourhood, 400, acquisition_time = acquisition_time/1000)
        enc_loc = yield from self.pre_line_scan_setup(neighbourhood+"aa", 400, acquisition_time = acquisition_time, refocus = refocus, recenter = recenter, expose_to_beam=expose_to_beam, transition_before=transition_before)
        well_move_time, steps_ahead, pdd = yield from self.calculate_hare(drop_to_det_time, droplet_offset_value = droplet_offset_value, acquisition_time = acquisition_time, post_drop_dwell_min_time = post_drop_dwell_min_time)
        n_scans, remains = divmod(20, steps_ahead)
        xl = []
        yl = []
        dl = []
        cl = []
        dwell_list = []
        if steps_ahead == 1:
            for y in range(20):
                for n in range(20):
                    xl = xl + [-.5 + n] + [n]
                    yl = yl + [y] + [y]
                    dl = dl + [1] + [0]
                    cl = cl + [0] + [1]
                    dwell_list = dwell_list + [pdd] + [pdd]
        else:
            for y in range(20):
                for n in range(n_scans):
                    xl = xl + [i-.5 + n*steps_ahead for i in range(0,steps_ahead)] + [n*steps_ahead] + [i + n*steps_ahead for i in range(0,steps_ahead)]
                    yl = yl + [y-.5]*steps_ahead + [y-.5] + [y]*steps_ahead
                    dl = dl + [1]*steps_ahead + [0] + [0]*steps_ahead
                    cl = cl + [0]*steps_ahead + [0] + [1]*steps_ahead
                    dwell_list = dwell_list + [pdd]*steps_ahead + [0] + [pdd]*steps_ahead
                if remains != 0:
                    xl = xl + [i-.5 + n_scans*steps_ahead for i in range(0,remains)] + [n_scans*steps_ahead] + [i + n_scans*steps_ahead for i in range(0,remains)]
                    yl = yl + [y-.5]*remains + [y-.5] + [y]*remains
                    dl = dl + [1]*remains + [0] + [0]*remains
                    cl = cl + [0]*remains + [0] + [1]*remains
                    dwell_list = dwell_list + [pdd]*remains + [int(drop_to_det_time - well_move_time*2*(remains-1) - pdd*remains)] + [pdd]*remains
        self.scan_and_cleanup(xl, yl, dwell_list, dl, cl, enc_loc, expose_to_beam=expose_to_beam, transition_before=transition_before, transition_after=transition_after)

    def configure_zebra_for_hare(self):
        epics.caput("XF:17IDC-ES:FMX{Zeb:3}:OUT1_TTL", 7)
        epics.caput("XF:17IDC-ES:FMX{Zeb:3}:OUT3_TTL", 10)

    def check_camera_settings(self, camera):
        if camera.cam.acquire_time.get() > 0.1:
            print(f'{camera} acquireTime > 0.1, which could affect processing. Please reduce this to continue.')
            return(False)
        if camera.cam.image_mode.get() != 2:
            print(f'{camera} not in continuous acquisition mode, please set this and retry.')
            return(False)
        if camera.cam.detector_state.get() != 1:
            print(f'{camera} not acquiring, please start and retry.')
            return(False)
        return(True)


class OxfordChip(ChipScanner):
    def __init__(self, **kwargs):
        super().__init__(400, 400, 25400, 0, 0, 25400,
                         8, 8, 800, 800,
                         20, 20, 125, 125,
                         cam_7, cam_8, **kwargs)

# cz_ref_1hip_scanner = OxfordChip(name='chip_scanner')


def autofocus(camera, stats, motor, start, end, steps, move2Focus=True, max_repeats = 2):
    """
    Chip scanner autofocus

    Scan axis, e.g. chipsc.z vs ROI stats sigma_x, and drive to position that minimizes sigma_x

    The scan is relative to the current position

    Examples:
    RE(autofocus(cam_8, 'stats4_sigma_x', chipsc.z, -40,40,15))
    RE(autofocus(cam_7, 'stats4_sigma_x', chipsc.z, -60,60,15, move2Focus=False))
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
    data = np.array(db[uid].table()[[stats_name, motor.name]])
    min_idx = np.argmin(data[:, 0])
    min_x = data[min_idx, 1]
    min_y = data[min_idx, 0]


    ax1.plot([min_x], [min_y], 'or')

    if move2Focus:
        yield from bps.mv(motor, min_x)

    if min_y < 1:
        print("Failed to find signal in ROI, aborting")
        return False, 0

    if 0 < min_idx < steps-1:
        success = True
    else:
        success = False
        if max_repeats > 0 and move2Focus:
            step_size = abs(end-start)/steps
            if min_idx == 0:
                new_start, new_end = -abs(end-start), step_size
            else:
                new_start, new_end = -step_size, abs(end-start)
            success = yield from autofocus(camera, stats, motor, new_start, new_end, steps, move2Focus=move2Focus, max_repeats = max_repeats - 1)

    # Reset Best-Effort Callback table settings to previous settings
    if bec_exists and bec_table_enabled:
        bec.enable_table()
    return success, min_y

def getDetectorDist(configStr = 'Robot'):
    """
    Returns Governor message

    configStr: Governor configuration, 'Robot' or 'Human', default: 'Robot'

    Examples:
    govMsgGet()
    govMsgGet(configStr = 'Human')
    """
    blStr = blStrGet()
    if blStr == -1: return -1

    sysStr = 'XF:17IDC-ES:' + blStr
    devStr = '{Gov:' + configStr
    stsStr = '-Dev:dz}Pos:In-Pos'
    pvStr = sysStr + devStr + stsStr
    govMsg = epics.caget(pvStr)

    return govMsg

def multiple_chip_neighbourhoods(neighbourhood_list, wait_time = 20, recenter = True, refocus = False):
    for neighbourhood in neighbourhood_list:
        RE(chip_scanner.ppmac_neighbourhood_scan(neighbourhood, wait_time, recenter = recenter, refocus=refocus))

def no_transition_scan(neighbourhood_list, wait_time = 20, recenter = True, refocus = False, with_droplets = False, droplet_wait_time = 20):
    for i, loc in enumerate(neighbourhood_list):
        transition_before = True if i==0 else False
        transition_after = True if i==(len(neighbourhood_list)-1) else False
        if with_droplets:
            yield from chip_scanner.ppmac_neighbourhood_scan_with_droplets(neighbourhood, wait_time, droplet_wait_time, recenter = recenter, refocus=refocus, transition_before=transition_before, transition_after=transition_after)
        else:
            yield from chip_scanner.ppmac_neighbourhood_scan(neighbourhood, wait_time, recenter = recenter, refocus=refocus, transition_before=transition_before, transition_after=transition_after)

def multi_no_transition_scan(list_of_neighbourhood_lists, wait_time = 20, recenter = True, refocus = False, with_droplets = False, droplet_wait_time = 20):
    for scan in list_of_neighbourhood_lists:
        RE(no_transition_scan(scan, wait_time=wait_time, recenter=recenter, refocus=refocus, with_droplets=with_droplets, droplet_wait_time=droplet_wait_time))

def chip_line_of_blocks(line, wait_time = 20):
    neighbourhoods = []
    for i in range(1,9):
        neighbourhoods.append(f'{line}{i}')
    multiple_chip_neighbourhoods(neighbourhoods, wait_time = wait_time)


letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
def chip_all_blocks(wait_time = 20):
    neighbourhoods = []
    for i in range(1,9):
        for letter in letters:
            neighbourhoods.append(f'{letter}{i}')
    multiple_neighbourhoods(neighbourhoods, wait_time = wait_time)



def configure_zebra_for_chip_scanner_with_droplets_scheme_1():
    zebra.pc.encoder.put(0)
    zebra.pc.arm.trig_source.put(0)
    zebra.pc.gate.sel.put(0)
    zebra.pc.pulse.sel.put(1)
    zebra.pc.pulse.start.put(1)
    zebra.pc.pulse.width.put(4)
    zebra.pc.pulse.step.put(10)
    zebra.pc.pulse.max.put(1)
    epics.caput("XF:17IDC-ES:FMX{Zeb:3}:M1:MRES", 0.01)
    time.sleep(0.5)
    epics.caput("XF:17IDC-ES:FMX{Zeb:3}:M1:SETPOS.PROC", 1)
    epics.caput("XF:17IDC-ES:FMX{Zeb:3}:DIV1_INP", 31)
    epics.caput("XF:17IDC-ES:FMX{Zeb:3}:DIV1_DIV", 2)
    epics.caput("XF:17IDC-ES:FMX{Zeb:3}:OUT1_TTL", 44)
    epics.caput("XF:17IDC-ES:FMX{Zeb:3}:OUT3_TTL", 48)


## Reference positions
# Pipette window horizontal
# - IB edge in beam center: -16300.000 um
# - OB edge in beam center: -19100.000 um
# - Window center in beam center (PAx): (-16300.000 -19100.000)/2 = -17700.0 +- 1400.0
# Pipette window vertical:
# - Top edge in beam center: -3500.000 um
# - Bottom edge in beam center: 2300.000 um
# - Window center in beam center (PAy, if not choosing 0): (-3500.000 + 2300.000)/2 = -600 +- 2900.0

import epics

# EPICS PV names
chx_LLM = "XF:17IDC-ES:FMX{Chip:1-Ax:CX}Mtr.LLM"
chx_HLM = "XF:17IDC-ES:FMX{Chip:1-Ax:CX}Mtr.HLM"
chy_LLM = "XF:17IDC-ES:FMX{Chip:1-Ax:CY}Mtr.LLM"
chy_HLM = "XF:17IDC-ES:FMX{Chip:1-Ax:CY}Mtr.HLM"

def pipalign_get_limits():
    """
    Returns a dictionary containing the motor limits for PA and CA states
    """
    return {
        'CA': {
            'chx': {'LLM': -14000, 'HLM': 14000},
            'chy': {'LLM': -14000, 'HLM': 14000}
        },
        'PA': {
            'chx': {'LLM': -19300, 'HLM': -16100},
            'chy': {'LLM': -3500, 'HLM': 2300}
        }
    }

def pipalign_set_limits(state, motor=None, limit_type=None, limits=None):
    """
    Sets motor limits flexibly - can set a single limit or all limits for a state
    
    Parameters
    ----------
    state : str
        Either 'PA' or 'CA'
    motor : str, optional
        'chx' or 'chy'. If None, sets limits for both motors
    limit_type : str, optional
        'LLM' or 'HLM'. If None, sets both limits
    limits : dict, optional
        Dictionary containing the limits. If None, uses default limits
    
    Examples
    --------
    # Set all limits for CA state
    pipalign_set_limits('CA')
    
    # Set only chx HLM for PA state
    pipalign_set_limits('PA', 'chx', 'HLM')
    """
    if limits is None:
        limits = pipalign_get_limits()
    
    state_limits = limits[state]
    
    # Map of limit types to their PV names
    pv_map = {
        'chx': {'LLM': chx_LLM, 'HLM': chx_HLM},
        'chy': {'LLM': chy_LLM, 'HLM': chy_HLM}
    }
    
    # If motor and limit_type specified, set only that limit
    if motor and limit_type:
        epics.caput(pv_map[motor][limit_type], state_limits[motor][limit_type])
        return
    
    # If only motor specified, set both limits for that motor
    if motor:
        for lim_type in ['LLM', 'HLM']:
            epics.caput(pv_map[motor][lim_type], state_limits[motor][lim_type])
        return
    
    # If neither specified, set all limits for the state
    for mot in ['chx', 'chy']:
        for lim_type in ['LLM', 'HLM']:
            epics.caput(pv_map[mot][lim_type], state_limits[mot][lim_type])

def pipalign_PA2CA():
    """
    Transitions Governor from PA to CA state (Chip_Scanner config) and sets safe limits on chx and chy
    
    Requirements
    ------------
    Governor in PA state
    
    Example
    -------
    pipalign_PA2CA()
    """
    if not govStatusGet('PA', configStr='Chip_Scanner'):
        print('Not in Governor state PA, exiting')
        return -1
    
    # Set only HLM first
    pipalign_set_limits('CA', 'chx', 'HLM')
    govStateSet('CA', configStr='Chip_Scanner')
    # Set all remaining limits
    pipalign_set_limits('CA')
    return

def pipalign_CA2PA():
    """
    Transitions Governor from CA to PA state (Chip_Scanner config) and sets safe limits on chx and chy
    
    Requirements
    ------------
    * Governor in CA state
    
    Example
    -------
    pipalign_CA2PA()
    """
    if not govStatusGet('CA', configStr='Chip_Scanner'):
        print('Not in Governor state CA, exiting')
        return -1
    
    # Set only LLM first
    pipalign_set_limits('PA', 'chx', 'LLM')
    govStateSet('PA', configStr='Chip_Scanner')
    # Set all remaining limits
    pipalign_set_limits('PA')
    return


    