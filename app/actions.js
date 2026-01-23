'use server'
import neo4j from 'neo4j-driver';
import driver from '@/lib/neo4j';

export async function getCharacterProfile(slug) {
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

export async function getCharacterTimeline(slug, page = 1, pageSize = 10) {
  const session = driver.session();
  const skip = (page - 1) * pageSize;
  
  try {
    const result = await session.run(`
      // 1. Find the target character and their episodes
      MATCH (c:Character {slug: $slug})-[:APPEARS_IN]->(s:Scene)-[:PART_OF]->(e:Episode)
      
      // 2. Count total distinct episodes for pagination metadata
      WITH c, count(DISTINCT e) AS totalCount
      
      // 3. Match the episodes again to get data for the current page
      MATCH (c)-[:APPEARS_IN]->(s:Scene)-[:PART_OF]->(e:Episode)
      
      // 4. Get other characters in those scenes
      OPTIONAL MATCH (other:Character)-[:APPEARS_IN]->(s)
      WHERE other <> c

      // 5. Group by episode and collect scenes
      WITH e, totalCount, s, collect(DISTINCT {
        name: other.name,
        slug: other.slug
      }) AS others
      ORDER BY e.date DESC, s.id ASC 

      WITH e, totalCount, collect({
        sceneId: s.id,
        text: s.text,
        characters: others
      }) AS scenes
      
      // 6. Return paginated results
      RETURN e.pid AS episodePid,
             e.date AS date,
             scenes,
             totalCount
      ORDER BY e.date DESC
      SKIP $skip LIMIT $limit
    `, { 
      slug, 
      skip: neo4j.int(skip), 
      limit: neo4j.int(pageSize) 
    });

    if (result.records.length === 0) return { episodes: [], totalCount: 0 };

    const episodes = result.records.map(rec => ({
      episodePid: rec.get('episodePid'),
      date: rec.get('date').toString(),
      scenes: rec.get('scenes')
    }));

    // totalCount is the same for every row in this result set
    const totalCount = result.records[0].get('totalCount').toNumber();

    return { episodes, totalCount };
  } finally {
    await session.close();
  }
}

export async function getMasterTimeline(page = 1, pageSize = 10) {
  const session = driver.session();
  const skip = (page - 1) * pageSize;
  
  try {
    const result = await session.run(`
      // 1. Get total episode count for pagination
      MATCH (e:Episode)
      WITH count(e) AS totalCount

      // 2. Fetch episodes with their scenes and characters
      MATCH (e:Episode)
      MATCH (s:Scene)-[:PART_OF]->(e)
      MATCH (c:Character)-[:APPEARS_IN]->(s)

      WITH e, totalCount, s, collect({
        name: c.name,
        slug: c.slug
      }) AS characters
      ORDER BY e.date DESC, s.id ASC

      // 3. Group scenes by episode
      WITH e, totalCount, collect({
        sceneId: s.id,
        text: s.text,
        characters: characters
      }) AS scenes
      
      RETURN e.pid AS episodePid,
             e.date AS date,
             scenes,
             totalCount
      ORDER BY e.date DESC
      SKIP $skip LIMIT $limit
    `, { 
      skip: neo4j.int(skip), 
      limit: neo4j.int(pageSize) 
    });

    const episodes = result.records.map(rec => ({
      episodePid: rec.get('episodePid'),
      date: rec.get('date').toString(),
      scenes: rec.get('scenes'),
      totalCount: rec.get('totalCount').toNumber()
    }));

    return { 
      episodes, 
      totalCount: episodes[0]?.totalCount || 0 
    };
  } finally {
    await session.close();
  }
}