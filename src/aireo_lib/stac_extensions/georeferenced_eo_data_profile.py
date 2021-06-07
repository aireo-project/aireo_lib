# The stac item extension for the GeoreferencedEOImage data profile
# 
# still have problem, stac_pydantic does not validate the orbitType metadata

from pydantic import BaseModel
from stac_pydantic import Extensions, Item
from typing import List, Optional
from geojson_pydantic.geometries import Geometry

class GeoreferencedEODataModel(BaseModel):
    parent_identifier: str
    product_type: str
    composed_of: Optional[str]
    linked_with: Optional[str]
    native_product_format: Optional[str]
    processing_level: Optional[str]
    auxillary_data_set_file: Optional[str]
    gsd: Optional[float]
    #bbox: Optional[Geometry]

    qi_accuracy_outliers: Optional[float]
    qi_accuracy_data_alignment: Optional[str]
    qi_accuracy_labelling: Optional[float]
    qi_completeness_missing_values: Optional[float]
    qi_completeness_metadata: Optional[float]
    #qi_completeness_classification_schema: Optional[float]

if __name__ == '__main__':
    from stac_pydantic import validate_item
    Extensions.register('georeferenced_eo_image', GeoreferencedEOImageModel)

    geo_img_metadata_aoi_d = \
        {
         "type": "Feature",
         "stac_extensions": ["georeferenced_eo_image"],
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
            "title": "Core Item",
            "parent_identifier": "null",
            "description": "A sample STAC Item that includes examples of all common metadata",
            "datetime": "2020-12-11T22:38:32.125Z",
            "start_datetime": "2020-12-11T22:38:32.125Z",
            "end_datetime": "2020-12-11T22:38:32.327Z",
            "created": "2020-12-12T01:48:13.725Z",
            "platform": "cool_sat2",
            "instruments": [
              "cool_sensor_v1"
            ],
            "constellation": "ion",
            "mission": "collection 5624",
            "gsd": 0.512,
            "FeatureRecipes": ["null"],
            "orbitType": ["234", "2342"],
            "doi": "null",
            "product_type": "null",
            "Status": "null",
          },
         "links": [{"rel": "root",
           "href": "../EO_TDS.json",
           "type": "application/json"}],
            
         "assets":{}
        }

    geo_img_metadata_aoi = Item(**geo_img_metadata_aoi_d)

    #print('The stac item for the georeferenced_eo_image dataprofile does not validate because the data type for orbitType is wrong: \n',validate_item(geo_img_metadata_aoi_d))

    # Fix the type of orbitType to be a string
    #geo_img_metadata_aoi_d['properties']['orbitType'] = 'ABC'
    #geo_img_metadata_aoi_d['FeatureRecipes'] = 'ABD'

    #print('After fixing the geo_img_metadata_aoi_d["properties"]["orbitType"] to be a string, the item validates now: \n', validate_item(geo_img_metadata_aoi_d))
    print(validate_item(geo_img_metadata_aoi_d))
    schema = GeoreferencedEOImageModel.schema_json(indent=2)
    f = open("georeference_eo_data.json", "w")
    f.write(schema)
    f.close()
