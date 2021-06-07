# AIREO TDS Extension

import typing
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, Required
from datetime import date, datetime, time, timedelta
import stac_pydantic
import json
from stac_pydantic import validate_item

AIREO_VERSION = "0.0.1-alpha.1"

###################################
#### Core elements models #########
###################################

class FieldSchema(BaseModel):
    features: typing.Dict[str, typing.List[str]]
    references: typing.Dict[str, typing.List[str]]

class ComplianceLevel(str, Enum):
    level_1 = 'level 1'
    level_2 = 'level 2'
    level_3 = 'level 3'

class Tasks(str, Enum):
    regression = 'regression'
    classification = 'classification'
    detection = 'detection'
    Semantic_Segmentation = 'Semantic Segmentation'
    Instance_Segmentation = 'Instance Segmentation'

class Roles(str, Enum):
    licensor = "licensor"
    producer = "producer" 
    processor = "processor" 
    host = "host"

class AIREOTDSCatalog(stac_pydantic.Catalog):
    
    """
    This class represents the core metadata for an AIREO TDS Catalog
    """
    #AOI: AOI_model
    name: Optional[str]
    description: str
    aireo_version: str = Field(AIREO_VERSION, const=True)
    license: str
    providers_name : Optional[str]
    providers_description : Optional[str]
    providers_role : Optional[typing.Dict] #[Roles]]
    providers_url : Optional[typing.Dict] #[Roles]]
    updated: Optional[datetime]
    start_datetime: Optional[datetime]
    end_datetime: Optional[datetime]
    #stac_extensions: typing.List[str]
    #definition: definitionsmodel   
    #stac_extensions:Optional[str]
    type: str
    #profiles: profilesmodel
    doi:Optional[str]
    #assets: assetmodel
    collection:Optional[str]
    provenance: Optional[str]
    publications: Optional[typing.List[str]]
    purpose: Optional[str]
    tasks: typing.List[Tasks]  # should belong to a list of fix values
    funding_info: Optional[str]
    collection_mechanism: Optional[str]
    data_preprocessing:str
    field_schema: FieldSchema
    example_definition: str
    dataset_split: Optional[str]
    data_completeness: Optional[str]
    data_sharing: Optional[str]

    compliance_level: ComplianceLevel
    findable: Optional[str]
    accessible: Optional[str]
    interoperable: Optional[str]
    reuseable: Optional[str]

    processing_history: Optional[str]
    feauture_engineering_recipies: Optional[str]
    data_source: Optional[str]

    qi_accuracy_outliers: Optional[float]
    qi_accuracyData_alignment: Optional[str]
    qi_completeness_missing_values: Optional[float]
    qi_completeness_metadata : Optional[float]

    #class Config:
    #    arbitrary_types_allowed = False

if __name__ == "__main__":
    eo_tds_d = \
    {"id": "Eo-TDS",
     "type": "Collection",
     "stac_version": "1.0.0-beta.2",
     "stac_extensions": ["None"],
     "description": "Top level collection for Biomass AIREO TDS",
     "title": "Top Level Collection",
     "license": "CC-BY-4.0",
     "created": "NULL",
     "providers": "Forest Observation System",
     "providers_name": "Forest Observation System",
     "providers_url": "https://forest-observation-system.net/",
     "platform": "sentinel-2",
     "instrument": "NULL",
     "tasks": ['regression'],
     "compliance_level": 'level 1',
     #"profiles": ["GeoreferencedEOImage", "ReferenceData"],
     "field_schema": {"features": {"input1": ["georeferenced_eo_image"]},
      "references": {"output1": ["ReferenceProfile"]}},
     "provenance": "",
     "purpose": "",
     "task": "",
     "collection_mechanism": "",
     "example_definition": "",
     "data_preprocessing": "",
     "AOI": ["AOI 1", "AOI 2", "AOI 3"],
     "links": [{"rel": "root",
       "href": "./EO_TDS.json",
       "type": "application/json"},
      {"rel": "sub_collection",
       "href": "./AOI_1/AOI_1.json",
       "type": "application/json",
       "title": "AOI 1"},
      {"rel": "sub_collection",
       "href": "./AOI_2/AOI_2.json",
       "type": "application/json",
       "title": "AOI 2"},
      {"rel": "sub_collection",
       "href": "./AOI_3/AOI_3.json",
       "type": "application/json",
       "title": "AOI 3"},
      {"rel": "field_metadata",
       "href": "./GeoreferencedEOImage.json",
       "type": "application/json",
       "title": "input1"},
      {"rel": "field_metadata",
       "href": "./ReferenceData.json",
       "type": "applicaion/json",
       "title": "output1"},
      {"rel": "self",
       "href": "https://raw.githubusercontent.com/radiantearth/stac-spec/v1.0.0-rc.2/examples/collection.json",
       "type": "application/json"}]}

    eo_tds = AIREOTDSCatalog(**eo_tds_d)

    #print(validate_item(eo_tds_d))
    schema = AIREOTDSCatalog.schema_json(indent=2)
    f = open("AIREO_TDS_catalog.json", "w")
    f.write(schema)
    f.close()
