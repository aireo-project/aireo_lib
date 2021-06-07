# The stac item extension for the GeoreferencedEODataCube profile
# 

from pydantic import BaseModel
from stac_pydantic import Extensions, Item

class GeoreferencedEODataCubeModel(BaseModel):
    dimensions: dict


if __name__ == '__main__':
    from stac_pydantic import validate_item
    Extensions.register('georeferenced_eo_datacube', GeoreferencedEODataCubeModel)
    geo_eocube_img_metadata_aoi_d = \
        {
            "type": "Feature",
            "stac_extensions": ["georeferenced_eo_datacube"],
            "stac_version": "1.0.0-beta.2",
            "id": "20201211_223832_CS2",

            "bbox": [
                172.91173669923782,
                1.3438851951615003,
                172.95469614953714,
                1.3690476620161975
            ],
            "geometry": {"type": "Polygon",
            "coordinates": [[[172.91173669923782, 1.3438851951615003],
                [172.95469614953714, 1.3438851951615003],
                [172.95469614953714, 1.3690476620161975],
                [172.91173669923782, 1.3690476620161975],
                [172.91173669923782, 1.3438851951615003]]]},

            "properties": {
                "title": "EODatacube profile",
                "description": "A sample STAC Item pulling data from EODataCUbe ",
                "datetime": "2020-12-11T22:38:32.125Z",
                "dimensions":{
                    "x": {
                        "type": "spatial",
                        "axis": "x",
                        "extent": [
                            -180,
                            180
                        ],
                        "values": [
                        172.91173669923782,
                        172.95469614953714
                        ],
                        "reference_system": 4326
                    },
                    "y": {
                        "type": "spatial",
                        "axis": "y",
                        "extent": [
                            -90, 
                            90
                        ],
                        "values": [
                        1.3438851951615003,
                        1.3690476620161975
                        ],
                        "reference_system": 4326
                    },
                    "metered_levels": {
                        "type": "spatial",
                        "axis": "z",
                        "values": [
                        ],
                        "unit": "m"
                    },
                    "time": {
                        "type": "temporal",
                        "values": [
                        "2020-12-11T22:38:32.125Z"
                        ]
                    },
                    "spectral": {
                        "type": "bands",
                        "values": [
                        "red",
                        "green",
                        "blue",
                        "NIR",
                        "SWIR"
                        ]
                    }
                }
            },
            "links": [{"rel": "root",
            "href": "../EO_TDS.json",
            "type": "application/json"}],
            
            "assets":{}
        }
        

    geo_eocube_img_metadata_aoi = Item(**geo_eocube_img_metadata_aoi_d)

    print(validate_item(geo_eocube_img_metadata_aoi_d))
    schema = GeoreferencedEODataCubeModel.schema_json(indent=2)
    f = open("GeoreferencedEODataCube.json", "w")
    f.write(schema)
    f.close()
 
