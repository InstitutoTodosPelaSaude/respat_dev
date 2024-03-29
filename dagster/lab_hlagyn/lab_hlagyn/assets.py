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

ROOT_PATH = pathlib.Path(__file__).parent.parent.parent.parent.absolute()
HLAGYN_FILES_FOLDER = ROOT_PATH / "data" / "hlagyn"
HLAGYN_FILES_EXTENSION = '.xlsx'

load_dotenv()
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_SCHEMA = os.getenv('DB_SCHEMA')

@asset(compute_kind="python")
def hlagyn_raw(context):
    """
    Read all excel files from data/hlagyn folder and save to db
    """
    engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

    # Choose one of the files and run the process
    hlagyn_files = [file for file in os.listdir(HLAGYN_FILES_FOLDER) if file.endswith(HLAGYN_FILES_EXTENSION)]
    assert len(hlagyn_files) > 0, f"No files found in the folder {HLAGYN_FILES_FOLDER} with extension {HLAGYN_FILES_EXTENSION}"

    # Read the file
    hlagyn_df = pd.read_excel(HLAGYN_FILES_FOLDER / hlagyn_files[0], dtype = str)
    hlagyn_df['file_name'] = hlagyn_files[0]
    context.log.info(f"Reading file {hlagyn_files[0]}")

    # The columns are not the same for all files, so we need to check the columns
    # and add the missing ones.
    common_columns = ['Idade', 'Sexo', 'Pedido', 'Data Coleta', 'Métodologia', 'Cidade', 'UF']
    result_columns = [
        # Covid Files
        'Resultado',
        # PR4 Files
        'Vírus Influenza A', 
        'Vírus Influenza B',
        'Vírus Sincicial Respiratório A/B',
        'Coronavírus SARS-CoV-2',
        # PR24 Files
        'VIRUS_IA',
        'VIRUS_H1N1',
        'VIRUS_AH3',
        'VIRUS_B',
        'VIRUS_MH',
        'VIRUS_SA',
        'VIRUS_SB',
        'VIRUS_RH',
        'VIRUS_PH',
        'VIRUS_PH2',
        'VIRUS_PH3',
        'VIRUS_PH4',
        'VIRUS_ADE',
        'VIRUS_BOC',
        'VIRUS_229E',
        'VIRUS_HKU',
        'VIRUS_NL63',
        'VIRUS_OC43',
        'VIRUS_SARS',
        'VIRUS_COV2',
        'VIRUS_EV',
        'BACTE_BP',
        'BACTE_BPAR',
        'BACTE_MP'
        ]
    
    # Check if all common columns are in the file
    for column in common_columns:
        assert column in hlagyn_df.columns, f"Column {column} not found in the file {hlagyn_files[0]}"

    # Add missing columns to the dataframe
    for column in result_columns:
        if column not in hlagyn_df.columns:
            hlagyn_df[column] = None
    
    # Save to db
    hlagyn_df.to_sql('hlagyn_raw', engine, schema=DB_SCHEMA, if_exists='replace', index=False)
    engine.dispose()

    n_rows = hlagyn_df.shape[0]
    context.add_output_metadata({'num_rows': n_rows})

    return MaterializeResult(
        metadata={
            "info": MetadataValue.md(dedent(f"""
            # HLAGyn Raw

            Last updated: {pd.Timestamp.now() - pd.Timedelta(hours=3)}

            Number of rows processed: {n_rows}
            """))
        }
    )

dagster_dbt_translator = DagsterDbtTranslator(
    settings=DagsterDbtTranslatorSettings(enable_asset_checks=True)
)

@dbt_assets(
    manifest=dbt_manifest_path,
    select='hlagyn',
    dagster_dbt_translator=dagster_dbt_translator
)
def respiratorios_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()