-- Passo 1 — Confirmar que as views estão acessíveis
select * from matches;
SELECT * FROM matches LIMIT 10;
select * from matches where season_id = 87678 and (home_team_id = 1974 or away_team_id = 1974);
SELECT COUNT(*) FROM matches;
SELECT
    MAX(match_date) AS ultima_partida,
    COUNT(*) AS total_partidas
FROM matches;

select * from matches
where tournament_id = 325 and season_id = 87678 -- and home_team_id = 1974 and away_team_id = 1974
order by match_date desc;

DESCRIBE matches;

-- Passo 2 — Conferir a quantidade de dados

SELECT COUNT(*) AS total_matches FROM matches;

-- conferir rapidamente os outros datasets:

SELECT COUNT(*) AS total_teams
FROM teams;

SELECT COUNT(*) AS total_players
FROM players;

SELECT COUNT(*) AS total_lineups
FROM lineups;

SELECT COUNT(*) AS total_player_statistics
FROM player_statistics;

SELECT COUNT(*) AS total_statistics
FROM statistics;


-- Encontrar os jogos do Vasco
SELECT
    match_id,
    tournament_name,
    season_name,
    home_team_name,
    home_score,
    away_team_name,
    away_score,
    match_date,
--    to_timestamp(match_date / 1000) AS match_datetime,
    status,
    slug
FROM matches
WHERE
    home_team_id = 1974
    OR away_team_id = 1974
ORDER BY match_date DESC;

-- Filtrar os jogos do Vasco em 2026

SELECT
    match_id,
    tournament_name,
    season_name,
    home_team_name,
    home_score,
    away_team_name,
    away_score,
    match_date,
    status,
    slug
FROM matches
WHERE
    (
        home_team_id = 1974
        OR away_team_id = 1974
    )
    AND EXTRACT(
        YEAR FROM match_date
    ) = 2026
ORDER BY match_date;

-- Total de partidas do Vasco em 2026
SELECT
    COUNT(*) AS total_matches_vasco_2026
FROM matches
WHERE
    (
        home_team_id = 1974
        OR away_team_id = 1974
    )
    AND EXTRACT(
        YEAR FROM match_date
    ) = 2026;

select distinct country_name from players;

select count(*) from players;
select * from players;

-- Verificar a partida Olimpia x Vasco -> match_id = 16253383

SELECT *
FROM matches
WHERE match_id = 16253383;

-- Ver quais estatísticas temos para essa partida

SELECT * FROM statistics 
WHERE match_id = 16253383;

-- Ver a escalação

SELECT *
FROM lineups
WHERE match_id = 16253383
ORDER BY
    team_id,
    starter DESC,
    player_name;

-- Ver estatísticas individuais

SELECT *
FROM player_statistics
WHERE match_id = 16253383
LIMIT 50;

-- Estatísticas da partida

SELECT *
FROM statistics
WHERE match_id = 16253383;

-- Validar a estrutura completa das estatísticas dessa partida.

SELECT
    period,
    group_name,
    statistic_name,
    team_side,
    value,
    value_numeric
FROM statistics
WHERE match_id = 16253383
ORDER BY
    period,
    group_name,
    statistic_name,
    team_side;

SELECT
    period,
    COUNT(*) AS total_statistics
FROM statistics
WHERE match_id = 16253383
GROUP BY period
ORDER BY period;

-- Validar LINEUPS

SELECT
    match_id,
    team_id,
    player_id,
    player_name,
    starter,
    position,
    shirt_number,
    captain,
    formation
FROM lineups
WHERE match_id = 16253383
ORDER BY
    team_id,
    starter DESC,
    player_name;

SELECT
    team_id,
    COUNT(*) AS total_players,
    SUM(CASE WHEN starter THEN 1 ELSE 0 END) AS starters,
    SUM(CASE WHEN NOT starter THEN 1 ELSE 0 END) AS substitutes
FROM lineups
WHERE match_id = 16253383
GROUP BY team_id
ORDER BY team_id;

-- VALIDAR PLAYER STATISTICS

SELECT
    team_id,
    COUNT(DISTINCT player_id) AS total_players,
    COUNT(*) AS total_statistics
FROM player_statistics
WHERE match_id = 16253383
GROUP BY team_id
ORDER BY team_id;

SELECT
    team_id,
    player_id,
    MAX(player_name) AS player_name,
    COUNT(*) AS total_metrics
FROM player_statistics
WHERE match_id = 16253383
GROUP BY
    team_id,
    player_id
ORDER BY
    team_id,
    player_name;

-- player_statistics × lineups
-- Se retornar zero linhas, teremos confirmado que: Todo jogador que possui estatísticas individuais 
-- nessa partida também existe na escalação registrada para a mesma partida e para o mesmo time.

SELECT
    ps.match_id,
    ps.team_id,
    ps.player_id,
    ps.player_name
FROM player_statistics ps
LEFT JOIN lineups l
    ON ps.match_id = l.match_id
    AND ps.team_id = l.team_id
    AND ps.player_id = l.player_id
WHERE ps.match_id = 16253383
  AND l.player_id IS NULL
GROUP BY
    ps.match_id,
    ps.team_id,
    ps.player_id,
    ps.player_name;

-- validar os principais números individuais



---------------------

SELECT
    match_id,
    match_date,
    home_team_name,
    away_team_name,
    home_score,
    away_score,
    home_score_penalties,
    away_score_penalties,
    home_score_current,
    away_score_current
FROM matches
WHERE
	(
    	home_team_name ILIKE '%Vasco%'
    	AND away_team_name ILIKE '%Volta Redonda%'
	) OR
	(
    	home_team_name ILIKE '%Volta Redonda%'
    	AND away_team_name ILIKE '%Vasco%'
	);