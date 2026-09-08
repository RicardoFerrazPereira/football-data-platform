DESCRIBE player_statistics;
DESCRIBE players;
select * from player_statistics;

-- TESTAR REGISTROS:

SELECT COUNT(*) FROM vw_vasco_player_match_statistics;

-- Verificar uma partida que já validamos - match_id = 16253383
SELECT
	match_id,
	match_date,
	player_id,
	player_name,
	minutes_played,
	goals,
	assists,
	expected_goals,
	expected_assists,
	rating
FROM
	vw_vasco_player_match_statistics
WHERE
	match_id = 16253383
ORDER BY
	rating DESC;

-- PRIMEIRO TESTE ANALÍTICO

SELECT
	player_name,
	SUM(COALESCE(goals, 0)) AS goals,
	SUM(COALESCE(assists, 0)) AS assists,
	SUM(COALESCE(expected_goals, 0)) AS expected_goals,
	SUM(COALESCE(expected_assists, 0)) AS expected_assists,
	SUM(COALESCE(minutes_played, 0)) AS minutes_played,
	ROUND(
        AVG(rating),
        2
    ) AS avg_rating
FROM
	vw_vasco_player_match_statistics
WHERE
	EXTRACT(YEAR FROM match_date) = 2026
GROUP BY
	player_id,
	player_name
ORDER BY
	goals DESC;

-- VALIDAÇÃO AGREGADA

SELECT
	player_name,
	SUM(COALESCE(goals, 0)) AS goals,
	SUM(COALESCE(assists, 0)) AS assists,
	SUM(COALESCE(minutes_played, 0)) AS minutes_played,
	ROUND(
        SUM(COALESCE(expected_goals, 0)),
        2
    ) AS expected_goals,
	ROUND(
        SUM(COALESCE(expected_assists, 0)),
        2
    ) AS expected_assists,
	ROUND(
        AVG(rating),
        2
    ) AS avg_rating
FROM
	vw_vasco_player_match_statistics
WHERE
	EXTRACT(YEAR FROM match_date) = 2026
GROUP BY
	player_id,
	player_name
ORDER BY
	goals DESC,
	assists DESC,
	avg_rating DESC;

