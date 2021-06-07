# The stac item extension for the GeoreferencedEOImage data profile
# 
# still have problem, stac_pydantic does not validate the orbitType metadata

from pydantic import BaseModel
from stac_pydantic import Extensions, Item
from typing import List, Optional
from geojson_pydantic.geometries import Geometry
from datetime import date, datetime, time, timedelta
from enum import Enum

class Task(str, Enum):
    regression = 'regression'
    classification = 'classification'
    detection = 'detection'
    Semantic_Segmentation = 'Semantic Segmentation'
    Instance_Segmentation = 'Instance Segmentation'

class TDS_Type_Model(str, Enum):
    annotated = 'annotated'
    measured = 'measured'
    digitised = 'digitised'
    sampled = 'sampled'

class ReferenceDataModel(BaseModel):
    name: str
    description: str
    type: str
    task: Task
    classes: List
    overviews: Optional[List]
    collection_method: Optional[str]
    data_preprocessing: Optional[str]
    time_gap: Optional[float]
    spatial_validity: Optional[float]
    provenance: Optional[str]
    processing_history: Optional[str]
    TDS_type: Optional[TDS_Type_Model]
    multi_extend_of: Optional[Geometry]
    center_of: Optional[Geometry]
    orientation: str
    CRS: str

    value: float
    time_range: Optional[timedelta]

    qi_accuracy_outliers: Optional[float]
    qi_accuracy_data_alignment: Optional[str]
    qi_accuracy_labelling: Optional[float]
    qi_completeness_missing_values: Optional[float]
    qi_completeness_metadata: Optional[float]
    qi_completeness_classification_schema: Optional[float]


if __name__ == '__main__':
    from stac_pydantic import validate_item
    Extensions.register('reference_data', ReferenceDataModel)

    ref_metadata_aoi_d = \
        {
         "id": "reference_data",
         "type": "Feature",
         "stac_extensions": ["reference_data"],
         "stac_version": "1.0.0-beta.2",
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
            "name": "reference",
            "description": "reference",
            "type": "reference",
            "task" : "regression",
            "datetime": "2020-03-09T14:53:23.262208+00:00",
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
            "classes": ["aa", "bb"],
            "overviews": ['bb', 'cc'],
            "collection_method": "N/A",
            "data_preprocessing": "None",
            "orientation": "null",
            "CRS": "null",
            "value": 7.5,
         },
          "links": [{"rel": "root",
           "href": "../EO_TDS.json",
           "type": "application/json"}],
            
         "assets":{}
        }

    ref_metadata_aoi = Item(**ref_metadata_aoi_d)
    print(validate_item(ref_metadata_aoi_d))
    #print('The stac item for the georeferenced_eo_image dataprofile does not validate because the data type for orbitType is wrong: \n',validate_item(ref_metadata_aoi_d))
    schema = ReferenceDataModel.schema_json(indent=2)
    f = open("reference_data.json", "w")
    f.write(schema)
    f.close()
