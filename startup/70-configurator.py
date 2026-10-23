"""Named YAML settings presets for Bluesky/ophyd-async devices.

Loaded by the beamline's IPython startup machinery. Hardware is not
connected or changed at import time. See configurator/README.md.
"""

from pathlib import Path
import re

import bluesky.plan_stubs as bps
from ophyd_async.core import Device, YamlSettingsProvider
from ophyd_async.epics.core import epics_signal_rw
from ophyd_async.plan_stubs import (
    ensure_connected,
    retrieve_settings,
    store_settings,
    apply_settings,
    apply_settings_if_different,
)

CONFIGURATOR_ROOT = Path('/epics/iocs/notebook/notebooks/configurator')
_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]*$')
_CAMERA_FIELDS = ('bin_x', 'bin_y', 'size_x', 'size_y', 'min_x', 'min_y', 'acquire_time')


class CameraSettings(Device):
    """Configuration-only view of a Prosilica areaDetector camera."""

    def __init__(self, prefix, name=''):
        p = f'ca://{prefix}cam1:'
        for field, suffix, dtype in (
            ('bin_x', 'BinX', int), ('bin_y', 'BinY', int),
            ('size_x', 'SizeX', int), ('size_y', 'SizeY', int),
            ('min_x', 'MinX', int), ('min_y', 'MinY', int),
            ('acquire_time', 'AcquireTime', float),
        ):
            setattr(self, field, epics_signal_rw(dtype, p + suffix + '_RBV', p + suffix))
        super().__init__(name=name)


def _read_saved_yaml(path):
    """Read only simple native settings YAML (do not create an alternative format)."""
    import yaml
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f'Expected mapping in {path}')
    return data


class Configurator:
    def __init__(self, root=CONFIGURATOR_ROOT, run_engine=None):
        self.root = Path(root)
        self._devices = {}
        self._RE = run_engine

    @staticmethod
    def _name(value):
        if not isinstance(value, str) or not _NAME.fullmatch(value):
            raise ValueError(f'Invalid name {value!r}; use letters, digits, _ or -')
        return value

    def help(self):
        """Show concise notebook usage examples for save, list, show and restore.

        Usage:
            configurator.help()

        Saving is a Bluesky plan (run with RE); interactive restoration
        calls RE internally. See configurator/README.md for details.
        """
        devices = '\n'.join(f'  {name}' for name in sorted(self._devices)) or '  (none)'
        print(f"""Bluesky Configurator
====================

Save current device settings (Bluesky plan):
  RE(configurator.save('routine_operations', 'cam_8', 'default'))

List available configurations:
  configurator.list()
  configurator.list('routine_operations')
  configurator.list('routine_operations', 'cam_8')

Show a saved configuration:
  configurator.show('routine_operations', 'cam_8', 'default')

Restore a saved configuration (interactive, calls RE internally):
  configurator.restore('routine_operations', 'cam_8', 'default')

Registered devices:
{devices}

Configuration directory:
  {self.root}
""")

    def register(self, name, device, *, restore_plan=None, acquire_signal=None):
        name = self._name(name)
        if name in self._devices:
            raise ValueError(f'Already registered: {name}')
        self._devices[name] = (device, restore_plan, acquire_signal)

    def _resolve(self, use_case, device_name, preset):
        keys = tuple(map(self._name, (use_case, device_name, preset)))
        if device_name not in self._devices:
            raise KeyError(f'Unregistered device: {device_name}')
        folder = self.root / keys[0] / keys[1]
        return folder, folder / f'{keys[2]}.yaml', self._devices[device_name]

    def list(self, use_case=None, device=None):
        """List cases, devices, or presets; return the names."""
        if device is not None and use_case is None:
            raise ValueError('Supply use_case when supplying device')
        if use_case is None:
            folder, pattern, dirs = self.root, '*', True
        elif device is None:
            folder, pattern, dirs = self.root / self._name(use_case), '*', True
        else:
            folder = self.root / self._name(use_case) / self._name(device)
            pattern, dirs = '*.yaml', False
        paths = folder.glob(pattern) if folder.is_dir() else ()
        if dirs:
            names = sorted(p.name for p in paths if p.is_dir())
        else:
            names = sorted(p.stem for p in paths if p.is_file())
        for name in names:
            print(name)
        return names

    def show(self, use_case, device, preset):
        """Show YAML values without accessing EPICS."""
        _, path, _ = self._resolve(use_case, device, preset)
        data = _read_saved_yaml(path)
        print(path)
        for key, value in data.items():
            print(f'  {key}: {value}')
        return data

    def save(self, use_case, device, preset, *, overwrite=False):
        """Bluesky plan: save the currently connected device's settings."""
        folder, path, (obj, _, _) = self._resolve(use_case, device, preset)
        if path.exists() and not overwrite:
            raise FileExistsError(f'Preset exists: {path} (set overwrite=True explicitly)')
        folder.mkdir(parents=True, exist_ok=True)
        yield from ensure_connected(obj, timeout=10)
        # Pre-existing name is checked again just before the operation.
        if path.exists() and not overwrite:
            raise FileExistsError(f'Preset exists: {path}')
        yield from store_settings(YamlSettingsProvider(folder), preset, obj)
        print(f'Saved {path}')

    def restore(self, use_case, device, preset):
        """Interactive notebook helper: prompt *outside* the RunEngine."""
        if self._RE is None:
            raise RuntimeError('Configurator has no RunEngine; assign configurator._RE = RE')
        if self._RE.state != 'idle':
            raise RuntimeError('RunEngine must be idle before restoration')
        folder, path, (obj, restore_plan, acquire_signal) = self._resolve(
            use_case, device, preset
        )
        data = _read_saved_yaml(path)
        # Validate keys and numeric values BEFORE prompting or altering hardware.
        if restore_plan is _restore_prosilica:
            _validate_camera_preset(data)
        stopped_by_us = False
        if restore_plan is _restore_prosilica and acquire_signal is None:
            raise RuntimeError('Camera acquisition signal unavailable: cannot safely restore')
        if acquire_signal is not None:
            acquiring = bool(acquire_signal.get(timeout=5))
            if acquiring:
                print(f'Camera {device} is acquiring.')
                print('[Y] Stop acquisition and restore')
                print('[N] Restore while acquiring (frames/plugins may be affected)')
                print('[C] Cancel (default)')
                choice = input('Choice [C]: ').strip().upper() or 'C'
                if choice == 'C':
                    print('Cancelled: no hardware changes made.')
                    return
                if choice not in ('Y', 'N'):
                    print('Cancelled: invalid choice; no hardware changes made.')
                    return
                if choice == 'Y':
                    acquire_signal.set(0).wait(timeout=10)
                    if bool(acquire_signal.get(timeout=5)):
                        raise RuntimeError('Acquisition did not stop; restoration aborted')
                    stopped_by_us = True
                else:
                    print('WARNING: proceeding during image acquisition.')
        if stopped_by_us:
            print('Acquisition stopped; it will NOT be restarted automatically.')
        self._RE(self._restore_plan(folder, preset, obj, restore_plan))

    @staticmethod
    def _restore_plan(folder, preset, obj, restore_plan):
        yield from ensure_connected(obj, timeout=10)
        saved = yield from retrieve_settings(YamlSettingsProvider(folder), preset, obj)
        if restore_plan is None:
            yield from apply_settings_if_different(saved, apply_plan=apply_settings)
        else:
            yield from restore_plan(obj, saved)
        for signal, expected in saved.items():
            actual = yield from bps.rd(signal)
            tolerance = 1e-6 if isinstance(expected, float) else 0
            if expected is None or not isinstance(actual, (float, int)):
                equal = actual == expected
            else:
                equal = abs(actual - expected) <= tolerance
            if not equal:
                raise RuntimeError(
                    f'Restore incomplete: {signal.name}: expected {expected}, got {actual}'
                )
        print(f'Restored and verified: {obj.name}/{preset}')


