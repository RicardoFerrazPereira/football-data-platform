-- TESTES vw_vasco_team_period_statistics

-- TESTE ESTRUTURAL

SELECT
    period,
    COUNT(*) AS total_partidas
FROM vw_vasco_team_period_statistics
GROUP BY period
ORDER BY period;

-- PARTIDAS QUE JÁ VALIDAMOS

SELECT
    match_id,
    period,
    opponent_team_name,
    venue,
    vasco_ball_possession,
    opponent_ball_possession,
    vasco_expected_goals,
    opponent_expected_goals,
    vasco_total_shots,
    opponent_total_shots,
    vasco_shots_on_target,
    opponent_shots_on_target,
    vasco_corner_kicks,
    opponent_corner_kicks
FROM vw_vasco_team_period_statistics
WHERE match_id = 16253383
ORDER BY
    CASE
        WHEN period = '1ST' THEN 1
        WHEN period = '2ND' THEN 2
    END;
