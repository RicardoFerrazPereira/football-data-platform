DESCRIBE statistics;
SELECT * FROM statistics LIMIT 20;

SELECT DISTINCT period FROM statistics ORDER BY period;


-- Retornar todos os atributos de estatísticas coletivas que o dataset realmente possui.
SELECT DISTINCT
    group_name,
    statistic_name
FROM statistics
WHERE period = 'ALL'
ORDER BY
    group_name,
    statistic_name;

-- PRIMEIRO TESTE

-- partida que já usamos para validar anteriormente:

SELECT COUNT(*)
FROM vw_vasco_team_statistics;

SELECT *
FROM vw_vasco_team_statistics
WHERE match_id = 16253383;

-- Trazer apenas as métricas principais

SELECT
	match_id,
	match_date,
	opponent_team_name,
	venue,
	vasco_ball_possession,
	opponent_ball_possession,
	vasco_expected_goals,
	opponent_expected_goals,
	vasco_big_chances,
	opponent_big_chances,
	vasco_total_shots,
	opponent_total_shots,
	vasco_shots_on_target,
	opponent_shots_on_target,
	vasco_corner_kicks,
	opponent_corner_kicks,
	vasco_fouls,
	opponent_fouls,
	vasco_yellow_cards,
	opponent_yellow_cards
FROM
	vw_vasco_team_statistics
WHERE
	match_id = 16253383;