def _validate_camera_preset(data):
    if set(data) != set(_CAMERA_FIELDS):
        raise ValueError(f'Camera preset must contain exactly: {_CAMERA_FIELDS}')
    for name in _CAMERA_FIELDS:
        value = data[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f'{name} must be numeric')
        if name != 'acquire_time' and (not isinstance(value, int) or value < 0):
            raise ValueError(f'{name} must be a nonnegative integer')
        if name == 'acquire_time' and not (0 < value < float('inf')):
            raise ValueError('acquire_time must be finite and positive')
    if data['bin_x'] < 1 or data['bin_y'] < 1 or data['size_x'] < 1 or data['size_y'] < 1:
        raise ValueError('Binning and ROI sizes must be positive')


def _restore_prosilica(dev, saved):
    """Restore camera settings in an ordered sequence.

    Let the EPICS IOC enforce the camera's supported binning and ROI limits.
    Intermediate readbacks may be adjusted by the IOC; the caller verifies
    all final settings against the saved preset and reports any mismatch.
    """
    # The 1200 x 1000 intermediate ROI worked in the initial FS4 test,
    # but it is a transition aid, not an allowed-geometry restriction.
    for signal, value in (
        (dev.size_x, 1200), (dev.size_y, 1000),
        (dev.min_x, 0), (dev.min_y, 0),
        (dev.bin_x, saved[dev.bin_x]), (dev.bin_y, saved[dev.bin_y]),
        (dev.min_x, saved[dev.min_x]), (dev.min_y, saved[dev.min_y]),
        (dev.size_x, saved[dev.size_x]), (dev.size_y, saved[dev.size_y]),
        (dev.acquire_time, saved[dev.acquire_time]),
    ):
        yield from bps.mv(signal, value)


# A startup profile can provide RE in the shared IPython namespace.
# Register the two requested Prosilica cameras; connection remains lazy.
configurator = Configurator(run_engine=globals().get('RE'))
configurator.register(
    'cam_fs4',
    CameraSettings('XF:17IDC-BI:FMX{FS:4-Cam:1}', name='cam_fs4_settings_full'),
    restore_plan=_restore_prosilica,
    acquire_signal=globals().get('cam_fs4').cam.acquire if globals().get('cam_fs4') is not None else None,
)

# Cam 8 uses the same Prosilica cam1: suffix, with a different IOC prefix.
# No cam_8 preset is supplied: save its actual operational state first.
configurator.register(
    'cam_8',
    CameraSettings('XF:17IDC-ES:FMX{Cam:8}', name='cam_8_settings_full'),
    restore_plan=_restore_prosilica,
    acquire_signal=globals().get('cam_8').cam.acquire if globals().get('cam_8') is not None else None,
)