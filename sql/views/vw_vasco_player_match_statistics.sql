
CREATE OR REPLACE VIEW main.vw_vasco_player_match_statistics AS

WITH player_stats_pivot AS (

    SELECT
        match_id,
        team_id,
        player_id,

        MAX(player_name) AS player_name,
        MAX("position") AS "position",

        -- Estatísticas básicas
        MAX(CASE WHEN statistic_name = 'minutesPlayed' THEN value_numeric END) AS minutes_played,
        MAX(CASE WHEN statistic_name = 'goals' THEN value_numeric END) AS goals,
        MAX(CASE WHEN statistic_name = 'goalAssist' THEN value_numeric END) AS assists,
        MAX(CASE WHEN statistic_name = 'expectedGoals' THEN value_numeric END) AS expected_goals,
        MAX(CASE WHEN statistic_name = 'expectedAssists' THEN value_numeric END) AS expected_assists,
        MAX(CASE WHEN statistic_name = 'rating' THEN value_numeric END) AS rating,

        -- Finalizações
        MAX(CASE WHEN statistic_name = 'totalShots' THEN value_numeric END) AS total_shots,
        MAX(CASE WHEN statistic_name = 'onTargetScoringAttempt' THEN value_numeric END) AS shots_on_target,
        MAX(CASE WHEN statistic_name = 'shotOffTarget' THEN value_numeric END) AS shots_off_target,
        MAX(CASE WHEN statistic_name = 'blockedScoringAttempt' THEN value_numeric END) AS blocked_scoring_attempts,
        MAX(CASE WHEN statistic_name = 'expectedGoalsOnTarget' THEN value_numeric END) AS expected_goals_on_target,
        MAX(CASE WHEN statistic_name = 'hitWoodwork' THEN value_numeric END) AS hit_woodwork,

        -- Passes e criação
        MAX(CASE WHEN statistic_name = 'accuratePass' THEN value_numeric END) AS accurate_passes,
        MAX(CASE WHEN statistic_name = 'totalPass' THEN value_numeric END) AS total_passes,
        MAX(CASE WHEN statistic_name = 'accurateCross' THEN value_numeric END) AS accurate_crosses,
        MAX(CASE WHEN statistic_name = 'accurateLongBalls' THEN value_numeric END) AS accurate_long_balls,
        MAX(CASE WHEN statistic_name = 'totalLongBalls' THEN value_numeric END) AS total_long_balls,
        MAX(CASE WHEN statistic_name = 'bigChanceCreated' THEN value_numeric END) AS big_chances_created,
        MAX(CASE WHEN statistic_name = 'bigChanceMissed' THEN value_numeric END) AS big_chances_missed,
        MAX(CASE WHEN statistic_name = 'keyPass' THEN value_numeric END) AS key_passes,
        MAX(CASE WHEN statistic_name = 'crossNotClaimed' THEN value_numeric END) AS crosses_not_claimed,
        MAX(CASE WHEN statistic_name = 'wasFouled' THEN value_numeric END) AS was_fouled,

        -- Posse e condução
        MAX(CASE WHEN statistic_name = 'touches' THEN value_numeric END) AS touches,
        MAX(CASE WHEN statistic_name = 'possessionLostCtrl' THEN value_numeric END) AS possession_lost,
        MAX(CASE WHEN statistic_name = 'dispossessed' THEN value_numeric END) AS dispossessed,
        MAX(CASE WHEN statistic_name = 'unsuccessfulTouch' THEN value_numeric END) AS unsuccessful_touches,
        MAX(CASE WHEN statistic_name = 'ballCarriesCount' THEN value_numeric END) AS ball_carries_count,
        MAX(CASE WHEN statistic_name = 'bestBallCarryProgression' THEN value_numeric END) AS best_ball_carry_progression,
        MAX(CASE WHEN statistic_name = 'progressiveBallCarriesCount' THEN value_numeric END) AS progressive_ball_carries_count,
        MAX(CASE WHEN statistic_name = 'totalBallCarriesDistance' THEN value_numeric END) AS total_ball_carries_distance,
        MAX(CASE WHEN statistic_name = 'totalProgressiveBallCarriesDistance' THEN value_numeric END) AS total_progressive_ball_carries_distance,
        MAX(CASE WHEN statistic_name = 'totalProgression' THEN value_numeric END) AS total_progression,

        -- Desarmes, duelos e defesa
        MAX(CASE WHEN statistic_name = 'totalTackle' THEN value_numeric END) AS total_tackles,
        MAX(CASE WHEN statistic_name = 'wonTackle' THEN value_numeric END) AS tackles_won,
        MAX(CASE WHEN statistic_name = 'challengeLost' THEN value_numeric END) AS challenges_lost,
        MAX(CASE WHEN statistic_name = 'ballRecovery' THEN value_numeric END) AS ball_recoveries,
        MAX(CASE WHEN statistic_name = 'interceptionWon' THEN value_numeric END) AS interceptions,
        MAX(CASE WHEN statistic_name = 'duelWon' THEN value_numeric END) AS duels_won,
        MAX(CASE WHEN statistic_name = 'duelLost' THEN value_numeric END) AS duels_lost,
        MAX(CASE WHEN statistic_name = 'aerialWon' THEN value_numeric END) AS aerial_duels_won,
        MAX(CASE WHEN statistic_name = 'aerialLost' THEN value_numeric END) AS aerial_duels_lost,
        MAX(CASE WHEN statistic_name = 'totalClearance' THEN value_numeric END) AS total_clearances,
        MAX(CASE WHEN statistic_name = 'clearanceOffLine' THEN value_numeric END) AS clearances_off_line,
        MAX(CASE WHEN statistic_name = 'outfielderBlock' THEN value_numeric END) AS outfielder_blocks,
        MAX(CASE WHEN statistic_name = 'ownGoals' THEN value_numeric END) AS own_goals,
        MAX(CASE WHEN statistic_name = 'errorLeadToAGoal' THEN value_numeric END) AS errors_leading_to_goal,
        MAX(CASE WHEN statistic_name = 'errorLeadToAShot' THEN value_numeric END) AS errors_leading_to_shot,
        MAX(CASE WHEN statistic_name = 'lastManTackle' THEN value_numeric END) AS last_man_tackles,
        MAX(CASE WHEN statistic_name = 'totalContest' THEN value_numeric END) AS total_contests,
        MAX(CASE WHEN statistic_name = 'wonContest' THEN value_numeric END) AS contests_won,

        -- Cruzamentos
        MAX(CASE WHEN statistic_name = 'totalCross' THEN value_numeric END) AS total_crosses,

        -- Faltas e impedimentos
        MAX(CASE WHEN statistic_name = 'fouls' THEN value_numeric END) AS fouls,
        MAX(CASE WHEN statistic_name = 'totalOffside' THEN value_numeric END) AS offsides,

        -- Goleiros
        MAX(CASE WHEN statistic_name = 'saves' THEN value_numeric END) AS saves,
        MAX(CASE WHEN statistic_name = 'penaltySave' THEN value_numeric END) AS penalty_saves,
        MAX(CASE WHEN statistic_name = 'penaltyFaced' THEN value_numeric END) AS penalties_faced,
        MAX(CASE WHEN statistic_name = 'savedShotsFromInsideTheBox' THEN value_numeric END) AS saved_shots_from_inside_box,
        MAX(CASE WHEN statistic_name = 'goodHighClaim' THEN value_numeric END) AS good_high_claims,
        MAX(CASE WHEN statistic_name = 'punches' THEN value_numeric END) AS punches,
        MAX(CASE WHEN statistic_name = 'totalKeeperSweeper' THEN value_numeric END) AS total_keeper_sweeper,
        MAX(CASE WHEN statistic_name = 'accurateKeeperSweeper' THEN value_numeric END) AS accurate_keeper_sweeper,

        -- Métricas físicas
        MAX(CASE WHEN statistic_name = 'kilometersCovered' THEN value_numeric END) AS kilometers_covered,
        MAX(CASE WHEN statistic_name = 'metersCoveredHighSpeedRunningKm' THEN value_numeric END) AS meters_covered_high_speed_running_km,
        MAX(CASE WHEN statistic_name = 'metersCoveredRunningKm' THEN value_numeric END) AS meters_covered_running_km,
        MAX(CASE WHEN statistic_name = 'metersCoveredSprintingKm' THEN value_numeric END) AS meters_covered_sprinting_km,
        MAX(CASE WHEN statistic_name = 'numberOfSprints' THEN value_numeric END) AS number_of_sprints,
        MAX(CASE WHEN statistic_name = 'topSpeed' THEN value_numeric END) AS top_speed,

        -- Pênaltis
        MAX(CASE WHEN statistic_name = 'penaltyConceded' THEN value_numeric END) AS penalties_conceded,
        MAX(CASE WHEN statistic_name = 'penaltyMiss' THEN value_numeric END) AS penalties_missed,
        MAX(CASE WHEN statistic_name = 'penaltyWon' THEN value_numeric END) AS penalties_won,
        MAX(CASE WHEN statistic_name = 'penaltyShootoutGoal' THEN value_numeric END) AS penalty_shootout_goals,
        MAX(CASE WHEN statistic_name = 'penaltyShootoutMiss' THEN value_numeric END) AS penalty_shootout_misses,
        MAX(CASE WHEN statistic_name = 'penaltyShootoutSave' THEN value_numeric END) AS penalty_shootout_saves

    FROM main.player_statistics
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
            WHEN home_team_id = 1974 THEN 'HOME'
            WHEN away_team_id = 1974 THEN 'AWAY'
            ELSE NULL
        END AS venue,

        CASE
            WHEN home_team_id = 1974 THEN away_team_id
            WHEN away_team_id = 1974 THEN home_team_id
            ELSE NULL
        END AS opponent_team_id,

        CASE
            WHEN home_team_id = 1974 THEN away_team_name
            WHEN away_team_id = 1974 THEN home_team_name
            ELSE NULL
        END AS opponent_team_name

    FROM main.matches
    WHERE home_team_id = 1974
       OR away_team_id = 1974
)

