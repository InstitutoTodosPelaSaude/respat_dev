{{ config(materialized='table') }}

WITH source_data AS(
    SELECT
    *
    FROM {{ ref("combined_05_location") }}
)
SELECT
    *
FROM source_data