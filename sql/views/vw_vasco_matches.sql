-- Criar a VIEW -> vw_vasco_matches
CREATE OR REPLACE VIEW vw_vasco_matches AS
WITH vasco_matches AS (
    SELECT
        -- =====================================
        -- IDENTIFICAÇÃO
        -- =====================================
		match_id,
        match_date,
        tournament_id,
        tournament_name,
        season_id,
        season_name,
        status,
        -- =====================================
        -- LOCAL DO JOGO
        -- =====================================
        CASE
            WHEN home_team_id = 1974 THEN 'HOME'
            WHEN away_team_id = 1974 THEN 'AWAY'
        END AS venue,
        -- =====================================
        -- ADVERSÁRIO
        -- =====================================
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
        END AS opponent_team_name,
        -- =====================================
        -- PLACAR TEMPO NORMAL
        -- =====================================
        CASE
            WHEN home_team_id = 1974
                THEN home_score
            WHEN away_team_id = 1974
                THEN away_score
        END AS vasco_score,
        CASE
            WHEN home_team_id = 1974
                THEN away_score
            WHEN away_team_id = 1974
                THEN home_score
        END AS opponent_score,
        -- =====================================
        -- PÊNALTIS
        -- =====================================
        CASE
            WHEN home_team_id = 1974
                THEN home_score_penalties
            WHEN away_team_id = 1974
                THEN away_score_penalties
        END AS vasco_penalties,
        CASE
            WHEN home_team_id = 1974
                THEN away_score_penalties
            WHEN away_team_id = 1974
                THEN home_score_penalties
        END AS opponent_penalties,
        -- =====================================
        -- PLACAR ACUMULADO SOFASCORE
        -- =====================================
        CASE
            WHEN home_team_id = 1974
                THEN home_score_current
            WHEN away_team_id = 1974
                THEN away_score_current
        END AS vasco_score_current,
        CASE
            WHEN home_team_id = 1974
                THEN away_score_current
            WHEN away_team_id = 1974
                THEN home_score_current
        END AS opponent_score_current
    FROM matches
    WHERE
        home_team_id = 1974
        OR away_team_id = 1974
)
SELECT
    *,
    -- =====================================
    -- RESULTADO NO TEMPO NORMAL
    -- =====================================
    CASE
        WHEN vasco_score > opponent_score
            THEN 'WIN'
        WHEN vasco_score < opponent_score
            THEN 'LOSS'
        WHEN vasco_score = opponent_score
            THEN 'DRAW'
    END AS result_normal_time,
    -- =====================================
    -- DECISÃO NOS PÊNALTIS
    -- =====================================
    CASE
        WHEN
            vasco_score = opponent_score
            AND vasco_penalties IS NOT NULL
            AND opponent_penalties IS NOT NULL
            THEN TRUE
        ELSE FALSE
    END AS decided_on_penalties,
    -- =====================================
    -- RESULTADO FINAL
    -- =====================================
    CASE
        -- Vitória no tempo normal
        WHEN vasco_score > opponent_score
            THEN 'WIN'
        -- Derrota no tempo normal
        WHEN vasco_score < opponent_score
            THEN 'LOSS'
        -- Empate + vitória nos pênaltis
        WHEN
            vasco_score = opponent_score
            AND vasco_penalties > opponent_penalties
            THEN 'WIN'
        -- Empate + derrota nos pênaltis
        WHEN
            vasco_score = opponent_score
            AND vasco_penalties < opponent_penalties
            THEN 'LOSS'
        -- Empate sem pênaltis
        WHEN vasco_score = opponent_score
            THEN 'DRAW'
    END AS result_final
FROM vasco_matches;