SELECT
    ps.match_id,
    vm.match_date,
    vm.tournament_id,
    vm.tournament_name,
    vm.season_id,
    vm.season_name,
    vm.venue,
    vm.opponent_team_id,
    vm.opponent_team_name,

    ps.team_id,
    ps.player_id,

    COALESCE(p.player_name, ps.player_name) AS player_name,
    COALESCE(p."position", ps."position") AS "position",

    p.short_name,
    p.country_name,

    -- Estatísticas básicas
    ps.minutes_played,
    ps.goals,
    ps.assists,
    ps.expected_goals,
    ps.expected_assists,
    ps.rating,

    -- Finalizações
    ps.total_shots,
    ps.shots_on_target,
    ps.shots_off_target,
    ps.blocked_scoring_attempts,
    ps.expected_goals_on_target,
    ps.hit_woodwork,

    -- Passes e criação
    ps.accurate_passes,
    ps.total_passes,
    ps.accurate_crosses,
    ps.accurate_long_balls,
    ps.total_long_balls,
    ps.big_chances_created,
    ps.big_chances_missed,
    ps.key_passes,
    ps.crosses_not_claimed,
    ps.was_fouled,

    -- Posse e condução
    ps.touches,
    ps.possession_lost,
    ps.dispossessed,
    ps.unsuccessful_touches,
    ps.ball_carries_count,
    ps.best_ball_carry_progression,
    ps.progressive_ball_carries_count,
    ps.total_ball_carries_distance,
    ps.total_progressive_ball_carries_distance,
    ps.total_progression,

    -- Desarmes, duelos e defesa
    ps.total_tackles,
    ps.tackles_won,
    ps.challenges_lost,
    ps.ball_recoveries,
    ps.interceptions,
    ps.duels_won,
    ps.duels_lost,
    ps.aerial_duels_won,
    ps.aerial_duels_lost,
    ps.total_clearances,
    ps.clearances_off_line,
    ps.outfielder_blocks,
    ps.own_goals,
    ps.errors_leading_to_goal,
    ps.errors_leading_to_shot,
    ps.last_man_tackles,
    ps.total_contests,
    ps.contests_won,

    -- Cruzamentos
    ps.total_crosses,

    -- Faltas e impedimentos
    ps.fouls,
    ps.offsides,

    -- Goleiros
    ps.saves,
    ps.penalty_saves,
    ps.penalties_faced,
    ps.saved_shots_from_inside_box,
    ps.good_high_claims,
    ps.punches,
    ps.total_keeper_sweeper,
    ps.accurate_keeper_sweeper,

    -- Métricas físicas
    ps.kilometers_covered,
    ps.meters_covered_high_speed_running_km,
    ps.meters_covered_running_km,
    ps.meters_covered_sprinting_km,
    ps.number_of_sprints,
    ps.top_speed,

    -- Pênaltis
    ps.penalties_conceded,
    ps.penalties_missed,
    ps.penalties_won,
    ps.penalty_shootout_goals,
    ps.penalty_shootout_misses,
    ps.penalty_shootout_saves

FROM player_stats_pivot AS ps

INNER JOIN vasco_matches AS vm
    ON ps.match_id = vm.match_id

LEFT JOIN main.players AS p
    ON ps.player_id = p.player_id;
