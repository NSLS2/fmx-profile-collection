logger = logging.getLogger(__name__)
logging.basicConfig(filename='/nsls2/data/fmx/shared/config/bluesky/logs/startup_log.log', level=logging.INFO)
import nslsii
import redis
from redis_json_dict import RedisJSONDict

uri = "info.fmx.nsls2.bnl.gov"
# # Provide an endstation prefix, if needed, with a trailing "-"
new_md = RedisJSONDict(redis.Redis(uri), prefix="")
BEAMLINE_ID = 'fmx'
## 20250107 Test startup issues
try:
    nslsii.configure_base(get_ipython().user_ns, BEAMLINE_ID, pbar=False,
                          publish_documents_with_kafka=True) # Progress bar for scans
    #nslsii.configure_base(get_ipython().user_ns, BEAMLINE_ID)
except:
    logging.exception('Got exception on main handler')
    raise
    # nslsii.configure_base(get_ipython().user_ns, BEAMLINE_ID, pbar=False,
#                       publish_documents_with_kafka=True) # Progress bar for scans

# Disable plots via BestEffortCallback:
bec.disable_plots()

# Metadata storage
RE.md = new_md

