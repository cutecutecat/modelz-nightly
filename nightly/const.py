from os import environ
from os.path import join, dirname
from typing import Dict, Literal

Endpoint = str
DeploymenStatus = Literal["NoReplicas", "NotReady", "Scaling", "Ready"]
CaseStatus = Literal["ok", "failed", "tle", "unknown"]

SUPABASE_DEV_URL: str = environ.get("SUPABASE_DEV_URL")
SUPABASE_DEV_KEY: str = environ.get("SUPABASE_DEV_KEY")
SUPABASE_DEV_USER: str = environ.get("SUPABASE_DEV_USER")
SUPABASE_DEV_PASSWORD: str = environ.get("SUPABASE_DEV_PASSWORD")
MODELZ_CLUSTER_ID: str = environ.get("MODELZ_CLUSTER_ID")
MODELZ_BASIC_URL: str = environ.get("MODELZ_BASIC_URL")

TIME_LIMIT = 600
TRY_INTERVAL = 1
LOG_DATES_RANGE = 5

HISTORY_SAVED_FILE = join(dirname(dirname(__file__)), "data", "result.json")
README_TEMPLATE_FILE = join(dirname(__file__), "README.jinja")
README_DUMP_FILE = join(dirname(dirname(__file__)), "README.md")


TEST_TEMPLATES: Dict[str, str] = {
    "Stable Diffusion": "https://docs.modelz.ai/frameworks/mosec/stable-diffusion",
    "ImageBind": "https://docs.modelz.ai/frameworks/mosec/imagebind",
    "Whisper": "https://docs.modelz.ai/frameworks/mosec/whisper",
}
