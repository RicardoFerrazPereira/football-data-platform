-- CRIAR A VIEW: vw_vasco_player_match_statistics
CREATE OR REPLACE VIEW vw_vasco_player_match_statistics AS
WITH player_stats_pivot AS (
    SELECT
        match_id,
        team_id,
        player_id,
        MAX(player_name) AS player_name,
        MAX(position) AS position,
        MAX(
            CASE
                WHEN statistic_name = 'minutesPlayed'
                THEN value_numeric
            END
        ) AS minutes_played,
        MAX(
            CASE
                WHEN statistic_name = 'goals'
                THEN value_numeric
            END
        ) AS goals,
        MAX(
            CASE
                WHEN statistic_name = 'goalAssist'
                THEN value_numeric
            END
        ) AS assists,
        MAX(
            CASE
                WHEN statistic_name = 'expectedGoals'
                THEN value_numeric
            END
        ) AS expected_goals,
        MAX(
            CASE
                WHEN statistic_name = 'expectedAssists'
                THEN value_numeric
            END
        ) AS expected_assists,
        MAX(
            CASE
                WHEN statistic_name = 'rating'
                THEN value_numeric
            END
        ) AS rating,
        MAX(
            CASE
                WHEN statistic_name = 'totalShots'
                THEN value_numeric
            END
        ) AS total_shots,
        MAX(
            CASE
                WHEN statistic_name = 'onTargetScoringAttempt'
                THEN value_numeric
            END
        ) AS shots_on_target,
        MAX(
            CASE
                WHEN statistic_name = 'accuratePass'
                THEN value_numeric
            END
        ) AS accurate_passes,
        MAX(
            CASE
                WHEN statistic_name = 'totalPass'
                THEN value_numeric
            END
        ) AS total_passes,
        MAX(
            CASE
                WHEN statistic_name = 'totalTackle'
                THEN value_numeric
            END
        ) AS total_tackles,
        MAX(
            CASE
                WHEN statistic_name = 'wonTackle'
                THEN value_numeric
            END
        ) AS tackles_won,
        MAX(
            CASE
                WHEN statistic_name = 'ballRecovery'
                THEN value_numeric
            END
        ) AS ball_recoveries,
        MAX(
            CASE
                WHEN statistic_name = 'interceptionWon'
                THEN value_numeric
            END
        ) AS interceptions,
        MAX(
            CASE
                WHEN statistic_name = 'duelWon'
                THEN value_numeric
            END
        ) AS duels_won,
        MAX(
            CASE
                WHEN statistic_name = 'duelLost'
                THEN value_numeric
            END
        ) AS duels_lost
    FROM player_statistics
    WHERE team_id = 1974
    GROUP BY
        match_id,
        team_id,
        player_id
),
vasco_matches AS (
    SELECT
        match_id,
        match_date,
        tournament_id,
        tournament_name,
        season_id,
        season_name,
        CASE
            WHEN home_team_id = 1974
            THEN 'HOME'
            WHEN away_team_id = 1974
            THEN 'AWAY'
        END AS venue,
        CASE
            WHEN home_team_id = 1974
            THEN away_team_id
            WHEN away_team_id = 1974
            THEN home_team_id
        END AS opponent_team_id,
        CASE
            WHEN home_team_id = 1974
            THEN away_team_name
            WHEN away_team_id = 1974
            THEN home_team_name
        END AS opponent_team_name
    FROM matches
    WHERE
        home_team_id = 1974
        OR away_team_id = 1974
)
SELECT
    -- =====================================
    -- MATCH
    -- =====================================
    ps.match_id,
    vm.match_date,
    vm.tournament_id,
    vm.tournament_name,
    vm.season_id,
    vm.season_name,
    vm.venue,
    vm.opponent_team_id,
    vm.opponent_team_name,
    -- =====================================
    -- TEAM
    -- =====================================
    ps.team_id,
    -- =====================================
    -- PLAYER
    -- =====================================
    ps.player_id,
    COALESCE(p.player_name, ps.player_name) AS player_name,
    COALESCE(p.position, ps.position) AS position,
    p.short_name,
    p.country_name,
    -- =====================================
    -- PERFORMANCE
    -- =====================================
    ps.minutes_played,
    ps.goals,
    ps.assists,
    ps.expected_goals,
    ps.expected_assists,
    ps.rating,
    -- =====================================
    -- SHOOTING
    -- =====================================
    ps.total_shots,
    ps.shots_on_target,
    -- =====================================
    -- PASSING
    -- =====================================
    ps.accurate_passes,
    ps.total_passes,
    -- =====================================
    -- DEFENDING
    -- =====================================
    ps.total_tackles,
    ps.tackles_won,
    ps.ball_recoveries,
    ps.interceptions,
    -- =====================================
    -- DUELS
    -- =====================================
    ps.duels_won,
    ps.duels_lost
FROM player_stats_pivot ps
INNER JOIN vasco_matches vm
    ON ps.match_id = vm.match_id
LEFT JOIN players p
    ON ps.player_id = p.player_id;