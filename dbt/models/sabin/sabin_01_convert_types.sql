{{ config(materialized='table') }}

WITH source_data AS (

    SELECT * FROM
    {{ source("dagster", "sabin_raw") }}

)
SELECT
    "OS" AS test_id,
    {{ normalize_text("Estado") }} AS state,
    {{ normalize_text("Municipio") }} AS location,
    TO_DATE("DataAtendimento", 'MM/DD/YYYY') AS date_testing, 
    TO_DATE("DataNascimento", 'MM/DD//YYYY') AS birth_date,  
    "Sexo" AS sex,
    "Descricao" AS exame,
    "Parametro" AS detalhe_exame,
    -- Normalize "Resultado"
    UNACCENT(UPPER(TRIM("Resultado"))) AS result,
    -- "DataAssinatura", 
    "file_name"
FROM source_data