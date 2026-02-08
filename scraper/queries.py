CHECK_DB_EXISTS = "MATCH (n) RETURN true LIMIT 1"

ADD_EPISODES_WITH_SCENES = """
UNWIND $batch AS ep
MERGE (e:Episode {pid: ep.pid})
ON CREATE SET e.date = date(ep.date),
            e.synopsis = ep.synopsis

WITH e, ep
UNWIND ep.scenes AS scene_data
MERGE (s:Scene {id: scene_data.sid})
SET s.order = scene_data.index,
    s.text = scene_data.text
MERGE (s)-[:PART_OF]->(e)
"""

CLEANUP_ORPHANS = """
MATCH (e:Episode)
WHERE (e.synopsis CONTAINS "The week's events in Ambridge"
OR e.synopsis CONTAINS "Contemporary drama in a rural setting")
AND NOT (e)<-[:PART_OF]-(:Scene)
DETACH DELETE e RETURN count(*) as count"""

CLEANUP_EXACT_DUPLICATES = """
MATCH (s:Scene)-[:PART_OF]->(e:Episode)
WITH e, e.synopsis as syn, s.text as txt ORDER BY e.date, s.id
WITH e, syn, collect(txt) as seq ORDER BY e.date, e.pid
WITH syn, seq, collect(e) as eps WHERE size(eps) > 1
UNWIND eps[1..] as d
OPTIONAL MATCH (ds:Scene)-[:PART_OF]->(d)
DETACH DELETE d, ds RETURN count(d) as count"""

CLEANUP_THIN_REPEATS = """
MATCH (s:Scene)-[:PART_OF]->(e:Episode)
WITH e, e.date as d, count(s) as c ORDER BY d DESC, c DESC
WITH d, collect({n: e, c: c}) as list WHERE size(list) = 2 AND list[0].c > 1 AND list[1].c = 1
WITH list[1].n as d
OPTIONAL MATCH (ds:Scene)-[:PART_OF]->(d)
DETACH DELETE d, ds RETURN count(d) as count"""

CLEANUP_DATE_SHIFTS = """
MATCH (e:Episode)
WITH e.date as cur, collect(e) as list WHERE size(list) = 2
OPTIONAL MATCH (y:Episode) WHERE y.date = cur - duration({days: 1})
WITH cur, list, y WHERE y IS NULL

// Calculate target date and check it isn't Saturday (6)
WITH list[1] as target, cur, (cur - duration({days: 1})) as newDate
WHERE newDate.dayOfWeek <> 6

SET target.date = newDate
RETURN count(target) as count"""

LINK_SHARED_TERMS_PREAMBLE = """
MATCH (c0:Character)
UNWIND (coalesce(c0.aliases, []) + [c0.name]) AS term
WITH term, count(c0) AS usage_count
WHERE usage_count > 1
WITH collect(DISTINCT term) AS shared_terms
"""

LINK_PASS1_BODY = """
// Find unambiguous characters and build regex from names + aliases
MATCH (c:Character)
WITH c, shared_terms, (coalesce(c.aliases, []) + [c.name]) AS terms
WHERE NONE(term IN terms WHERE term IN shared_terms)
WITH c, '.*\\\\b(' + reduce(s = '', t IN terms |
    CASE WHEN s = '' THEN t ELSE s + '|' + t END
) + ')\\\\b.*' AS regex

MATCH (s:Scene)-[:PART_OF]->(e:Episode)
WHERE s.text =~ regex
  {pid_filter}
  AND (c.dob IS NULL OR e.date >= c.dob)
  AND (c.dod IS NULL OR e.date <= c.dod)
  AND (c.first_appearance IS NULL OR e.date >= c.first_appearance)
  AND (c.last_appearance IS NULL OR e.date <= c.last_appearance)
MERGE (c)-[:APPEARS_IN]->(s)
"""

