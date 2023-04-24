const express = require('express');
const cors = require('cors');
const neo4j = require('neo4j-driver');
require('dotenv').config();


let user = process.env.DB_USER;
let password = process.env.DB_KEY;
let uri = process.env.DB_HOST;

const driver = neo4j.driver(uri, neo4j.auth.basic(user, password));
const session = driver.session();

const app = express();
const port = 7006;

app.use(cors());

app.use((req, res, next) => {
    if (req.query.access_token && req.query.access_token === process.env.ACCESS_TOKEN) {
        next()
    } else {
        res.sendStatus(401);
    }
});

app.use(express.json());

app.post('/sketchmapper', async (req, res) => {
    console.log(req.body);

    const buildingValues = req.body.filter(shape => shape.type === 'building').map(shape => {
        return {
            area: shape.area,
            compactness: shape.compactness,
            distance: shape.distance,
            azimuth: shape.azimuth
        }
    });

    const streetValues = req.body.filter(shape => shape.type === 'street').map(shape => {
        return {
            length: shape.length,
            distance: shape.distance,
            azimuth: shape.azimuth
        }
    });

    const vegetationValues = req.body.filter(shape => shape.type === 'vegetation').map(shape => {
        return {
            area: shape.area,
            compactness: shape.compactness,
            distance: shape.distance,
            azimuth: shape.azimuth
        }
    })

    let matchQuery = '';
    let callQuery = '';
    let diffQuery = '';

    if (streetValues.length > 0) {
        matchQuery += ', (p)<-[rs]-(s:Street)';
        callQuery += `
            call {
                with s_vals, s, rs
                unwind s_vals as val
                return
                (
                    min(abs(s.length - val.length) / val.length) +
                    min(abs(rs.distance - val.distance) / val.distance) +
                    min(abs(rs.azimuth - val.azimuth) / val.azimuth)
                ) / 3 as diff_streets
            }
        `;
        diffQuery += ' + diff_streets';
    }

    if (vegetationValues.length > 0) {
        matchQuery += ', (p)<-[rv]-(v:Vegetation)';
        callQuery += `
            call {
                with v_vals, v, rv
                unwind v_vals as val
                return
                (
                    min(abs(v.area - val.area) / val.area) +
                    min(abs(v.compactness - val.compactness) / val.compactness) +
                    min(abs(rv.distance - val.distance) / val.distance) +
                    min(abs(rv.azimuth - val.azimuth) / val.azimuth)
                ) / 4 as diff_vegetation
            }
        `;
        diffQuery += ' + diff_vegetation';
    }

    const result = await session.run(
        `
            with
            $buildingValues as b_vals,
            $streetValues as s_vals,
            $vegetationValues as v_vals
            match (p:Point)<-[rb]-(b:Building) ${matchQuery}
            call {
                with b_vals, b, rb
                unwind b_vals as val
                return
                (
                    min(abs(b.area - val.area) / val.area) +
                    min(abs(b.compactness - val.compactness) / val.compactness) +
                    min(abs(rb.distance - val.distance) / val.distance) +
                    min(abs(rb.azimuth - val.azimuth) / val.azimuth)
                ) / 4 as diff_buildings
            }
            ${callQuery}
            return [p.centroid.x, p.centroid.y] as coords, avg(diff_buildings${diffQuery}) as diff_total order by diff_total limit 10
        `,
        {
            buildingValues: buildingValues,
            streetValues: streetValues,
            vegetationValues: vegetationValues
        }
    )
    res.json(result.records.map(record => record.get('coords')))
})

app.listen(port, () => {
    console.log(`Server running on port ${port}`)
})
