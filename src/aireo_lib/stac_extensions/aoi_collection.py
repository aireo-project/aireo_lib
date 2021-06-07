# Extension for AOI Collection

import typing
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, Required
import datetime
import stac_pydantic
import json
from geojson_pydantic.geometries import Geometry

AIREO_VERSION = "0.0.1-alpha.1"

###################################
#### Core elements models #########
###################################

class AOICollection(stac_pydantic.Collection):
    
    """
    This class represents the  metadata for an AOI Collection
    """
    #AOI: AOI_model
    geometry: Geometry


if __name__ == "__main__":
    collection_ex_d = \
        {"id": "AOI_1",
         "description": "A collection for AOI 1.",
         "stac_version": "1.0.0-beta.2",
         "links": [{"href": "../EO_TDS.json", "rel": "parent"},
          {"href": "./GeoreferencedEOImage_AOI_1.json",
           "rel": "item",
           "type": "application/json",
           "title": "Georeferenced EO Image for AOI_1"},
          {"href": "./ReferenceData_AOI_1.json",
           "rel": "item",
           "type": "application/json",
           "title": "Reference data for AOI_1"},
          {"href": "./AOI_1_time_1/GeoreferencedEOImage.json",
           "rel": "child",
           "type": "application/json",
           "title": "AOI 1 image for time 1"},
          {"href": "./AOI_1_time_1/ReferenceData.json",
           "rel": "child",
           "type": "application/json",
           "title": "AOI 1 reference data for time 1"},
          {"href": "https://raw.githubusercontent.com/radiantearth/stac-spec/v1.0.0-rc.2/examples/collection.json",
           "rel": "self",
           "type": "application/json"}],
         "title": "AOI 1",
         "license": "MIT",
         "extent": {"spatial": {"bbox": [[172.911, 1.343, 172.955, 1.3691]]},
          "temporal": {"interval": [["2008-01-01T00:00:00.000000Z",
             "2008-12-31T00:00:00.000000Z"]]}},
           "geometry": {
             "type": "Polygon",
             "coordinates": [
               [
                 [
                   172.91173669923782,
                   1.3438851951615003
                 ],
                 [
                   172.95469614953714,
                   1.3438851951615003
                 ],
                 [
                   172.95469614953714,
                   1.3690476620161975
                 ],
                 [
                   172.91173669923782,
                   1.3690476620161975
                 ],
                 [
                   172.91173669923782,
                   1.3438851951615003
                 ]
               ]
             ]
            }, 
         "type": "Collection"}

    aoi_collection_ex = AOICollection(** collection_ex_d)
    schema = AOICollection.schema_json(indent=2)
    f = open("aoi_collection.json", "w")
    f.write(schema)
    f.close()