LINK_PASS2_BODY = """
// Find ambiguous characters and build regex from names + aliases
MATCH (c:Character)
WITH c, shared_terms, (coalesce(c.aliases, []) + [c.name]) AS terms
WHERE ANY(term IN terms WHERE term IN shared_terms)
WITH c, '.*\\\\b(' + reduce(s = '', t IN terms |
    CASE WHEN s = '' THEN t ELSE s + '|' + t END
) + ')\\\\b.*' AS regex

MATCH (s:Scene)-[:PART_OF]->(e:Episode)
WHERE s.text =~ regex
  {pid_filter}

// Check if character is temporally active (alive, within appearance range)
// Keep inactive characters as rivals to prevent incorrect fallback
WITH s, c, e,
    CASE
        WHEN (c.dob IS NOT NULL AND e.date < c.dob) THEN false
        WHEN (c.dod IS NOT NULL AND e.date > c.dod) THEN false
        WHEN (c.first_appearance IS NOT NULL AND e.date < c.first_appearance) THEN false
        WHEN (c.last_appearance IS NOT NULL AND e.date > c.last_appearance) THEN false
        ELSE true
    END AS temporally_active

// Check if character's full name appears anywhere in this episode
WITH s, c, e, temporally_active,
    EXISTS {{
        MATCH (other_scene:Scene)-[:PART_OF]->(e)
        WHERE other_scene.text CONTAINS c.name
    }} AS full_name_in_episode

// Count close family (spouse, parent, child, sibling) in scene - weight 3
OPTIONAL MATCH (s)<-[:APPEARS_IN]-(closeRelative:Character)
WHERE (c)-[:SPOUSE|ROMANTIC_RELATIONSHIP]-(closeRelative)
   OR (c)-[:CHILD_OF]->(closeRelative)
   OR (closeRelative)-[:CHILD_OF]->(c)
   OR (c)-[:CHILD_OF]->(:Character)<-[:CHILD_OF]-(closeRelative)

WITH s, c, e, temporally_active, full_name_in_episode, count(DISTINCT closeRelative) AS close_family

// Count grandparents/grandchildren in scene - weight 1
OPTIONAL MATCH (s)<-[:APPEARS_IN]-(distantRelative:Character)
WHERE (c)-[:CHILD_OF*2]->(distantRelative)
   OR (distantRelative)-[:CHILD_OF*2]->(c)

WITH s, c, e, temporally_active, full_name_in_episode, close_family, count(DISTINCT distantRelative) AS distant_family

// Count friends in scene - weight 2
OPTIONAL MATCH (s)<-[:APPEARS_IN]-(friend:Character)
WHERE (c)-[:FRIEND_OF]-(friend)

WITH s, c, e, temporally_active, full_name_in_episode, close_family, distant_family, count(DISTINCT friend) AS friends

// Count co-habitants/co-workers in scene - weight 2
OPTIONAL MATCH (s)<-[:APPEARS_IN]-(cohabitant:Character)
WHERE EXISTS {{
    MATCH (c)-[r1:LIVES_AT|WORKS_AT]->(loc:Location)<-[r2:LIVES_AT|WORKS_AT]-(cohabitant)
    WHERE (r1.from IS NULL OR r1.from <= e.date) AND (r1.to IS NULL OR r1.to >= e.date)
      AND (r2.from IS NULL OR r2.from <= e.date) AND (r2.to IS NULL OR r2.to >= e.date)
}}

WITH s, c, e, temporally_active, full_name_in_episode, close_family, distant_family, friends,
    count(DISTINCT cohabitant) AS cohabitant_count

// Contextual keyword scoring - count matched keywords, each worth 2 points
WITH s, c, e, temporally_active, full_name_in_episode, close_family, distant_family, friends, cohabitant_count,
    CASE
        WHEN c.keywords IS NOT NULL
        THEN reduce(score = 0, kw IN c.keywords |
            score + CASE WHEN s.text =~ ('.*\\\\b' + kw + '\\\\b.*') THEN 2 ELSE 0 END
        )
        ELSE 0
    END AS keyword_score

// Score each candidate and flag definite matches
WITH s, c, e, temporally_active,
    (close_family * 3) + (cohabitant_count * 2) + (friends * 2) + distant_family + keyword_score AS total_score,
    CASE
        WHEN s.text CONTAINS c.name THEN true
        WHEN full_name_in_episode THEN true
        WHEN e.date = c.dob OR e.date = c.dod THEN true
        ELSE false
    END AS definite_match

// Collect all candidates per scene and pick the best match for each alias group
WITH s, e, collect({{
    character: c,
    score: total_score,
    definite: definite_match,
    active: temporally_active,
    aliases: coalesce(c.aliases, []),
    full_name: c.name
}}) AS candidates

UNWIND candidates AS cand
WITH s, e, cand, candidates, cand.character AS character,
    [rival IN candidates
     WHERE rival.character <> cand.character
     AND ANY(a IN rival.aliases WHERE a IN cand.aliases)] AS rivals

// Check if any rival's full name appears anywhere in this episode
WITH s, e, cand, character, candidates, rivals,
    ANY(rival IN rivals WHERE
        EXISTS {{
            MATCH (other_scene:Scene)-[:PART_OF]->(e)
            WHERE other_scene.text CONTAINS rival.full_name
        }}
    ) AS rival_full_name_present

// Check for memorial keywords + deceased rival (exclude living candidates)
WITH s, e, cand, character, rivals, rival_full_name_present,
    EXISTS {{
        MATCH (other_scene:Scene)-[:PART_OF]->(e)
        WHERE other_scene.text =~ '.*\\\\b(death|died|funeral|memorial|footsteps|passed away|loss of|mourning)\\\\b.*'
    }} AS has_memorial_keywords,
    ANY(rival IN rivals WHERE
        rival.character.dod IS NOT NULL
    ) AS has_deceased_rival,
    ANY(rival IN rivals WHERE
        rival.character.dod IS NOT NULL
        AND e.date = rival.character.dod
    ) AS is_rival_death_episode

WITH s, cand, character, rivals, rival_full_name_present,
    ((has_memorial_keywords AND has_deceased_rival) OR is_rival_death_episode)
    AND cand.active AS excluded_by_memorial

WHERE cand.active  // Only link temporally active characters
  AND NOT rival_full_name_present  // Exclude if rival's full name present
  AND NOT excluded_by_memorial  // Exclude living candidates when discussing deceased rivals
  AND (cand.definite
       OR size(rivals) = 0  // Only candidate for this alias - always match
       OR (cand.score >= 1  // Multiple candidates - require score >= 1 and be highest
           AND NONE(r IN rivals WHERE r.score >= cand.score)))
MERGE (character)-[:APPEARS_IN]->(s)
"""

