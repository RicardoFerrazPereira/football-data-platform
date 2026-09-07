-- CRIAR A VIEW -> vw_vasco_team_period_statistics

CREATE OR REPLACE
VIEW vw_vasco_team_period_statistics AS
WITH vasco_matches AS (
SELECT
	match_id,
	match_date,
	tournament_id,
	tournament_name,
	season_id,
	season_name,
	CASE
		WHEN home_team_id = 1974 THEN 'HOME'
		WHEN away_team_id = 1974 THEN 'AWAY'
	END AS venue,
	CASE
		WHEN home_team_id = 1974 THEN away_team_id
		WHEN away_team_id = 1974 THEN home_team_id
	END AS opponent_team_id,
	CASE
		WHEN home_team_id = 1974 THEN away_team_name
		WHEN away_team_id = 1974 THEN home_team_name
	END AS opponent_team_name,
	CASE
		WHEN home_team_id = 1974 THEN 'home'
		WHEN away_team_id = 1974 THEN 'away'
	END AS vasco_side
FROM
	matches
WHERE
	home_team_id = 1974
	OR away_team_id = 1974
),
statistics_pivot AS (
SELECT
	s.match_id,
	s.period,
	-- =====================================
	-- MATCH OVERVIEW
	-- =====================================
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Ball possession'
                THEN s.value_numeric
            END
        ) AS vasco_ball_possession,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Ball possession'
                THEN s.value_numeric
            END
        ) AS opponent_ball_possession,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.group_name = 'Match overview'
                 AND s.statistic_name = 'Expected goals'
                THEN s.value_numeric
            END
        ) AS vasco_expected_goals,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.group_name = 'Match overview'
                 AND s.statistic_name = 'Expected goals'
                THEN s.value_numeric
            END
        ) AS opponent_expected_goals,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Big chances'
                THEN s.value_numeric
            END
        ) AS vasco_big_chances,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Big chances'
                THEN s.value_numeric
            END
        ) AS opponent_big_chances,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Corner kicks'
                THEN s.value_numeric
            END
        ) AS vasco_corner_kicks,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Corner kicks'
                THEN s.value_numeric
            END
        ) AS opponent_corner_kicks,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.group_name = 'Match overview'
                 AND s.statistic_name = 'Total shots'
                THEN s.value_numeric
            END
        ) AS vasco_total_shots,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.group_name = 'Match overview'
                 AND s.statistic_name = 'Total shots'
                THEN s.value_numeric
            END
        ) AS opponent_total_shots,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Passes'
                THEN s.value_numeric
            END
        ) AS vasco_passes,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Passes'
                THEN s.value_numeric
            END
        ) AS opponent_passes,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Fouls'
                THEN s.value_numeric
            END
        ) AS vasco_fouls,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Fouls'
                THEN s.value_numeric
            END
        ) AS opponent_fouls,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Yellow cards'
                THEN s.value_numeric
            END
        ) AS vasco_yellow_cards,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Yellow cards'
                THEN s.value_numeric
            END
        ) AS opponent_yellow_cards,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Red cards'
                THEN s.value_numeric
            END
        ) AS vasco_red_cards,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Red cards'
                THEN s.value_numeric
            END
        ) AS opponent_red_cards,
	-- =====================================
	-- SHOTS
	-- =====================================
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Shots on target'
                THEN s.value_numeric
            END
        ) AS vasco_shots_on_target,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Shots on target'
                THEN s.value_numeric
            END
        ) AS opponent_shots_on_target,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Shots off target'
                THEN s.value_numeric
            END
        ) AS vasco_shots_off_target,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Shots off target'
                THEN s.value_numeric
            END
        ) AS opponent_shots_off_target,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Blocked shots'
                THEN s.value_numeric
            END
        ) AS vasco_blocked_shots,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Blocked shots'
                THEN s.value_numeric
            END
        ) AS opponent_blocked_shots,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Shots inside box'
                THEN s.value_numeric
            END
        ) AS vasco_shots_inside_box,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Shots inside box'
                THEN s.value_numeric
            END
        ) AS opponent_shots_inside_box,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Shots outside box'
                THEN s.value_numeric
            END
        ) AS vasco_shots_outside_box,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Shots outside box'
                THEN s.value_numeric
            END
        ) AS opponent_shots_outside_box,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Expected goals on target'
                THEN s.value_numeric
            END
        ) AS vasco_expected_goals_on_target,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Expected goals on target'
                THEN s.value_numeric
            END
        ) AS opponent_expected_goals_on_target,
	-- =====================================
	-- DEFENDING
	-- =====================================
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Total tackles'
                THEN s.value_numeric
            END
        ) AS vasco_total_tackles,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Total tackles'
                THEN s.value_numeric
            END
        ) AS opponent_total_tackles,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Interceptions'
                THEN s.value_numeric
            END
        ) AS vasco_interceptions,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Interceptions'
                THEN s.value_numeric
            END
        ) AS opponent_interceptions,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Recoveries'
                THEN s.value_numeric
            END
        ) AS vasco_recoveries,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Recoveries'
                THEN s.value_numeric
            END
        ) AS opponent_recoveries,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Clearances'
                THEN s.value_numeric
            END
        ) AS vasco_clearances,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Clearances'
                THEN s.value_numeric
            END
        ) AS opponent_clearances
FROM
	statistics s
INNER JOIN vasco_matches vm
        ON
	s.match_id = vm.match_id
WHERE
	s.period IN ('1ST', '2ND')
GROUP BY
	s.match_id,
	s.period
)
SELECT
	vm.*,
	sp.period,
	sp.vasco_ball_possession,
	sp.opponent_ball_possession,
	sp.vasco_expected_goals,
	sp.opponent_expected_goals,
	sp.vasco_big_chances,
	sp.opponent_big_chances,
	sp.vasco_corner_kicks,
	sp.opponent_corner_kicks,
	sp.vasco_total_shots,
	sp.opponent_total_shots,
	sp.vasco_passes,
	sp.opponent_passes,
	sp.vasco_fouls,
	sp.opponent_fouls,
	sp.vasco_yellow_cards,
	sp.opponent_yellow_cards,
	sp.vasco_red_cards,
	sp.opponent_red_cards,
	sp.vasco_shots_on_target,
	sp.opponent_shots_on_target,
	sp.vasco_shots_off_target,
	sp.opponent_shots_off_target,
	sp.vasco_blocked_shots,
	sp.opponent_blocked_shots,
	sp.vasco_shots_inside_box,
	sp.opponent_shots_inside_box,
	sp.vasco_shots_outside_box,
	sp.opponent_shots_outside_box,
	sp.vasco_expected_goals_on_target,
	sp.opponent_expected_goals_on_target,
	sp.vasco_total_tackles,
	sp.opponent_total_tackles,
	sp.vasco_interceptions,
	sp.opponent_interceptions,
	sp.vasco_recoveries,
	sp.opponent_recoveries,
	sp.vasco_clearances,
	sp.opponent_clearances
FROM
	vasco_matches vm
INNER JOIN statistics_pivot sp
    ON
	vm.match_id = sp.match_id;

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
