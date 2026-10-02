CREATE OR REPLACE VIEW vw_vasco_player_season_metrics AS

WITH aggregated AS (

    SELECT

        -- ============================================================
        -- IDENTIFICAÇÃO
        -- ============================================================

        player_id,

        ARG_MAX(player_name, minutes_played) AS player_name,

        team_id,

        season_id,
        ARG_MAX(season_name, minutes_played) AS season_name,

        tournament_id,
        ARG_MAX(tournament_name, minutes_played) AS tournament_name,

        -- Posição predominante:
        -- posição em que o jogador acumulou mais minutos
        ARG_MAX(position, minutes_played) AS position,

        -- ============================================================
        -- PARTICIPAÇÃO
        -- ============================================================

        COUNT(
            DISTINCT CASE
                WHEN COALESCE(minutes_played, 0) > 0
                THEN match_id
            END
        ) AS matches_played,

        SUM(COALESCE(minutes_played, 0)) AS minutes_played,

        -- ============================================================
        -- RATING
        -- Média ponderada pelos minutos
        -- ============================================================

        SUM(
            CASE
                WHEN rating IS NOT NULL
                 AND COALESCE(minutes_played, 0) > 0
                THEN rating * minutes_played
                ELSE 0
            END
        ) AS rating_weighted_sum,

        SUM(
            CASE
                WHEN rating IS NOT NULL
                 AND COALESCE(minutes_played, 0) > 0
                THEN minutes_played
                ELSE 0
            END
        ) AS rating_minutes,

        -- ============================================================
        -- PERFORMANCE
        -- ============================================================

        SUM(COALESCE(touches, 0)) AS touches,

        SUM(COALESCE(possession_lost, 0)) AS possession_lost,

        -- ============================================================
        -- ATAQUE
        -- ============================================================

        SUM(COALESCE(goals, 0)) AS goals,
        SUM(COALESCE(assists, 0)) AS assists,
        SUM(COALESCE(own_goals, 0)) AS own_goals,

        SUM(COALESCE(expected_goals, 0)) AS expected_goals,
        SUM(COALESCE(expected_assists, 0)) AS expected_assists,
        SUM(COALESCE(expected_goals_on_target, 0)) AS expected_goals_on_target,

        SUM(COALESCE(total_shots, 0)) AS total_shots,
        SUM(COALESCE(shots_on_target, 0)) AS shots_on_target,
        SUM(COALESCE(shots_off_target, 0)) AS shots_off_target,

        SUM(COALESCE(hit_woodwork, 0)) AS hit_woodwork,

        SUM(COALESCE(big_chances_created, 0)) AS big_chances_created,
        SUM(COALESCE(big_chances_missed, 0)) AS big_chances_missed,

        -- ============================================================
        -- PASSES
        -- ============================================================

        SUM(COALESCE(total_passes, 0)) AS total_passes,
        SUM(COALESCE(accurate_passes, 0)) AS accurate_passes,
        SUM(COALESCE(key_passes, 0)) AS key_passes,

        SUM(COALESCE(total_long_balls, 0)) AS total_long_balls,
        SUM(COALESCE(accurate_long_balls, 0)) AS accurate_long_balls,

        SUM(COALESCE(total_crosses, 0)) AS total_crosses,
        SUM(COALESCE(accurate_crosses, 0)) AS accurate_crosses,

        -- ============================================================
        -- DEFESA
        -- ============================================================

        SUM(COALESCE(total_tackles, 0)) AS total_tackles,
        SUM(COALESCE(tackles_won, 0)) AS tackles_won,

        SUM(COALESCE(interceptions, 0)) AS interceptions,

        SUM(COALESCE(total_clearances, 0)) AS total_clearances,

        SUM(COALESCE(outfielder_blocks, 0)) AS outfielder_blocks,

        SUM(COALESCE(blocked_scoring_attempts, 0))
            AS blocked_scoring_attempts,

        SUM(COALESCE(challenges_lost, 0)) AS challenges_lost,

        SUM(COALESCE(last_man_tackles, 0)) AS last_man_tackles,

        SUM(COALESCE(errors_leading_to_shot, 0))
            AS errors_leading_to_shot,

        SUM(COALESCE(errors_leading_to_goal, 0))
            AS errors_leading_to_goal,

        SUM(COALESCE(clearances_off_line, 0))
            AS clearances_off_line,

        -- ============================================================
        -- DUELOS
        -- ============================================================

        SUM(COALESCE(duels_won, 0)) AS duels_won,
        SUM(COALESCE(duels_lost, 0)) AS duels_lost,

        SUM(COALESCE(aerial_duels_won, 0))
            AS aerial_duels_won,

        SUM(COALESCE(aerial_duels_lost, 0))
            AS aerial_duels_lost,

        SUM(COALESCE(total_contests, 0))
            AS total_contests,

        SUM(COALESCE(contests_won, 0))
            AS contests_won,

        -- ============================================================
        -- POSSE / RECUPERAÇÃO
        -- ============================================================

        SUM(COALESCE(ball_recoveries, 0))
            AS ball_recoveries,

        SUM(COALESCE(dispossessed, 0))
            AS dispossessed,

        SUM(COALESCE(unsuccessful_touches, 0))
            AS unsuccessful_touches,

        -- ============================================================
        -- CONDUÇÃO / PROGRESSÃO
        -- ============================================================

        SUM(COALESCE(ball_carries_count, 0))
            AS ball_carries_count,

        SUM(COALESCE(total_ball_carries_distance, 0))
            AS total_ball_carries_distance,

        SUM(COALESCE(progressive_ball_carries_count, 0))
            AS progressive_ball_carries_count,

        SUM(COALESCE(total_progressive_ball_carries_distance, 0))
            AS total_progressive_ball_carries_distance,

        SUM(COALESCE(total_progression, 0))
            AS total_progression,

        MAX(best_ball_carry_progression)
            AS best_ball_carry_progression,

        -- ============================================================
        -- DISCIPLINA
        -- ============================================================

        SUM(COALESCE(fouls, 0)) AS fouls,
        SUM(COALESCE(was_fouled, 0)) AS was_fouled,
        SUM(COALESCE(offsides, 0)) AS offsides,

        SUM(COALESCE(penalties_conceded, 0))
            AS penalties_conceded,

        SUM(COALESCE(penalties_won, 0))
            AS penalties_won,

        SUM(COALESCE(penalties_missed, 0))
            AS penalties_missed,

        -- ============================================================
        -- DISPUTA DE PÊNALTIS
        -- ============================================================

        SUM(COALESCE(penalty_shootout_goals, 0))
            AS penalty_shootout_goals,

        SUM(COALESCE(penalty_shootout_misses, 0))
            AS penalty_shootout_misses,

        SUM(COALESCE(penalty_shootout_saves, 0))
            AS penalty_shootout_saves,

        -- ============================================================
        -- FÍSICO
        -- ============================================================

        SUM(COALESCE(kilometers_covered, 0))
            AS kilometers_covered,

        SUM(COALESCE(meters_covered_running_km, 0))
            AS meters_covered_running_km,

        SUM(COALESCE(meters_covered_high_speed_running_km, 0))
            AS meters_covered_high_speed_running_km,

        SUM(COALESCE(meters_covered_sprinting_km, 0))
            AS meters_covered_sprinting_km,

        SUM(COALESCE(number_of_sprints, 0))
            AS number_of_sprints,

        MAX(top_speed) AS top_speed,

        -- ============================================================
        -- GOLEIRO
        -- ============================================================

        SUM(COALESCE(saves, 0)) AS saves,

        SUM(COALESCE(saved_shots_from_inside_box, 0))
            AS saved_shots_from_inside_box,

        SUM(COALESCE(good_high_claims, 0))
            AS good_high_claims,

        SUM(COALESCE(punches, 0))
            AS punches,

        SUM(COALESCE(crosses_not_claimed, 0))
            AS crosses_not_claimed,

        SUM(COALESCE(total_keeper_sweeper, 0))
            AS total_keeper_sweeper,

        SUM(COALESCE(accurate_keeper_sweeper, 0))
            AS accurate_keeper_sweeper,

        SUM(COALESCE(penalties_faced, 0))
            AS penalties_faced,

        SUM(COALESCE(penalty_saves, 0))
            AS penalty_saves

    FROM vw_vasco_player_match_statistics

    GROUP BY
        player_id,
        team_id,
        season_id,
        tournament_id
),

