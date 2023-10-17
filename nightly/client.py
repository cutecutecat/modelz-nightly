import os
import time
from typing import Dict, List, Tuple, cast
from threading import Thread

from supabase import create_client, Client as SupabaseClient
from supabase.lib.client_options import ClientOptions

from modelz import DeploymentClient, ModelzClient
from modelz.openapi.sdk.types import UNSET
from modelz.openapi.sdk.models import (
    Template,
    DeploymentCreateRequest,
    DeploymentSpec,
    Deployment,
)
from modelz.openapi.sdk.api.api_key import get_users_login_name_api_keys
from modelz.openapi.sdk.api.template import get_public_templates
from modelz.openapi.sdk.client import AuthenticatedClient


from nightly.const import (
    MODELZ_BASIC_URL,
    TEST_TEMPLATES,
    TIME_LIMIT,
    TRY_INTERVAL,
    CaseStatus,
)

os.environ["MODELZ_DISABLE_RICH"] = "true"


class NightlyClient:
    def __init__(self):
        # Fetch through auth()
        self.user_id: str = ""
        self.access_token: str = ""
        self.api_key: str = ""

        # low-level OpenAPI client for unwrapper methods
        self.client: AuthenticatedClient
        # high-level deployment client
        self.deploy_client: DeploymentClient

    def auth(
        self, peoject_url: str, anoy_key: str, user_email: str, user_password: str
    ) -> Tuple[str, str]:
        # supabase email login to get JWT token and user ID
        options = ClientOptions(persist_session=False, auto_refresh_token=False)
        supabase_client: SupabaseClient = create_client(peoject_url, anoy_key, options)

        resp = supabase_client.auth.sign_in_with_password(
            {"email": user_email, "password": user_password}
        )
        self.user_id = resp.user.id
        self.access_token = resp.session.access_token
        self.client = AuthenticatedClient(
            base_url=MODELZ_BASIC_URL, token=self.access_token
        )

        # Get API Key from ModelZ
        resp = get_users_login_name_api_keys.sync_detailed(
            login_name=self.user_id, client=self.client
        )
        if resp.parsed is None:
            raise RuntimeError("empty API Key")
        self.api_key = resp.parsed.key

        self.deploy_client = DeploymentClient(
            login_name=self.user_id,
            key=self.api_key,
            host=MODELZ_BASIC_URL,
        )

    def list_template(self) -> List[Template]:
        resp = get_public_templates.sync_detailed(client=self.client)
        if resp.parsed is None:
            raise RuntimeError("empty public templates")
        return resp.parsed

    @staticmethod
    def filter_template(templates: List[Template]) -> Dict[str, Template]:
        exist_templates = {t.name: t for t in templates}
        for name in TEST_TEMPLATES.keys():
            if name not in exist_templates:
                raise RuntimeError
        return {name: exist_templates[name] for name in TEST_TEMPLATES.keys()}

    def get_deployment_url(self, deployment_id: str) -> str:
        endpoint = UNSET
        while endpoint == UNSET:
            resp = self.deploy_client.get(deployment_id)
            # fallback for no deployments
            if resp.parsed is None:
                raise RuntimeError
            endpoint = resp.parsed.status.endpoint
            time.sleep(1)
        return endpoint

    def create_deployment(self, t: Template) -> str:
        req = DeploymentCreateRequest(
            spec=DeploymentSpec(
                name=t.suggest_name,
                deployment_source=t.deployment_source,
                server_resource=t.server_source,
                framework=t.framework,
                min_replicas=0,
                max_replicas=1,
                target_load=10,
                startup_duration=300,
                port=t.port,
                command=t.command,
                http_probe_path=t.http_probe_path,
            )
        )
        resp = self.deploy_client.create(req)
        return resp.parsed.spec.id

    def wait_till_ready(
        self, deployment_id: str, url: str
    ) -> Tuple[CaseStatus, int | None]:
        client = ModelzClient(key=self.api_key, endpoint=url)
        # send request to deployment
        time.sleep(10)
        Thread(target=client.inference, kwargs={"params": ""}).start()

        status = "NotReady"
        for i in range(TIME_LIMIT // TRY_INTERVAL):
            resp = self.deploy_client.get(deployment_id)
            if resp.parsed is None:
                raise RuntimeError
            status = resp.parsed.status.phase

            if status == "Ready":
                return "ok", i * TRY_INTERVAL
            if status == "NotReady" or status == "NoReplicas":
                time.sleep(TRY_INTERVAL)
                continue
            else:
                return "failed", None
        return "tle", None

    def remove_all_deployments(self):
        resp = self.deploy_client.list()
        if resp.parsed.deployments == UNSET:
            return
        for d in cast(List[Deployment], resp.parsed.deployments):
            self.deploy_client.delete(d.spec.id)
