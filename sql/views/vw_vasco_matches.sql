-- Criar a VIEW -> vw_vasco_matches

CREATE OR REPLACE VIEW vw_vasco_matches AS

WITH vasco_matches AS (

    SELECT
        match_id,
        match_date,
        tournament_id,
        tournament_name,
        season_id,
        season_name,
        status,

        -- Mandante ou visitante
        CASE
            WHEN home_team_id = 1974 THEN 'HOME'
            WHEN away_team_id = 1974 THEN 'AWAY'
        END AS venue,

        -- Adversário
        CASE
            WHEN home_team_id = 1974 THEN away_team_id
            WHEN away_team_id = 1974 THEN home_team_id
        END AS opponent_team_id,

        CASE
            WHEN home_team_id = 1974 THEN away_team_name
            WHEN away_team_id = 1974 THEN home_team_name
        END AS opponent_team_name,

        -- Placar do Vasco no tempo normal
        CASE
            WHEN home_team_id = 1974 THEN home_score
            WHEN away_team_id = 1974 THEN away_score
        END AS vasco_score,

        -- Placar do adversário no tempo normal
        CASE
            WHEN home_team_id = 1974 THEN away_score
            WHEN away_team_id = 1974 THEN home_score
        END AS opponent_score,

        -- Pênaltis do Vasco
        CASE
            WHEN home_team_id = 1974 THEN home_score_penalties
            WHEN away_team_id = 1974 THEN away_score_penalties
        END AS vasco_penalties,

        -- Pênaltis do adversário
        CASE
            WHEN home_team_id = 1974 THEN away_score_penalties
            WHEN away_team_id = 1974 THEN home_score_penalties
        END AS opponent_penalties,

        -- Score current do Vasco
        CASE
            WHEN home_team_id = 1974 THEN home_score_current
            WHEN away_team_id = 1974 THEN away_score_current
        END AS vasco_score_current,

        -- Score current do adversário
        CASE
            WHEN home_team_id = 1974 THEN away_score_current
            WHEN away_team_id = 1974 THEN home_score_current
        END AS opponent_score_current

    FROM matches

    WHERE
        home_team_id = 1974
        OR away_team_id = 1974
)

SELECT
    *,

    ----------------------------------------------------------------
    -- Resultado considerando apenas o placar do jogo
    -- (tempo normal / placar oficial da partida)
    ----------------------------------------------------------------
    CASE
        WHEN vasco_score > opponent_score THEN 'WIN'
        WHEN vasco_score < opponent_score THEN 'LOSS'
        WHEN vasco_score = opponent_score THEN 'DRAW'
    END AS result_normal_time,

    ----------------------------------------------------------------
    -- Identifica se houve decisão por pênaltis
    --
    -- IMPORTANTE:
    -- Não podemos exigir que vasco_score = opponent_score.
    --
    -- Em confrontos eliminatórios de ida e volta, por exemplo,
    -- o jogo pode terminar 2x1 e ainda assim ir para os pênaltis
    -- por causa do resultado agregado.
    ----------------------------------------------------------------
    CASE
        WHEN
            vasco_penalties IS NOT NULL
            AND opponent_penalties IS NOT NULL
        THEN TRUE
        ELSE FALSE
    END AS decided_on_penalties,

    ----------------------------------------------------------------
    -- Resultado final
    --
    -- Primeiro verificamos os pênaltis, pois eles devem prevalecer
    -- sobre o placar normal quando existem.
    --
    -- Depois, caso não haja pênaltis, utilizamos o placar normal.
    ----------------------------------------------------------------
    CASE

        -- Vasco venceu nos pênaltis
        WHEN
            vasco_penalties IS NOT NULL
            AND opponent_penalties IS NOT NULL
            AND vasco_penalties > opponent_penalties
        THEN 'WIN'

        -- Vasco perdeu nos pênaltis
        WHEN
            vasco_penalties IS NOT NULL
            AND opponent_penalties IS NOT NULL
            AND vasco_penalties < opponent_penalties
        THEN 'LOSS'

        -- Sem decisão por pênaltis:
        -- resultado pelo placar normal
        WHEN vasco_score > opponent_score
        THEN 'WIN'

        WHEN vasco_score < opponent_score
        THEN 'LOSS'

        WHEN vasco_score = opponent_score
        THEN 'DRAW'

    END AS result_final

FROM vasco_matches;