metrics AS (

    SELECT

        -- ============================================================
        -- IDENTIFICAÇÃO
        -- ============================================================

        player_id,
        player_name,
        team_id,
        season_id,
        season_name,
        tournament_id,
        tournament_name,
        position,

        matches_played,
        minutes_played,

        -- ============================================================
        -- PERFORMANCE
        -- ============================================================

        ROUND(
            rating_weighted_sum
            / NULLIF(rating_minutes, 0),
            2
        ) AS average_rating,

        touches,
        ROUND(
            touches / NULLIF(matches_played, 0),
            2
        ) AS touches_per_game,

        ROUND(
            touches * 90.0 / NULLIF(minutes_played, 0),
            2
        ) AS touches_per_90,

        possession_lost,
        ROUND(
            possession_lost / NULLIF(matches_played, 0),
            2
        ) AS possession_lost_per_game,

        ROUND(
            possession_lost * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS possession_lost_per_90,

        -- ============================================================
        -- ATAQUE
        -- ============================================================

        goals,

        ROUND(
            goals / NULLIF(matches_played, 0),
            2
        ) AS goals_per_game,

        ROUND(
            goals * 90.0 / NULLIF(minutes_played, 0),
            2
        ) AS goals_per_90,

        assists,

        ROUND(
            assists / NULLIF(matches_played, 0),
            2
        ) AS assists_per_game,

        ROUND(
            assists * 90.0 / NULLIF(minutes_played, 0),
            2
        ) AS assists_per_90,

        own_goals,

        ROUND(
            own_goals / NULLIF(matches_played, 0),
            2
        ) AS own_goals_per_game,

        ROUND(
            own_goals * 90.0 / NULLIF(minutes_played, 0),
            2
        ) AS own_goals_per_90,

        expected_goals,

        ROUND(
            expected_goals / NULLIF(matches_played, 0),
            3
        ) AS xg_per_game,

        ROUND(
            expected_goals * 90.0
            / NULLIF(minutes_played, 0),
            3
        ) AS xg_per_90,

        expected_assists,

        ROUND(
            expected_assists / NULLIF(matches_played, 0),
            3
        ) AS xa_per_game,

        ROUND(
            expected_assists * 90.0
            / NULLIF(minutes_played, 0),
            3
        ) AS xa_per_90,

        expected_goals_on_target,

        ROUND(
            expected_goals_on_target
            / NULLIF(matches_played, 0),
            3
        ) AS xgot_per_game,

        ROUND(
            expected_goals_on_target * 90.0
            / NULLIF(minutes_played, 0),
            3
        ) AS xgot_per_90,

        total_shots,

        ROUND(
            total_shots / NULLIF(matches_played, 0),
            2
        ) AS shots_per_game,

        ROUND(
            total_shots * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS shots_per_90,

        shots_on_target,

        ROUND(
            shots_on_target / NULLIF(matches_played, 0),
            2
        ) AS shots_on_target_per_game,

        ROUND(
            shots_on_target * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS shots_on_target_per_90,

        shots_off_target,

        ROUND(
            shots_off_target / NULLIF(matches_played, 0),
            2
        ) AS shots_off_target_per_game,

        ROUND(
            shots_off_target * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS shots_off_target_per_90,

        hit_woodwork,

        ROUND(
            hit_woodwork / NULLIF(matches_played, 0),
            2
        ) AS hit_woodwork_per_game,

        ROUND(
            hit_woodwork * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS hit_woodwork_per_90,

        big_chances_created,

        ROUND(
            big_chances_created
            / NULLIF(matches_played, 0),
            2
        ) AS big_chances_created_per_game,

        ROUND(
            big_chances_created * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS big_chances_created_per_90,

        big_chances_missed,

        ROUND(
            big_chances_missed
            / NULLIF(matches_played, 0),
            2
        ) AS big_chances_missed_per_game,

        ROUND(
            big_chances_missed * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS big_chances_missed_per_90,

        ROUND(
            shots_on_target
            / NULLIF(total_shots, 0),
            4
        ) AS shot_accuracy,

        -- ============================================================
        -- PASSES
        -- ============================================================

        total_passes,

        ROUND(
            total_passes / NULLIF(matches_played, 0),
            2
        ) AS passes_per_game,

        ROUND(
            total_passes * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS passes_per_90,

        accurate_passes,

        ROUND(
            accurate_passes / NULLIF(matches_played, 0),
            2
        ) AS accurate_passes_per_game,

        ROUND(
            accurate_passes * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS accurate_passes_per_90,

        key_passes,

        ROUND(
            key_passes / NULLIF(matches_played, 0),
            2
        ) AS key_passes_per_game,

        ROUND(
            key_passes * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS key_passes_per_90,

        total_long_balls,

        ROUND(
            total_long_balls
            / NULLIF(matches_played, 0),
            2
        ) AS long_balls_per_game,

        ROUND(
            total_long_balls * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS long_balls_per_90,

        accurate_long_balls,

        ROUND(
            accurate_long_balls
            / NULLIF(matches_played, 0),
            2
        ) AS accurate_long_balls_per_game,

        ROUND(
            accurate_long_balls * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS accurate_long_balls_per_90,

        total_crosses,

        ROUND(
            total_crosses / NULLIF(matches_played, 0),
            2
        ) AS crosses_per_game,

        ROUND(
            total_crosses * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS crosses_per_90,

        accurate_crosses,

        ROUND(
            accurate_crosses
            / NULLIF(matches_played, 0),
            2
        ) AS accurate_crosses_per_game,

        ROUND(
            accurate_crosses * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS accurate_crosses_per_90,

        ROUND(
            accurate_passes
            / NULLIF(total_passes, 0),
            4
        ) AS pass_accuracy,

        ROUND(
            accurate_long_balls
            / NULLIF(total_long_balls, 0),
            4
        ) AS long_ball_accuracy,

        ROUND(
            accurate_crosses
            / NULLIF(total_crosses, 0),
            4
        ) AS cross_accuracy,

        -- ============================================================
        -- DEFESA
        -- ============================================================

        total_tackles,

        ROUND(
            total_tackles / NULLIF(matches_played, 0),
            2
        ) AS tackles_per_game,

        ROUND(
            total_tackles * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS tackles_per_90,

        tackles_won,

        ROUND(
            tackles_won / NULLIF(matches_played, 0),
            2
        ) AS tackles_won_per_game,

        ROUND(
            tackles_won * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS tackles_won_per_90,

        interceptions,

        ROUND(
            interceptions / NULLIF(matches_played, 0),
            2
        ) AS interceptions_per_game,

        ROUND(
            interceptions * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS interceptions_per_90,

        total_clearances,

        ROUND(
            total_clearances
            / NULLIF(matches_played, 0),
            2
        ) AS clearances_per_game,

        ROUND(
            total_clearances * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS clearances_per_90,

        outfielder_blocks,

        ROUND(
            outfielder_blocks
            / NULLIF(matches_played, 0),
            2
        ) AS outfielder_blocks_per_game,

        ROUND(
            outfielder_blocks * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS outfielder_blocks_per_90,

        blocked_scoring_attempts,

        ROUND(
            blocked_scoring_attempts
            / NULLIF(matches_played, 0),
            2
        ) AS blocked_scoring_attempts_per_game,

        ROUND(
            blocked_scoring_attempts * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS blocked_scoring_attempts_per_90,

        challenges_lost,

        ROUND(
            challenges_lost / NULLIF(matches_played, 0),
            2
        ) AS challenges_lost_per_game,

        ROUND(
            challenges_lost * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS challenges_lost_per_90,

        last_man_tackles,

        ROUND(
            last_man_tackles
            / NULLIF(matches_played, 0),
            2
        ) AS last_man_tackles_per_game,

        ROUND(
            last_man_tackles * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS last_man_tackles_per_90,

        errors_leading_to_shot,

        ROUND(
            errors_leading_to_shot
            / NULLIF(matches_played, 0),
            2
        ) AS errors_leading_to_shot_per_game,

        ROUND(
            errors_leading_to_shot * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS errors_leading_to_shot_per_90,

        errors_leading_to_goal,

        ROUND(
            errors_leading_to_goal
            / NULLIF(matches_played, 0),
            2
        ) AS errors_leading_to_goal_per_game,

        ROUND(
            errors_leading_to_goal * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS errors_leading_to_goal_per_90,

        clearances_off_line,

        ROUND(
            clearances_off_line
            / NULLIF(matches_played, 0),
            2
        ) AS clearances_off_line_per_game,

        ROUND(
            clearances_off_line * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS clearances_off_line_per_90,

        -- ============================================================
        -- DUELOS
        -- ============================================================

        duels_won,

        ROUND(
            duels_won / NULLIF(matches_played, 0),
            2
        ) AS duels_won_per_game,

        ROUND(
            duels_won * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS duels_won_per_90,

        duels_lost,

        ROUND(
            duels_lost / NULLIF(matches_played, 0),
            2
        ) AS duels_lost_per_game,

        ROUND(
            duels_lost * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS duels_lost_per_90,

        duels_won + duels_lost AS total_duels,

        ROUND(
            (duels_won + duels_lost)
            / NULLIF(matches_played, 0),
            2
        ) AS duels_per_game,

        ROUND(
            (duels_won + duels_lost) * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS duels_per_90,

        ROUND(
            duels_won
            / NULLIF(duels_won + duels_lost, 0),
            4
        ) AS duel_win_rate,

        aerial_duels_won,

        ROUND(
            aerial_duels_won
            / NULLIF(matches_played, 0),
            2
        ) AS aerial_duels_won_per_game,

        ROUND(
            aerial_duels_won * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS aerial_duels_won_per_90,

        aerial_duels_lost,

        ROUND(
            aerial_duels_lost
            / NULLIF(matches_played, 0),
            2
        ) AS aerial_duels_lost_per_game,

        ROUND(
            aerial_duels_lost * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS aerial_duels_lost_per_90,

        aerial_duels_won + aerial_duels_lost
            AS total_aerial_duels,

        ROUND(
            (aerial_duels_won + aerial_duels_lost)
            / NULLIF(matches_played, 0),
            2
        ) AS aerial_duels_per_game,

        ROUND(
            (aerial_duels_won + aerial_duels_lost) * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS aerial_duels_per_90,

        ROUND(
            aerial_duels_won
            / NULLIF(
                aerial_duels_won + aerial_duels_lost,
                0
            ),
            4
        ) AS aerial_duel_win_rate,

        -- Duelos pelo chão
        (duels_won + duels_lost)
        - (aerial_duels_won + aerial_duels_lost)
            AS ground_duels,

        ROUND(
            (
                (duels_won + duels_lost)
                - (aerial_duels_won + aerial_duels_lost)
            )
            / NULLIF(matches_played, 0),
            2
        ) AS ground_duels_per_game,

        ROUND(
            (
                (duels_won + duels_lost)
                - (aerial_duels_won + aerial_duels_lost)
            ) * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS ground_duels_per_90,

        duels_won - aerial_duels_won
            AS ground_duels_won,

        ROUND(
            (duels_won - aerial_duels_won)
            / NULLIF(matches_played, 0),
            2
        ) AS ground_duels_won_per_game,

        ROUND(
            (duels_won - aerial_duels_won) * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS ground_duels_won_per_90,

        duels_lost - aerial_duels_lost
            AS ground_duels_lost,

        ROUND(
            (duels_lost - aerial_duels_lost)
            / NULLIF(matches_played, 0),
            2
        ) AS ground_duels_lost_per_game,

        ROUND(
            (duels_lost - aerial_duels_lost) * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS ground_duels_lost_per_90,

        ROUND(
            (duels_won - aerial_duels_won)
            / NULLIF(
                (duels_won + duels_lost)
                - (aerial_duels_won + aerial_duels_lost),
                0
            ),
            4
        ) AS ground_duel_win_rate,

        -- Contests
        total_contests,

        ROUND(
            total_contests
            / NULLIF(matches_played, 0),
            2
        ) AS contests_per_game,

        ROUND(
            total_contests * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS contests_per_90,

        contests_won,

        ROUND(
            contests_won
            / NULLIF(matches_played, 0),
            2
        ) AS contests_won_per_game,

        ROUND(
            contests_won * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS contests_won_per_90,

        ROUND(
            contests_won
            / NULLIF(total_contests, 0),
            4
        ) AS contest_win_rate,

        -- ============================================================
        -- RECUPERAÇÃO / POSSE
        -- ============================================================

        ball_recoveries,

        ROUND(
            ball_recoveries
            / NULLIF(matches_played, 0),
            2
        ) AS ball_recoveries_per_game,

        ROUND(
            ball_recoveries * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS ball_recoveries_per_90,

        dispossessed,

        ROUND(
            dispossessed
            / NULLIF(matches_played, 0),
            2
        ) AS dispossessed_per_game,

        ROUND(
            dispossessed * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS dispossessed_per_90,

        unsuccessful_touches,

        ROUND(
            unsuccessful_touches
            / NULLIF(matches_played, 0),
            2
        ) AS unsuccessful_touches_per_game,

        ROUND(
            unsuccessful_touches * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS unsuccessful_touches_per_90,

        -- ============================================================
        -- CONDUÇÃO / PROGRESSÃO
        -- ============================================================

        ball_carries_count,

        ROUND(
            ball_carries_count
            / NULLIF(matches_played, 0),
            2
        ) AS ball_carries_per_game,

        ROUND(
            ball_carries_count * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS ball_carries_per_90,

        total_ball_carries_distance,

        ROUND(
            total_ball_carries_distance
            / NULLIF(matches_played, 0),
            2
        ) AS ball_carries_distance_per_game,

        progressive_ball_carries_count,

        ROUND(
            progressive_ball_carries_count
            / NULLIF(matches_played, 0),
            2
        ) AS progressive_carries_per_game,

        ROUND(
            progressive_ball_carries_count * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS progressive_carries_per_90,

        total_progressive_ball_carries_distance,

        ROUND(
            total_progressive_ball_carries_distance
            / NULLIF(matches_played, 0),
            2
        ) AS progressive_carry_distance_per_game,

        total_progression,

        ROUND(
            total_progression
            / NULLIF(matches_played, 0),
            2
        ) AS progression_per_game,

        ROUND(
            total_progression * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS progression_per_90,

        best_ball_carry_progression,

        -- ============================================================
        -- DISCIPLINA
        -- ============================================================

        fouls,

        ROUND(
            fouls / NULLIF(matches_played, 0),
            2
        ) AS fouls_per_game,

        ROUND(
            fouls * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS fouls_per_90,

        was_fouled,

        ROUND(
            was_fouled / NULLIF(matches_played, 0),
            2
        ) AS was_fouled_per_game,

        ROUND(
            was_fouled * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS was_fouled_per_90,

        offsides,

        ROUND(
            offsides / NULLIF(matches_played, 0),
            2
        ) AS offsides_per_game,

        ROUND(
            offsides * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS offsides_per_90,

        penalties_conceded,

        ROUND(
            penalties_conceded
            / NULLIF(matches_played, 0),
            2
        ) AS penalties_conceded_per_game,

        penalties_won,

        ROUND(
            penalties_won
            / NULLIF(matches_played, 0),
            2
        ) AS penalties_won_per_game,

        penalties_missed,

        ROUND(
            penalties_missed
            / NULLIF(matches_played, 0),
            2
        ) AS penalties_missed_per_game,

        -- ============================================================
        -- DISPUTA DE PÊNALTIS
        -- ============================================================

        penalty_shootout_goals,
        penalty_shootout_misses,
        penalty_shootout_saves,

        -- ============================================================
        -- FÍSICO
        -- ============================================================

        kilometers_covered,

        ROUND(
            kilometers_covered
            / NULLIF(matches_played, 0),
            3
        ) AS kilometers_covered_per_game,

        meters_covered_running_km,

        ROUND(
            meters_covered_running_km
            / NULLIF(matches_played, 0),
            3
        ) AS running_distance_per_game,

        meters_covered_high_speed_running_km,

        ROUND(
            meters_covered_high_speed_running_km
            / NULLIF(matches_played, 0),
            3
        ) AS high_speed_running_distance_per_game,

        meters_covered_sprinting_km,

        ROUND(
            meters_covered_sprinting_km
            / NULLIF(matches_played, 0),
            3
        ) AS sprinting_distance_per_game,

        number_of_sprints,

        ROUND(
            number_of_sprints
            / NULLIF(matches_played, 0),
            2
        ) AS sprints_per_game,

        ROUND(
            number_of_sprints * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS sprints_per_90,

        top_speed,

        -- ============================================================
        -- GOLEIRO
        -- ============================================================

        saves,

        ROUND(
            saves / NULLIF(matches_played, 0),
            2
        ) AS saves_per_game,

        ROUND(
            saves * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS saves_per_90,

        saved_shots_from_inside_box,

        ROUND(
            saved_shots_from_inside_box
            / NULLIF(matches_played, 0),
            2
        ) AS saved_shots_inside_box_per_game,

        ROUND(
            saved_shots_from_inside_box * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS saved_shots_inside_box_per_90,

        good_high_claims,

        ROUND(
            good_high_claims
            / NULLIF(matches_played, 0),
            2
        ) AS good_high_claims_per_game,

        ROUND(
            good_high_claims * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS good_high_claims_per_90,

        punches,

        ROUND(
            punches / NULLIF(matches_played, 0),
            2
        ) AS punches_per_game,

        ROUND(
            punches * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS punches_per_90,

        crosses_not_claimed,

        ROUND(
            crosses_not_claimed
            / NULLIF(matches_played, 0),
            2
        ) AS crosses_not_claimed_per_game,

        ROUND(
            crosses_not_claimed * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS crosses_not_claimed_per_90,

        total_keeper_sweeper,

        ROUND(
            total_keeper_sweeper
            / NULLIF(matches_played, 0),
            2
        ) AS keeper_sweeper_per_game,

        ROUND(
            total_keeper_sweeper * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS keeper_sweeper_per_90,

        accurate_keeper_sweeper,

        ROUND(
            accurate_keeper_sweeper
            / NULLIF(matches_played, 0),
            2
        ) AS accurate_keeper_sweeper_per_game,

        ROUND(
            accurate_keeper_sweeper * 90.0
            / NULLIF(minutes_played, 0),
            2
        ) AS accurate_keeper_sweeper_per_90,

        penalties_faced,

        ROUND(
            penalties_faced
            / NULLIF(matches_played, 0),
            2
        ) AS penalties_faced_per_game,

        penalty_saves,

        ROUND(
            penalty_saves
            / NULLIF(matches_played, 0),
            2
        ) AS penalty_saves_per_game

    FROM aggregated
)

SELECT *
FROM metrics;