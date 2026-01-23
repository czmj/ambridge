'use server'
import driver from '@/lib/neo4j';
import neo4j from 'neo4j-driver';

export async function getCharacterProfile(slug: string) {
  const session = driver.session();
  try {
    const result = await session.run(`
      MATCH (c:Character {slug: $slug})
      RETURN c
    `, { slug });

    if (result.records.length === 0) return null;
    const record = result.records[0];

    return {
      details: record.get('c').properties,
    };
  } finally {
    await session.close();
  }
}

export async function getTimeline({
  page = 1,
  pageSize = 10,
  sort = 'desc',
  slug,
}: {
  page?: number,
  pageSize?: number,
  sort?: 'asc' | 'desc',
  slug?: string,
} = {}) {
 const session = driver.session();
  const skip = (page - 1) * pageSize;
  const sortOrder = sort.toUpperCase() === 'ASC' ? 'ASC' : 'DESC';

  try {
    const cypher = `
      MATCH (e:Episode)
      ${slug ? 'MATCH (c:Character {slug: $slug})-[:APPEARS_IN]->(s:Scene)-[:PART_OF]->(e)' : ''}
      
      WITH count(DISTINCT e) AS totalCount
      
      MATCH (e:Episode)
      ${slug ? 'MATCH (target:Character {slug: $slug})-[:APPEARS_IN]->(s:Scene)-[:PART_OF]->(e)' : 'MATCH (s:Scene)-[:PART_OF]->(e)'}
      
      OPTIONAL MATCH (other:Character)-[:APPEARS_IN]->(s)
      ${slug ? 'WHERE other <> target' : ''}

      WITH e, totalCount, s, [x IN collect(DISTINCT {
        name: other.name,
        slug: other.slug
      }) WHERE x.slug IS NOT NULL] AS characters
      ORDER BY e.date ${sortOrder}, s.id ASC

      WITH e, totalCount, collect({
        sceneId: s.id,
        text: s.text,
        characters: characters
      }) AS scenes
      
      RETURN e.pid AS pid,
             e.date AS date,
             scenes,
             totalCount
      ORDER BY e.date ${sortOrder}
      SKIP $skip LIMIT $limit
    `;

    const result = await session.run(cypher, {
      slug,
      skip: neo4j.int(skip),
      limit: neo4j.int(pageSize)
    });

    if (result.records.length === 0) return { episodes: [], totalCount: 0 };

    const episodes = result.records.map(rec => ({
      pid: rec.get('pid'),
      date: rec.get('date').toString(),
      scenes: rec.get('scenes')
    }));

    const totalCount = result.records[0].get('totalCount').toNumber();

    return { episodes, totalCount };
  } finally {
    await session.close();
  }
}