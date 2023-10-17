import json
import os
import random
import time
from typing import Dict, List, Literal
from datetime import date, timedelta

from jinja2 import Template as Jinja2Template
from pydantic import BaseModel, TypeAdapter

from nightly.client import NightlyClient
from nightly.const import (
    HISTORY_SAVED_FILE,
    LOG_DATES_RANGE,
    README_DUMP_FILE,
    README_TEMPLATE_FILE,
    TEST_TEMPLATES,
    TIME_LIMIT,
    CaseStatus,
)


# https://img.shields.io/badge/status-15s-green
# https://img.shields.io/badge/status-failed-red
# https://img.shields.io/badge/status->600s-red
# https://img.shields.io/badge/status-unknown-yellow
class MLOpsRunOneDate(BaseModel):
    badge: Dict[str, str]

    @classmethod
    def factory_empty(cls):
        """
        generate empty experiment with unknown data
        """
        templates = sorted(
            [f"[{name}]({TEST_TEMPLATES[name]})" for name in TEST_TEMPLATES.keys()]
        )
        badges = [
            "![img](https://img.shields.io/badge/status-unknown-yellow)"
            for _ in TEST_TEMPLATES.keys()
        ]
        return cls(badge=dict(zip(templates, badges)))

    def add_exp(
        self,
        name: str,
        status: CaseStatus,
        time: int | None = None,
    ):
        label = f"[{name}]({TEST_TEMPLATES[name]})"
        if status == "ok" and time is None:
            return
        elif status == "ok":
            self.badge[
                label
            ] = f"![img](https://img.shields.io/badge/status-{time}s-green)"
        elif status == "tle":
            self.badge[
                label
            ] = f"![img](https://img.shields.io/badge/status->{TIME_LIMIT}s-red)"
        elif status == "failed":
            self.badge[
                label
            ] = f"![img](https://img.shields.io/badge/status-failed-red)"
        else:
            self.badge[
                label
            ] = f"![img](https://img.shields.io/badge/status-unknown-yellow)"


class MLOpsDataSum(BaseModel):
    cases: Dict[str, MLOpsRunOneDate]
    templates: List[str]

    @classmethod
    def factory_empty(cls):
        """
        generate empty experiment with unknown data
        """
        dates = cls._generate_dates()
        templates = sorted(
            [f"[{name}]({TEST_TEMPLATES[name]})" for name in TEST_TEMPLATES.keys()]
        )
        cases = {d: MLOpsRunOneDate.factory_empty() for d in dates}
        return cls(cases=cases, templates=templates)

    @classmethod
    def restore(cls):
        data = cls.factory_empty()
        data._update_from_history()
        return data

    def add_exp(
        self,
        name: str,
        status: Literal["ok", "failed", "tle", "unknown"],
        time: int | None = None,
    ):
        day = date.today().strftime("%Y-%m-%d")
        self.cases[day].add_exp(name, status, time)

    @staticmethod
    def _generate_dates():
        today = date.today()
        dates: List[str] = []
        for i in range(LOG_DATES_RANGE):
            day = today - timedelta(days=i)
            dates.append(day.strftime("%Y-%m-%d"))
        return dates

    def dump_readme(self):
        self._save_data()
        dates = self._generate_dates()
        case_by_date = {
            t: {d: self.cases[d].badge[t] for d in dates} for t in self.templates
        }
        with open(README_TEMPLATE_FILE, "r") as f:
            template = Jinja2Template(f.read())
        rendered = template.render(dates=dates, case_sum=case_by_date)
        with open(README_DUMP_FILE, "w") as f:
            f.write(rendered)

    def _save_data(self):
        data = self.model_dump_json(indent=4)
        with open(HISTORY_SAVED_FILE, "w") as f:
            f.write(data)

    def _update_from_history(self):
        """
        retrive from history saved files
        """
        if not os.path.isfile(HISTORY_SAVED_FILE):
            return
        with open(HISTORY_SAVED_FILE, "r") as f:
            raw = f.read()
        data_dict = json.loads(raw)
        ta = TypeAdapter(MLOpsDataSum)
        retrive = ta.validate_python(data_dict)
        # update cases from history
        for d in self._generate_dates():
            if d in retrive.cases.keys():
                self.cases[d] = retrive.cases[d]


def collect_exp(client: NightlyClient, data: MLOpsDataSum, name: str, template: str):
    deployment_id = client.create_deployment(template)
    url = client.get_deployment_url(deployment_id)
    status, consume = client.wait_till_ready(deployment_id, url)
    data.add_exp(name, status, consume)
