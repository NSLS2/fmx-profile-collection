from ophyd import (AreaDetector, EpicsSignal, EpicsSignalRO, 
                   DeviceStatus) 
from ophyd.areadetector.base import ADComponent, EpicsSignalWithRBV


class EigerBase(AreaDetector):    
    
    armed = ADComponent(EpicsSignalRO, 'cam1:Armed')    
    sequence_id = ADComponent(EpicsSignalRO, 'cam1:SequenceId')
    num_triggers = ADComponent(EpicsSignalWithRBV, 'cam1:NumTriggers')
    threshold_energy = ADComponent(EpicsSignalWithRBV, 'cam1:ThresholdEnergy')
    photon_energy = ADComponent(EpicsSignalWithRBV, 'cam1:PhotonEnergy')
    fw_file_path = ADComponent(EpicsSignalWithRBV, 'cam1:FilePath', string=True)
    fw_name_pattern = ADComponent(EpicsSignalWithRBV, 'cam1:FWNamePattern', string=True)
    fw_nimages_per_file = ADComponent(EpicsSignalWithRBV, 'cam1:FWNImagesPerFile')
    fw_enable = ADComponent(EpicsSignalWithRBV, 'cam1:FWEnable')
    fw_auto_remove = ADComponent(EpicsSignalWithRBV, 'cam1:FWAutoRemove')
    save_files = ADComponent(EpicsSignalWithRBV, 'cam1:SaveFiles')
    manual_trigger = ADComponent(EpicsSignalWithRBV, 'cam1:ManualTrigger')
    roi_mode = ADComponent(EpicsSignalWithRBV, 'cam1:ROIMode')
    flatfield_applied = ADComponent(EpicsSignalWithRBV, 'cam1:FlatfieldApplied')
    compression_algo = ADComponent(EpicsSignalWithRBV, 'cam1:CompressionAlgo')
    dead_time = ADComponent(EpicsSignalRO, 'cam1:DeadTime_RBV')
    
    # Metadata
    beam_center_x = ADComponent(EpicsSignalWithRBV, 'cam1:BeamX')
    beam_center_y = ADComponent(EpicsSignalWithRBV, 'cam1:BeamY')
    wavelength = ADComponent(EpicsSignalWithRBV, 'cam1:Wavelength')
    det_distance = ADComponent(EpicsSignalWithRBV, 'cam1:DetDist')
    
    # MX Metadata
    chi_start = ADComponent(EpicsSignalWithRBV, 'cam1:ChiStart')
    chi_incr = ADComponent(EpicsSignalWithRBV, 'cam1:ChiIncr')
    kappa_start = ADComponent(EpicsSignalWithRBV, 'cam1:KappaStart')
    kappa_incr = ADComponent(EpicsSignalWithRBV, 'cam1:KappaIncr')
    omega_start = ADComponent(EpicsSignalWithRBV, 'cam1:OmegaStart')
    omega_incr = ADComponent(EpicsSignalWithRBV, 'cam1:OmegaIncr')
    phi_start = ADComponent(EpicsSignalWithRBV, 'cam1:PhiStart')
    phi_incr = ADComponent(EpicsSignalWithRBV, 'cam1:PhiIncr')
    two_theta_start = ADComponent(EpicsSignalWithRBV, 'cam1:TwoThetaStart')
    two_theta_incr = ADComponent(EpicsSignalWithRBV, 'cam1:TwoThetaIncr')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.configuration_attrs = ['cam', 'threshold_energy', 'photon_energy', 
                                    'beam_center_x', 'beam_center_y', 'wavelength', 'det_distance', 
                                    'flatfield_applied', 'compression_algo'
                                    'chi_start', 'chi_incr', 'kappa_start', 'kappa_incr', 
                                    'omega_start', 'omega_incr', 'phi_start', 'phi_incr', 
                                    'two_theta_start', 'two_theta_incr', 'num_triggers']
        self.cam.configuration_attrs = ['acquire_time', 'acquire_period']
    
class Eiger(EigerBase, Device):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._fs_resource = None
        self._armed_status = None
        self._done_status = None
        self._waiting_arm = False
        
        self.stage_sigs.update({
            self.cam.trigger_mode: 3, # 'External Enable'
            self.fw_enable: 1, 
            self.fw_auto_remove: 1,
            self.save_files: 1,
            self.manual_trigger: 0,
        })
        
    def kickoff(self):
        print(self.name, "kickoff")
        self._armed_status = DeviceStatus(self)
        self._done_status = DeviceStatus(self)
        self._waiting_arm = True
        self.armed.subscribe(self._armed_changed, run=False)
        self.cam.acquire.subscribe(self._acquire_changed, run=False)
        #yield from abs_set(eiger.cam.acquire, 1)
        eiger.cam.acquire.put(1) # abs_set doesn't work, can't import mv
        return self._armed_status
    
    def complete(self):
        print(self.name, "complete")
        return self._done_status
    
    def _armed_changed(self, value=None, old_value=None, obj=None, *args, **kwargs):
        if old_value == 0 and value == 1 and self._armed_status is not None:
            print(self.name, "armed")
            self._waiting_arm = False
            obj.clear_sub(self._armed_changed)
            self._armed_status._finished()
            self._armed_status = None
            
    def _acquire_changed(self, value=None, old_value=None, obj=None, *args, **kwargs):
        if old_value == 1 and value == 0:
            print(self.name, "done acquiring")
            if self._waiting_arm and self._armed_status is not None:
                self._waiting_arm = False
                self.armed.clear_sub(self._armed_changed)
                obj.clear_sub(self._acquire_changed)
                self._armed_status._finished(success=False)
                self._armed_status = None
                
            elif self._done_status is not None:
                obj.clear_sub(self._acquire_changed)
                self._done_status._finished()
                self._done_status = None
        
eiger = Eiger('XF:17IDC-ES:FMX{Det:Eig16M}', name='eiger')