MANUAL_LINK_CHARACTER = """
MATCH (c:Character {name: $char_name})
UNWIND $scene_ids AS s_id
MATCH (s:Scene {id: s_id})
MERGE (c)-[r:APPEARS_IN]->(s)
RETURN count(r) AS links_created
"""

FIND_EMPTY_SCENES = """
MATCH (e:Episode)<-[:PART_OF]-(empty:Scene)
WHERE NOT (empty)<-[:APPEARS_IN]-(:Character)
MATCH (target:Scene)-[:PART_OF]->(e)
WHERE target.order = empty.order - 1
RETURN empty.id AS empty_id, empty.text AS empty_text,
    target.id AS target_id, target.text AS target_text,
    e.pid AS episode_pid
ORDER BY empty.id ASC
"""

MERGE_SCENES = """
MATCH (target:Scene {id: $target_id})
MATCH (empty:Scene {id: $empty_id})
SET target.text = target.text + " " + empty.text
DETACH DELETE empty
"""

FIND_SINGLE_SCENE_EPISODES = """
MATCH (s:Scene)-[:PART_OF]->(e:Episode)
WHERE e.date >= date() - duration({days: 7})
WITH e, count(s) AS scene_count
WHERE scene_count = 1
RETURN e.pid AS pid
"""

DELETE_EPISODES = """
MATCH (e:Episode)
WHERE e.pid IN $pids
OPTIONAL MATCH (s:Scene)-[:PART_OF]->(e)
DETACH DELETE s, e
RETURN count(e) AS count
"""
