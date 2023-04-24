import psycopg
from psycopg.rows import dict_row
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def write_buildings(tx, buildings):
    tx.run("""
        UNWIND $buildings as b
        CREATE (:Building {osm_id: b.osm_id, floors: b.floors, shape: b.shape, compactness: b.compactness, corners: b.corners, area: b.area, centroid: point({x: b.x, y: b.y, srid: 4326})})
        """,
           buildings=buildings)

def write_streets(tx, streets):
    tx.run("""
        UNWIND $streets as s
        CREATE (:Street {osm_id: s.osm_id, curvature: s.curvature, length: s.length, nodes: s.nodes, centroid: point({x: s.x, y: s.y, srid: 4326})})
        """,
           streets=streets)

def write_vegetation(tx, vegetation):
    tx.run("""
        UNWIND $vegetation as v
        CREATE (:Vegetation {osm_id: v.osm_id, shape: v.shape, compactness: v.compactness, corners: v.corners, area: v.area, centroid: point({x: v.x, y: v.y, srid: 4326})})
        """,
           vegetation=vegetation)

def write_points(tx, points):
    tx.run("""
        UNWIND $points as p
        MERGE (point:Point {idx: p.idx})
        ON CREATE SET point.centroid = point({x: p.x, y: p.y, srid: 4326})
        WITH point, p
        MATCH (b:Building|Street|Vegetation {osm_id: p.osm_id})
        CREATE (b)-[:IS_NEIGHBOR_OF {distance: p.distance, azimuth: p.azimuth}]->(point)
    """,
        points=points)

with GraphDatabase.driver(os.getenv('NEO4J_HOST'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))) as driver:
    with driver.session(database="neo4j") as session:

        with psycopg.connect(os.getenv('PG_CONNECTION')) as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute("""
                    SELECT osm_id, floors, shape, compactness, corners, ST_Area(geom) AS area, ST_X(centroid::geometry) AS x, ST_Y(centroid::geometry) AS y FROM buildings
                """)

                result = cursor.fetchall()
                print(result)
                session.execute_write(write_buildings, result)

                cursor.execute("""
                    SELECT osm_id, curvature, length, nodes, ST_Area(geom) AS area, ST_X(centroid::geometry) AS x, ST_Y(centroid::geometry) AS y FROM streets
                """)

                result = cursor.fetchall()
                print(result)
                session.execute_write(write_streets, result)

                cursor.execute("""
                    SELECT osm_id, shape, compactness, corners, ST_X(centroid::geometry) AS x, ST_Y(centroid::geometry) AS y FROM vegetation
                """)

                result = cursor.fetchall()
                print(result)
                session.execute_write(write_vegetation, result)

                cursor.execute("""
                    SELECT p.idx, b.osm_id, ST_Length(ST_ShortestLine(p.centroid::geometry, b.geom::geometry)::geography) as distance, ST_Azimuth(p.centroid, b.centroid) as azimuth, ST_X(p.centroid::geometry) AS x, ST_Y(p.centroid::geometry) AS y
                    FROM points p
                    LEFT JOIN buildings b ON ST_DWithin(p.centroid, b.geom, 50)
                    UNION ALL
                    SELECT p.idx, b.osm_id, ST_Length(ST_ShortestLine(p.centroid::geometry, b.geom::geometry)::geography) as distance, ST_Azimuth(p.centroid, b.centroid) as azimuth, ST_X(p.centroid::geometry) AS x, ST_Y(p.centroid::geometry) AS y
                    FROM points p
                    LEFT JOIN streets b ON ST_DWithin(p.centroid, b.geom, 50)
                    UNION ALL
                    SELECT p.idx, b.osm_id, ST_Length(ST_ShortestLine(p.centroid::geometry, b.geom::geometry)::geography) as distance, ST_Azimuth(p.centroid, b.centroid) as azimuth, ST_X(p.centroid::geometry) AS x, ST_Y(p.centroid::geometry) AS y
                    FROM points p
                    LEFT JOIN vegetation b ON ST_DWithin(p.centroid, b.geom, 50)
                """)

                result = cursor.fetchall()
                print(result)
                session.execute_write(write_points, result)
