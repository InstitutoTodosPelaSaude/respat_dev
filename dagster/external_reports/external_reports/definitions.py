import os

from dagster import Definitions
from dagster_dbt import DbtCliResource

from .assets import respiratorios_dbt_assets, external_report_rio_export_to_tsv, external_report_rio_send_email
from .constants import dbt_project_dir
from .schedules import schedules

defs = Definitions(
    assets=[respiratorios_dbt_assets, external_report_rio_export_to_tsv, external_report_rio_send_email],
    schedules=schedules,
    resources={
        "dbt": DbtCliResource(project_dir=os.fspath(dbt_project_dir)),
    },
)