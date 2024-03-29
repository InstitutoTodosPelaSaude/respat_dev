from dagster import (
    AssetExecutionContext,
    asset,
    MaterializeResult, 
    MetadataValue
)
from dagster_dbt import (
    DbtCliResource, 
    dbt_assets,
    DagsterDbtTranslator,
    DagsterDbtTranslatorSettings
)
from textwrap import dedent
import pandas as pd
import os
import pathlib
from sqlalchemy import create_engine
from dotenv import load_dotenv

from .constants import dbt_manifest_path

dagster_dbt_translator = DagsterDbtTranslator(
    settings=DagsterDbtTranslatorSettings(enable_asset_checks=True)
)

ROOT_PATH = pathlib.Path(__file__).parent.parent.parent.parent.absolute()
HISTORICAL_COMBINED_FILE_FOLDER = ROOT_PATH / "data" / "historical_data"
HISTORICAL_COMBINED_FILE_EXTENSION = '.tsv'

load_dotenv()
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_SCHEMA = os.getenv('DB_SCHEMA')

@asset(compute_kind="python")
def combined_historical_raw(context):
    """
    Import the combined historical data to the database
    """
    
    engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

    # Choose one of the files and run the process
    combined_files = [file for file in os.listdir(HISTORICAL_COMBINED_FILE_FOLDER) if file.endswith(HISTORICAL_COMBINED_FILE_EXTENSION)]
    assert len(combined_files) > 0, f"No files found in the folder {HISTORICAL_COMBINED_FILE_FOLDER} with extension {HISTORICAL_COMBINED_FILE_EXTENSION}"

    combined_file = combined_files[0]
    combined_df = pd.read_csv(HISTORICAL_COMBINED_FILE_FOLDER / combined_file, sep='\t', dtype=str)

    # Save to db
    combined_df.to_sql('combined_historical_raw', engine, schema=DB_SCHEMA, if_exists='replace', index=False)
    engine.dispose()

    n_rows = combined_df.shape[0]
    context.add_output_metadata({'num_rows': n_rows})

    return MaterializeResult(
        metadata={
            "info": MetadataValue.md(dedent(f"""
            # Import Combined Historical Data

            Last updated: {pd.Timestamp.now() - pd.Timedelta(hours=3)}

            Number of rows processed: {n_rows}
            """))
        }
    )

@dbt_assets(
    manifest=dbt_manifest_path,
    select='combined +epiweeks +municipios +age_groups +fix_location +macroregions',
    dagster_dbt_translator=dagster_dbt_translator
)
def respiratorios_combined_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()

@dbt_assets(
    manifest=dbt_manifest_path,
    select='combined_historical',
    dagster_dbt_translator=dagster_dbt_translator
)
def respiratorios_historical_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()