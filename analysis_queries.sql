USE weather_traffic_db;

-- Check table exists
SHOW TABLES;

-- Check row count
SELECT COUNT(*) AS total_rows
FROM weather_traffic_data;

-- Preview data
SELECT *
FROM weather_traffic_data
LIMIT 10;

-- Average traffic index by borough
SELECT 
    borough,
    ROUND(AVG(traffic_index_capped), 4) AS avg_traffic_index,
    ROUND(AVG(rain), 4) AS avg_rain,
    ROUND(AVG(temperature_2m), 4) AS avg_temp
FROM weather_traffic_data
GROUP BY borough
ORDER BY avg_traffic_index DESC;

-- Hourly traffic pattern
SELECT
    hour,
    ROUND(AVG(traffic_index_capped), 4) AS avg_traffic_index,
    ROUND(AVG(rain), 4) AS avg_rain
FROM weather_traffic_data
GROUP BY hour
ORDER BY hour;

-- Rainy hours vs dry hours
SELECT
    CASE 
        WHEN rain > 0 THEN 'Rainy'
        ELSE 'Dry'
    END AS weather_condition,
    ROUND(AVG(traffic_index_capped), 4) AS avg_traffic_index,
    COUNT(*) AS total_rows
FROM weather_traffic_data
GROUP BY weather_condition;

-- Freezing temperature impact
SELECT
    CASE 
        WHEN temperature_2m < 0 THEN 'Freezing'
        ELSE 'Normal'
    END AS temp_condition,
    ROUND(AVG(traffic_index_capped), 4) AS avg_traffic_index,
    COUNT(*) AS total_rows
FROM weather_traffic_data
GROUP BY temp_condition;

-- Peak hours only: 7-9 AM and 5-7 PM
SELECT
    borough,
    hour,
    ROUND(AVG(traffic_index_capped), 4) AS avg_traffic_index,
    ROUND(AVG(rain), 4) AS avg_rain
FROM weather_traffic_data
WHERE hour IN (7, 8, 9, 17, 18, 19)
GROUP BY borough, hour
ORDER BY borough, hour;

-- Snowfall impact
SELECT
    CASE 
        WHEN snowfall = 0 THEN 'No Snow'
        WHEN snowfall < 5 THEN 'Light Snow'
        ELSE 'Heavy Snow'
    END AS snow_condition,
    ROUND(AVG(traffic_index_capped), 4) AS avg_traffic_index,
    COUNT(*) AS total_rows
FROM weather_traffic_data
GROUP BY snow_condition;

-- Most congested streets
SELECT
    borough,
    street,
    direction,
    ROUND(AVG(traffic_index_capped), 4) AS avg_traffic_index,
    COUNT(*) AS total_rows
FROM weather_traffic_data
GROUP BY borough, street, direction
HAVING COUNT(*) >= 10
ORDER BY avg_traffic_index DESC
LIMIT 20;

-- Rain impact by borough
SELECT
    borough,
    CASE 
        WHEN rain > 0 THEN 'Rainy'
        ELSE 'Dry'
    END AS weather_condition,
    ROUND(AVG(traffic_index_capped), 4) AS avg_traffic_index,
    COUNT(*) AS total_rows
FROM weather_traffic_data
GROUP BY borough, weather_condition
ORDER BY borough, weather_condition;

-- Date range check
SELECT
    MIN(date) AS start_date,
    MAX(date) AS end_date
FROM weather_traffic_data;