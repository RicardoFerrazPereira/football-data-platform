SELECT
    ps.player_id,
    MAX(ps.player_name) AS player_name,
    MAX(
        CASE
            WHEN ps.statistic_name = 'goals'
            THEN ps.value_numeric
        END
    ) AS goals,
    MAX(
        CASE
            WHEN ps.statistic_name = 'goalAssist'
            THEN ps.value_numeric
        END
    ) AS assists,
    MAX(
        CASE
            WHEN ps.statistic_name = 'expectedGoals'
            THEN ps.value_numeric
        END
    ) AS xg,
    MAX(
        CASE
            WHEN ps.statistic_name = 'expectedAssists'
            THEN ps.value_numeric
        END
    ) AS xa,
    MAX(
        CASE
            WHEN ps.statistic_name = 'minutesPlayed'
            THEN ps.value_numeric
        END
    ) AS minutes_played,
    MAX(
        CASE
            WHEN ps.statistic_name = 'rating'
            THEN ps.value_numeric
        END
    ) AS rating
FROM player_statistics AS ps
WHERE ps.match_id = 16253383
  AND ps.team_id = 1974
GROUP BY
    ps.player_id
ORDER BY
    goals DESC NULLS LAST,
    rating DESC NULLS LAST;

-- nomes das colunas e como a tabela player_statistics está registrada no DuckDB

SELECT
    player_id,
    player_name,
    statistic_name,
    value_numeric,
FROM player_statistics
WHERE match_id = 16253383
  AND team_id = 1974
LIMIT 50;

SELECT
    SUM(value_numeric) AS total_goals
FROM player_statistics
WHERE match_id = 16253383
  AND team_id = 1974
  AND statistic_name = 'goals';

-- Total de vitória do Vasco em 2026

SELECT
	*
FROM
	matches
WHERE
	EXTRACT(YEAR FROM match_date) = 2026
	AND (
        (home_team_id = 1974
		AND home_score > away_score)
	OR
        (away_team_id = 1974
		AND away_score > home_score)
    );

-- retrospecto completo do Vasco em 2026

WITH vasco_matches AS (
SELECT
	match_id,
	match_date,
	tournament_name,
	CASE
		WHEN home_team_id = 1974 THEN home_score
		ELSE away_score
	END AS vasco_goals,
	CASE
		WHEN home_team_id = 1974 THEN away_score
		ELSE home_score
	END AS opponent_goals
FROM
	matches
WHERE
	EXTRACT(YEAR FROM match_date) = 2026
	AND 1974 IN (home_team_id, away_team_id)
),
retrospecto AS (
SELECT
	COUNT(*) AS jogos,
	SUM(
            CASE
                WHEN vasco_goals > opponent_goals THEN 1
                ELSE 0
            END
        ) AS vitorias,
	SUM(
            CASE
                WHEN vasco_goals = opponent_goals THEN 1
                ELSE 0
            END
        ) AS empates,
	SUM(
            CASE
                WHEN vasco_goals < opponent_goals THEN 1
                ELSE 0
            END
        ) AS derrotas,
	SUM(vasco_goals) AS gols_marcados,
	SUM(opponent_goals) AS gols_sofridos
FROM
	vasco_matches
)
SELECT
	jogos,
	vitorias,
	empates,
	derrotas,
	gols_marcados,
	gols_sofridos,
	gols_marcados - gols_sofridos AS saldo_gols,
	(vitorias * 3 + empates) AS pontos,
	ROUND(
        (
            (vitorias * 3.0 + empates)
            / (jogos * 3)
        ) * 100,
        2
    ) AS aproveitamento_percentual
FROM
	retrospecto;

SELECT * FROM matches where match_id = 15512219;

SELECT
    match_id,
    match_date,
    tournament_name,
    home_team_name,
    home_score,
    away_score,
    away_team_name,
    status
FROM matches
WHERE
    EXTRACT(YEAR FROM match_date) = 2026
    AND 1974 IN (home_team_id, away_team_id)
    AND home_score = away_score
ORDER BY match_date;

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

-- TESTAR VIEW

SELECT
    *
FROM vw_vasco_matches
LIMIT 10;

SELECT
    match_id,
    match_date,
    opponent_team_name,
    vasco_score,
    opponent_score,
    vasco_penalties,
    opponent_penalties,
    result_normal_time,
    decided_on_penalties,
    result_final
FROM vw_vasco_matches
WHERE opponent_team_name ILIKE '%Volta Redonda%';

select count(*) from vw_vasco_matches where result_normal_time = 'WIN' and EXTRACT(
        YEAR FROM match_date
    ) = 2026;

select * from vw_vasco_matches where result_normal_time = 'DRAW' and EXTRACT(
        YEAR FROM match_date
    ) = 2026 --and tournament_name like '%Brasileirão Betano%';
	order by tournament_name;

select * from vw_vasco_matches where EXTRACT(
        YEAR FROM match_date
    ) = 2026

-- RETROSPECTO COMPLETO DO VASCO EM 2026

SELECT
    COUNT(*) AS matches,
    SUM(
        CASE
            WHEN result_normal_time = 'WIN'
            THEN 1
            ELSE 0
        END
    ) AS wins,
    SUM(
        CASE
            WHEN result_normal_time = 'DRAW'
            THEN 1
            ELSE 0
        END
    ) AS draws,
    SUM(
        CASE
            WHEN result_normal_time = 'LOSS'
            THEN 1
            ELSE 0
        END
    ) AS losses,
    SUM(vasco_score) AS goals_for,
    SUM(opponent_score) AS goals_against,
    SUM(vasco_score) - SUM(opponent_score) AS goal_difference
FROM vw_vasco_matches
WHERE
    EXTRACT(YEAR FROM match_date) = 2026 and status = 'finished';