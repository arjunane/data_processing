﻿-- TESTS:
-- Select all tables with OSM in public
SELECT     *
FROM     information_schema.tables
WHERE     table_schema = 'public'
    AND table_name LIKE 'osm_%';

-- Select all tables with OSM in public
SELECT     * 
FROM     pg_tables
WHERE     schemaname='public'
    AND tablename LIKE 'osm_%';

-- Select all indexes with OSM in public
SELECT     * 
FROM     pg_indexes
WHERE     schemaname='public'
    AND tablename LIKE 'osm_%'
    AND indexname LIKE '%_pkey';

-- Select all indexes with OSM in public
SELECT     * 
FROM     pg_indexes
WHERE     schemaname='openstreetmap'
    AND tablename LIKE 'osm_%'
    AND indexname LIKE '%_pkey';

-- 0. Create new schema
CREATE SCHEMA openstreetmap;

-- 1. Move all tables to new schema
DO
$$
DECLARE
    row record;
BEGIN
    FOR row IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'osm_%'
    LOOP
        EXECUTE 'ALTER TABLE public.' || quote_ident(row.tablename) || ' SET SCHEMA openstreetmap;';
    END LOOP;
END;
$$;

-- 2. Remove all wrong 'pkey' indexes (_line, _point, _polygon, _roads)
DO
$$
DECLARE
    row record;
BEGIN
    FOR row IN SELECT indexname FROM pg_indexes 
    WHERE (schemaname='openstreetmap' 
    AND indexname LIKE '%_pkey')
    AND (tablename LIKE '%_line'
    OR tablename LIKE '%_point'
    OR tablename LIKE '%_polygon'
    OR tablename LIKE '%_roads')
    LOOP
        EXECUTE 'DROP INDEX openstreetmap.' || quote_ident(row.indexname) || ';';
    END LOOP;
END;
$$;

-- 3. Add column 'gid' serial
-- 4. Add primary keys
-- 5. Rename geo-column 'way' to 'geom'
DO
$$
DECLARE
    row record;
BEGIN
    FOR row IN SELECT tablename FROM pg_tables 
    WHERE schemaname='openstreetmap' 
    AND (tablename LIKE '%_line'
    OR tablename LIKE '%_point'
    OR tablename LIKE '%_polygon'
    OR tablename LIKE '%_roads')
    LOOP
        EXECUTE 'ALTER TABLE openstreetmap.' || quote_ident(row.tablename) || ' ADD gid SERIAL;';
        EXECUTE 'ALTER TABLE openstreetmap.' || quote_ident(row.tablename) || ' ADD PRIMARY KEY (gid);';
        EXECUTE 'ALTER TABLE openstreetmap.' || quote_ident(row.tablename) || ' RENAME COLUMN way TO geom;';
    END LOOP;
END;
$$;

-- 6. Set geometry and SRID

ALTER TABLE openstreetmap.osm_deu_line
    ALTER COLUMN geom TYPE geometry(LineString,3857) 
        USING ST_SetSRID(geom,3857);

ALTER TABLE openstreetmap.osm_deu_point
    ALTER COLUMN geom TYPE geometry(Point,3857) 
        USING ST_SetSRID(geom,3857);

ALTER TABLE openstreetmap.osm_deu_polygon
    ALTER COLUMN geom TYPE geometry(MultiPolygon, 3857) 
        USING ST_SetSRID(ST_MULTI(geom),3857);

ALTER TABLE openstreetmap.osm_deu_roads
    ALTER COLUMN geom TYPE geometry(LineString,3857) 
        USING ST_SetSRID(geom,3857);

-- 7. Add indexes GIST (geom) and GIN (tags)
DO
$$
DECLARE
    row record;
BEGIN
    FOR row IN SELECT tablename FROM pg_tables 
    WHERE schemaname='openstreetmap' 
    AND (tablename LIKE '%_line'
    OR tablename LIKE '%_point'
    OR tablename LIKE '%_polygon'
    OR tablename LIKE '%_roads')
    LOOP
        EXECUTE 'CREATE INDEX ' || quote_ident(row.tablename) || '_geom_idx ON openstreetmap.' || quote_ident(row.tablename) || ' USING gist (geom);';
    END LOOP;
END;
$$;

-- EXECUTE 'CREATE INDEX ' || quote_ident(row.tablename) || '_tags_idx ON openstreetmap.' || quote_ident(row.tablename) || ' USING GIN (tags);';