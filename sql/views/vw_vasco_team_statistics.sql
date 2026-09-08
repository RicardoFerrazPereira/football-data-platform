-- CRIAR A VIEW -> vw_vasco_team_statistics
CREATE OR REPLACE
VIEW vw_vasco_team_statistics AS
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
                 AND s.statistic_name = 'Expected goals'
                 AND s.group_name = 'Match overview'
                THEN s.value_numeric
            END
        ) AS vasco_expected_goals,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Expected goals'
                 AND s.group_name = 'Match overview'
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
                 AND s.statistic_name = 'Total shots'
                 AND s.group_name = 'Match overview'
                THEN s.value_numeric
            END
        ) AS vasco_total_shots,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Total shots'
                 AND s.group_name = 'Match overview'
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
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Average rating'
                THEN s.value_numeric
            END
        ) AS vasco_average_rating,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Average rating'
                THEN s.value_numeric
            END
        ) AS opponent_average_rating,
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
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Hit woodwork'
                THEN s.value_numeric
            END
        ) AS vasco_hit_woodwork,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Hit woodwork'
                THEN s.value_numeric
            END
        ) AS opponent_hit_woodwork,
	-- =====================================
	-- PASSES
	-- =====================================
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Accurate passes'
                THEN s.value_numeric
            END
        ) AS vasco_accurate_passes,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Accurate passes'
                THEN s.value_numeric
            END
        ) AS opponent_accurate_passes,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Final third entries'
                THEN s.value_numeric
            END
        ) AS vasco_final_third_entries,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Final third entries'
                THEN s.value_numeric
            END
        ) AS opponent_final_third_entries,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Crosses'
                THEN s.value_numeric
            END
        ) AS vasco_crosses,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Crosses'
                THEN s.value_numeric
            END
        ) AS opponent_crosses,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Long balls'
                THEN s.value_numeric
            END
        ) AS vasco_long_balls,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Long balls'
                THEN s.value_numeric
            END
        ) AS opponent_long_balls,
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
                 AND s.statistic_name = 'Tackles won'
                THEN s.value_numeric
            END
        ) AS vasco_tackles_won_pct,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Tackles won'
                THEN s.value_numeric
            END
        ) AS opponent_tackles_won_pct,
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
        ) AS opponent_clearances,
	-- =====================================
	-- DUELS
	-- =====================================
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Duels'
                THEN s.value_numeric
            END
        ) AS vasco_duels_pct,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Duels'
                THEN s.value_numeric
            END
        ) AS opponent_duels_pct,
	MAX(
            CASE
                WHEN s.team_side = vm.vasco_side
                 AND s.statistic_name = 'Dispossessed'
                THEN s.value_numeric
            END
        ) AS vasco_dispossessed,
	MAX(
            CASE
                WHEN s.team_side <> vm.vasco_side
                 AND s.statistic_name = 'Dispossessed'
                THEN s.value_numeric
            END
        ) AS opponent_dispossessed
FROM
	statistics s
INNER JOIN vasco_matches vm
        ON
	s.match_id = vm.match_id
WHERE
	s.period = 'ALL'
GROUP BY
	s.match_id
)
SELECT
	vm.*,
	sp.*
FROM
	vasco_matches vm
LEFT JOIN statistics_pivot sp
    ON
	vm.match_id = sp.match_id;