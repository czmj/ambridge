"use server";
import driver from "@/lib/neo4j";
import { FamilyDatum } from "@/components/FamilyTree";
import neo4j from "neo4j-driver";

async function executeQuery(cypher: string, params = {}) {
  const session = driver.session();
  try {
    const result = await session.executeRead((tx) => tx.run(cypher, params));
    return result.records.map((record) => record.toObject());
  } catch (error) {
    console.error("Cypher Execution Error:", error);
    throw error;
  } finally {
    await session.close();
  }
}

export async function getCharacterProfile(slug: string) {
  const cypher = `
    MATCH (c:Character {slug: $slug})
    RETURN c { .* } AS profile
  `;

  const result = await executeQuery(cypher, { slug });
  return result[0]?.profile || null;
}

export async function getTimeline({
  page = 1,
  pageSize = 10,
  sort = "desc",
  slug,
}: {
  page?: number;
  pageSize?: number;
  sort?: "asc" | "desc";
  slug?: string;
} = {}) {
  const skip = (page - 1) * pageSize;
  const sortOrder = sort.toUpperCase() === "ASC" ? "ASC" : "DESC";

  const countCypher = `
    MATCH (e:Episode)<-[:PART_OF]-(s:Scene)
      ${slug ? "MATCH (:Character {slug: $slug})-[:APPEARS_IN]->(s)" : ""}
    RETURN count(DISTINCT e) AS totalCount
  `;

  const dataCypher = `
      MATCH (e:Episode)
      ${slug ? "MATCH (c:Character {slug: $slug})-[:APPEARS_IN]->(s:Scene)-[:PART_OF]->(e)" : ""}
            
      MATCH (e:Episode)
      ${slug ? "MATCH (target:Character {slug: $slug})-[:APPEARS_IN]->(s:Scene)-[:PART_OF]->(e)" : "MATCH (s:Scene)-[:PART_OF]->(e)"}
      
      OPTIONAL MATCH (other:Character)-[:APPEARS_IN]->(s)
      ${slug ? "WHERE other <> target" : ""}

      WITH e, s, [x IN collect(DISTINCT {
        name: other.name,
        slug: other.slug
      }) WHERE x.slug IS NOT NULL] AS characters
      ORDER BY e.date ${sortOrder}, s.id ASC

      WITH e, collect({
        sceneId: s.id,
        text: s.text,
        characters: characters
      }) AS scenes
      
      RETURN e.pid AS pid,
             e.date AS date,
             scenes
      ORDER BY e.date ${sortOrder}
      SKIP $skip LIMIT $limit
    `;

  const [countRes, dataRes] = await Promise.all([
    executeQuery(countCypher, { slug }),
    executeQuery(dataCypher, {
      slug,
      skip: neo4j.int(skip),
      limit: neo4j.int(pageSize),
    }),
  ]);

  return {
    totalCount: countRes[0]?.totalCount.toNumber() || 0,
    episodes: dataRes.map((rec) => ({
      pid: rec.pid,
      date: rec.date.toString(),
      scenes: rec.scenes,
    })),
  };
}

export async function getFamilyTree(
  slug: string,
): Promise<FamilyDatum[] | null> {
  const cypher = `
    MATCH (c:Character {slug: $slug})

    CALL (c) { OPTIONAL MATCH (c)-[:(CHILD_OF|SPOUSE)*1..3]-(p:Character) WHERE p <> c RETURN collect(DISTINCT p) AS relations }

    WITH relations + [c] AS allRaw
    UNWIND allRaw AS person
    WITH collect(DISTINCT person) AS people

    UNWIND people AS p
    CALL (p, people) { OPTIONAL MATCH (p)-[:CHILD_OF]->(parent:Character)
           WHERE parent IN people RETURN collect(parent.slug) AS parentSlugs }
    CALL (p, people) { 
          OPTIONAL MATCH (p)-[r:SPOUSE]-(spouse:Character)
           WHERE spouse IN people 
            RETURN 
              collect(DISTINCT spouse.slug) AS spouseSlugs,
               collect(DISTINCT {slug: spouse.slug, status: r.status}) AS spouseDetails }                                                                                                
    CALL (p, people, spouseSlugs) { OPTIONAL MATCH (child:Character)-[:CHILD_OF]->(p)                                                                                         
            OPTIONAL MATCH (child)-[:CHILD_OF]->(coparent:Character)                                                                                                           
            WHERE coparent IN people AND coparent <> p AND NOT coparent.slug IN spouseSlugs                                                                                    
            RETURN [x IN collect(DISTINCT coparent.slug) | {slug: x, status: 'coparent'}]   as coparentDetails}
    CALL (p, people) { OPTIONAL MATCH (child:Character)-[:CHILD_OF]->(p)
           WHERE child IN people RETURN collect(child.slug) AS childSlugs }

    RETURN p { .name, .slug, .dob, .dod, .gender } AS person,
           parentSlugs, 
           spouseSlugs AS partnerSlugs, 
           spouseDetails + coparentDetails AS partnerDetails,
           childSlugs
  `;

  const results = await executeQuery(cypher, { slug });

  if (results.length <= 1) return null;

  const sortedResults = [
    ...results.filter(({ person }) => person.slug === slug),
    ...results.filter(({ person }) => person.slug !== slug),
  ];

  return sortedResults.map((row) => {
    return {
      id: row.person.slug,
      data: {
        name: row.person.name,
        gender: (row.person.gender.toLowerCase() === "female" ? "F" : "M") as
          | "M"
          | "F",
        dob: row.person.dob?.year?.toString(),
        dod: row.person.dod?.year?.toString(),
        partnerStatuses: Object.fromEntries(
          row.partnerDetails.map((detail: { slug: string; status: string }) => [
            detail.slug,
            detail.status,
          ]),
        ),
      },
      rels: {
        parents: row.parentSlugs,
        spouses: row.partnerSlugs,
        children: row.childSlugs,
      },
    };
  });
}

export async function getEpisodeByDate(date: string) {
  const cypher = `
    MATCH (e:Episode {date: date($date)})
    MATCH (s:Scene)-[:PART_OF]->(e)
    OPTIONAL MATCH (c:Character)-[:APPEARS_IN]->(s)
    
    WITH e, s, collect(DISTINCT {
      name: c.name,
      slug: c.slug
    }) AS characters
    ORDER BY s.id ASC

    RETURN e.pid AS pid,
           e.date AS date,
           e.synopsis AS synopsis,
           collect({
             sceneId: s.id,
             text: s.text,
             characters: [char IN characters WHERE char.slug IS NOT NULL]
           }) AS scenes
    LIMIT 1
  `;

  const result = await executeQuery(cypher, { date });

  if (!result[0]) return null;

  return result[0];
}
