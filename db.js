import neo4j from 'neo4j-driver';

const driver = neo4j.driver(
    'neo4j+s://df6f46e8.databases.neo4j.io',
    neo4j.auth.basic('neo4j', 'GrFPX0A9rfqeWZgJY-GNygpTSESYCI8yobmy2QUI_QA')
);

export async function saveToNeo4j(structuredData) {
    const session = driver.session({ database: 'neo4j' });
    
    try {
        const result = await session.run(
            `
            MERGE (u:User {user_id: $user_id})
            CREATE (o:Observation {
                timestamp: datetime($timestamp),
                interaction_duration_sec: $interaction_duration_sec,
                location_type: $location_type
            })
            CREATE (u)-[:MADE_OBSERVATION]->(o)
            
            WITH o
            UNWIND $objects AS obj
            MERGE (ob:Object {name: obj})
            CREATE (o)-[:OBSERVED]->(ob)
            
            WITH o
            CREATE (v:Vision {
                approx_model: $approx_model,
                color: $color,
                confidence: $confidence
            })
            CREATE (o)-[:HAS_VISION]->(v)
            
            WITH o
            CREATE (vid:Video {
                intent: $intent,
                keywords: $keywords,
                sentiment: $sentiment
            })
            CREATE (o)-[:HAS_VIDEO]->(vid)
            
            RETURN o
            `,
            {
                user_id: structuredData.user_id,
                timestamp: structuredData.timestamp,
                interaction_duration_sec: structuredData.context.interaction_duration_sec,
                location_type: structuredData.context.location_type,
                objects: structuredData.vision.objects,
                approx_model: structuredData.vision.approx_model || 'unknown',
                color: structuredData.vision.color || 'unknown',
                confidence: structuredData.vision.confidence,
                intent: structuredData.video.intent,
                keywords: structuredData.video.keywords,
                sentiment: structuredData.video.sentiment
            }
        );
        
        console.log('✅ Data saved to Neo4j:', result.records.length, 'records created');
        return { success: true, records: result.records.length };
        
    } catch (error) {
        console.error('❌ Neo4j save error:', error);
        throw error;
    } finally {
        await session.close();
    }
}

export async function closeDriver() {
    await driver.close();
}