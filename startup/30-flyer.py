import time as ttime
from collections import deque
from ophyd.sim import NullStatus
from ophyd.status import SubscriptionStatus


class MXFlyer:
    def __init__(self, vector, zebra, eiger=None) -> None:
        self.name = 'MXFlyer'
        self.vector = vector
        self.zebra = zebra
        self.detector = eiger

        self._asset_docs_cache = deque()
        self._resource_uids = []
        self._datum_counter = None
        self._datum_ids = []

        self._collection_object = None

    def stage(self):
        ...

    def unstage(self):
        ...

    def kickoff(self):
        self.stage()
        
        # TODO: add zebra and eiger puts here...
        # TODO: or in LSDC daq_macros and daq_lib, this is already done so
        # TODO: only vector go is necessary

        self.vector.go.put(1)

        return NullStatus()

    def complete(self):
        def callback_motion(value, old_value, **kwargs):
            print(f'old: {old_value} -> new: {value}')
            if int(round(old_value)) == 1 and int(round(value)) == 0:
                return True
            else:
                return False

        motion_status = SubscriptionStatus(self.vector.active, callback_motion)
        return motion_status

    def describe_collect(self):
        return {self.name: {}}

    def collect(self):
        self.unstage()

        now = ttime.time()
        data = {}
        yield {'data': data,
               'timestamps': {key: now for key in data},
               'time': now,
               'filled': {key: False for key in data}}

    def collect_asset_docs(self):
        items = list(self._asset_docs_cache)
        self._asset_docs_cache.clear()
        for item in items:
            yield item


mx_flyer = MXFlyer(vector=vector, zebra=zebra, eiger=eiger_single)