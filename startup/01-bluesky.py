import nslsii
import redis
from redis_json_dict import RedisJSONDict
#
uri = "info.fmx.nsls2.bnl.gov"
# # Provide an endstation prefix, if needed, with a trailing "-"
new_md = RedisJSONDict(redis.Redis(uri), prefix="")

BEAMLINE_ID = 'fmx'

## 20250107 Test startup issues
# nslsii.configure_base(get_ipython().user_ns, BEAMLINE_ID)
nslsii.configure_base(get_ipython().user_ns, BEAMLINE_ID, pbar=False,
                      publish_documents_with_kafka=True) # Progress bar for scans

# Disable plots via BestEffortCallback:
bec.disable_plots()

RE.md = new_md

#from pathlib import Path

#import appdirs

#from bluesky.utils import PersistentDict

# runengine_metadata_dir = appdirs.user_data_dir(appname="bluesky") / Path("runengine-metadata")
#runengine_metadata_dir = Path(f"/nsls2/data/{BEAMLINE_ID}/shared/config/{BEAMLINE_ID}_bluesky_config/")

# PersistentDict will create the directory if it does not exist
#RE.md = PersistentDict(runengine_metadata_dir)

