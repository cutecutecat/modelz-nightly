from threading import Thread
from typing import List
from nightly.client import NightlyClient
from nightly.const import (
    SUPABASE_DEV_URL,
    SUPABASE_DEV_KEY,
    SUPABASE_DEV_USER,
    SUPABASE_DEV_PASSWORD,
)
from nightly.types import MLOpsDataSum, collect_exp


data = MLOpsDataSum.restore()
client = NightlyClient()

client.auth(
    SUPABASE_DEV_URL, SUPABASE_DEV_KEY, SUPABASE_DEV_USER, SUPABASE_DEV_PASSWORD
)
templates = client.list_template()
templates_dict = client.filter_template(templates)
client.remove_all_deployments()

threads: List[Thread] = []
for name, template in templates_dict.items():
    t = Thread(
        target=collect_exp,
        kwargs={"client": client, "data": data, "name": name, "template": template},
    )
    threads.append(t)
    t.start()

for t in threads:
    t.join()

data.dump_readme()
client.remove_all_deployments()
