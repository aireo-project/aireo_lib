import pkg_resources

from loguru import logger

import json
import yaml

from shutil import copyfile


from stac_pydantic import validate_item
from stac_pydantic import Extensions
from stac_pydantic import Item

import typing
from typing import NamedTuple
from dataclasses import dataclass

from pathlib import Path

from aireo_lib.stac_extensions.georeferenced_eo_image_profile import GeoreferencedEOImageModel
from aireo_lib.stac_extensions.reference_data_profile import ReferenceDataModel
from aireo_lib.stac_extensions.aireo_tds_catalog import AIREOTDSCatalog
from aireo_lib.stac_extensions.aoi_collection import AOICollection
from aireo_lib.stac_extensions.georeferenced_eo_data_profile import GeoreferencedEODataModel
from aireo_lib.stac_extensions.georeferenced_eo_datacube_profile import GeoreferencedEODataCubeModel


stac_extension_config_fn = pkg_resources.resource_filename(__name__, 'data/tds_stac_extension.yaml')
metadata_requirement_config_fn = pkg_resources.resource_filename(__name__, 'data/metadata_requirement.yaml')

with open(stac_extension_config_fn, 'r') as ext_yaml_f:
    stac_extension_conf_d = yaml.safe_load(ext_yaml_f)

# register the stac pydantic vendor extensions (for STAC item)
for profile_name in stac_extension_conf_d:
    profile_info = stac_extension_conf_d[profile_name]
    ext_registration_cmd = 'Extensions.register(' +'"' + \
    profile_info['extension_name'] + '", ' + \
    profile_info['class_name'] + ')'
    exec(ext_registration_cmd)


class MetadataRequirementInfo(NamedTuple):
    """
    Metadata requirement for the core catalog, aoi collection, a global profile, or an aoi profile
    """
    required_metadata_set: set 
    recommended_metadata_set: set
    optional_metadata_set: set

class FieldSchema(NamedTuple):
    features: typing.Dict[str, typing.List[str]]
    references: typing.Dict[str, typing.List[str]]


class FieldProfileInfo(NamedTuple):
    fn_path: str # absolute path to parse file,
    metadata_d: typing.Dict # dictionary of metadata
    data_asset_w_path: typing.Union[str, None] = None #  absolute path to asset, will be empty for global profile, will be
    # relative path when writing to catalog
    data_asset_info_d: typing.Union[typing.Dict, None] = None # dictionary which store data asset fields, empty for global profile



class AllFieldMetadata(NamedTuple):
    """
    map from a field to its metadata dictionary, global level or aoi level
    """
    features: typing.Dict[str, FieldProfileInfo]
    references: typing.Dict[str, FieldProfileInfo]

@dataclass
class TDSRootCtlInfo:
    fn_path: str # absolute path to the file
    tds_root_metadata_d: typing.Dict
    # this field is None at first but will be updated later
    g_all_field_metadata: typing.Union[AllFieldMetadata, None] = None

@dataclass
class AOICollectionInfo:
    fn_path: str # absolute path to the file
    aoi_collection_metadata_d: typing.Dict
    aoi_all_field_metadata: typing.Union[AllFieldMetadata, None] = None


# Populate the metadata requirement for different extensions and profiles
with open(metadata_requirement_config_fn, 'r') as metadata_requirement_f:
    all_metadata_requirement_d = yaml.safe_load(metadata_requirement_f)


# map from a stac file type (aireo tds catalog, extension) to its metadata requirement
ext_to_metadata_req_info_d = {}
for ext_name in all_metadata_requirement_d:
    ext_metadata_req_d = all_metadata_requirement_d[ext_name]
    required_metadata_set = set([metadata for metadata in ext_metadata_req_d
                                if ext_metadata_req_d[metadata]=='required'])
    recommended_metadata_set = set([metadata for metadata in ext_metadata_req_d
                                if ext_metadata_req_d[metadata]=='recommended'])
    optional_metadata_set = set([metadata for metadata in ext_metadata_req_d
                                if ext_metadata_req_d[metadata]=='optional'])
    ext_to_metadata_req_info_d[ext_name] = \
            MetadataRequirementInfo(required_metadata_set=required_metadata_set,
                                    recommended_metadata_set=recommended_metadata_set,
                                    optional_metadata_set=optional_metadata_set)
    


class DatasetSTACCatalog:
    """
    This class provides the functionalities to populate the metadata for an EO TDS catalog, and 
    functionalities to load and parse an EO TDS Catalog in STAC compliant json format.
    """
    def __init__(self):

        self.valid_tds_root = False
        self.valid_tds = False
        self.valid_field_schema = False
        self.aoi_collection_info_l = []
        

    @classmethod
    def from_TDSCatalog(cls, tds_catalog_path):
        """
        This function  takes as input a full path to the EO TDS catalog root json;  
        it then parses the EO TDS TDS json files to extract all the metadata and links to 
        assets; and finally creates a DatasetSTACCatalog object

        :param tds_catalog_path: full path to the EO TDS catalog root json file
        :return: a DatasetSTACCatalog object
        """

        # Load the TDS root json
        tds_ctl_root_info = DatasetSTACCatalog.__parse_root_tds_ctl_info(tds_catalog_path)

        tds_ctl_o = DatasetSTACCatalog()

        # Load and Parse all global field profiles
        tds_ctl_root_info.g_all_field_metadata = DatasetSTACCatalog.__parse_g_profile_info(tds_ctl_root_info)

        # to validate it
        tds_ctl_o.tds_ctl_root_info = tds_ctl_root_info
        tds_ctl_o.valid_tds_root = True

        field_schema_d = tds_ctl_root_info.tds_root_metadata_d.get('field_schema')

        # Add field schema
        tds_ctl_o.add_field_schema(field_schema_d)

        # Load and Parse each AOI sub-collections
        tds_ctl_o.aoi_collection_info_l = DatasetSTACCatalog.__parse_aoi_subcollection_info(tds_ctl_root_info)

        for aoi_collection_info in tds_ctl_o.aoi_collection_info_l:
            # For each AOI sub-collection parse all AOI field profiles
            # and update the field aoi_all_field_metadata
            aoi_collection_info.aoi_all_field_metadata = DatasetSTACCatalog.__parse_aoi_profile_info(aoi_collection_info, tds_ctl_root_info) 

        tds_ctl_o.valid_tds = True
        
        return tds_ctl_o


    @staticmethod
    def validate_tds_root_dict(tds_dict):
        """
        To validate the TDS root json dict
        """
        valid_tds_d = True
        try:
            tds_catalog = AIREOTDSCatalog(**tds_dict)
        except Exception as e:
            logger.error( e)
            valid_tds_d = False

        return valid_tds_d
    
    @staticmethod
    def validate_aoi_dict(aoi_dict):
        """
        To validate the AOI subcollection json dict
        """
        valid_aoi_d = True
        try:
            aoi_col = AOICollection(**aoi_dict)
        except Exception as e:
            logger.error( e)
            valid_aoi_d = False

        return valid_aoi_d

    @staticmethod
    def validate_global_profile_dict(g_profile_dict):
        """
        To validate a global profile  json dict for one field (eo feature or reference data)
        """
        valid_g_profile = True
        try:
            item = Item(**g_profile_dict)
        except Exception as e:
            logger.error(e)
            valid_g_profile = False

        if valid_g_profile:
            valid_g_profile = validate_item(g_profile_dict) 

        return valid_g_profile
        # provide additional validation
    
    @staticmethod
    def validate_aoi_profile_dict(aoi_profile_dict):
        """
        To validate an AOI's  profile  json dict for one field
        """
        valid_aoi_profile = True
        try:
            item = Item(**aoi_profile_dict)
        except Exception as e:
            logger.error(e)
            valid_aoi_profile = False

        if valid_aoi_profile:
            valid_aoi_profile = validate_item(aoi_profile_dict) 

        return valid_aoi_profile


    @staticmethod
    def __parse_root_tds_ctl_info(tds_ctl_path):
        """
        Parse an EO TDS root catalog json file
        """
        # Load the TDS root json
        with open(tds_ctl_path, 'r') as tds_ctl_f:
            tds_ctl_d = json.load(tds_ctl_f)

        tds_ctl_full_path = str(Path(tds_ctl_path).absolute())

        tds_ctl_info = TDSRootCtlInfo(fn_path= tds_ctl_full_path,
                                      tds_root_metadata_d=tds_ctl_d)
        return tds_ctl_info 

    @staticmethod
    def __parse_g_profile_info(tds_root_ctl_info):
        """
        Parse the metadata profiles  linked from a TDS root catalog 
        and save all the root profile metadadata to a AllFieldMetadata object  
        Return: 
        """
        
        root_ctl_abs_folder= Path(tds_root_ctl_info.fn_path).absolute().parent
        field_schema = FieldSchema(**tds_root_ctl_info.tds_root_metadata_d['field_schema'] )
        # logger.info(field_schema)

        all_field_metadata = AllFieldMetadata(features={}, references={})

        for link in tds_root_ctl_info.tds_root_metadata_d.get('links'):
            if link['rel'].startswith('metadata'):
                _, field_type, field_name = link['rel'].split('/') # the rel for a profile is in the format '/metadata/features/input1'
                profile_path = Path(link['href'])
                if not profile_path.is_absolute():
                    profile_path = root_ctl_abs_folder / profile_path

                with open(profile_path, 'r') as profile_f:
                    profile_metadata_d = json.load(profile_f)

                if not hasattr(FieldSchema, field_type):
                    raise Exception(f"The type of field could only be 'features' or 'references',{field_type} is not a valid one")

                field_profile_info = FieldProfileInfo(fn_path=profile_path, metadata_d=profile_metadata_d)
                set_field_metadata_command = 'all_field_metadata.'+ field_type+'["' + field_name + '"] = ' + 'field_profile_info'
                exec(set_field_metadata_command)

        # TODO: to check that the number of profiles match
        return all_field_metadata
    
    def __parse_aoi_profile_info(aoi_collection_info, tds_root_ctl_info):
        """
        Parse all aoi profile metadata linked from an AOICollectionInfo object
        and save the extracted metadata to an AllFieldMetadata object

        :param aoi_collection_info: an AOICollectionInfo object
        :param tds_root_ctl_info: a TDSRootCtlInfo object

        :returns:  an AllFieldMetadata object
        """
        # duplicated code,, to clean up
        aoi_collection_abs_folder= Path(aoi_collection_info.fn_path).absolute().parent
        field_schema = FieldSchema(**tds_root_ctl_info.tds_root_metadata_d['field_schema'] )
        # print(field_schema)

        all_field_metadata = AllFieldMetadata(features={}, references={})

        for link in aoi_collection_info.aoi_collection_metadata_d.get('links'):
            if link['rel'].startswith('metadata'):
                _, field_type, field_name = link['rel'].split('/') # the rel for a profile is in the format '/metadata/features/input1'
                profile_path = Path(link['href'])
                if not profile_path.is_absolute():
                    profile_path = aoi_collection_abs_folder / profile_path

                with open(profile_path, 'r') as profile_f:
                    profile_metadata_d = json.load(profile_f)

                if not hasattr(FieldSchema, field_type):
                    raise Exception(f"The type of field could only be 'features' or 'references',{field_type} is not a valid one")

                # parse asset information
                # expect only one assset per profile, throw exception otherwise
                if len(profile_metadata_d['assets']) != 1:
                    raise Exception(f'Has different than 1 asset for file: {profile_path}')

                data_asset_name = list(profile_metadata_d['assets'].keys())[0]
                data_asset_info_d = profile_metadata_d['assets'][data_asset_name]

                data_asset_path = Path(data_asset_info_d['href'])
                if not data_asset_path.is_absolute():
                    # if it is relative, convert to absolute based on profile_path
                
                    data_asset_path = aoi_collection_abs_folder / data_asset_path 
                    if not data_asset_path.is_file():
                        raise Exception(f'{data_asset_path} doesnt point to an asset file')


                field_profile_info = FieldProfileInfo(fn_path=str(profile_path), metadata_d=profile_metadata_d,
                                                      data_asset_w_path=str(data_asset_path), 
                                                      data_asset_info_d = data_asset_info_d)
                set_field_metadata_command = 'all_field_metadata.'+ field_type+'["' + field_name + '"] = ' + 'field_profile_info'
                #print(set_field_metadata_command)
                exec(set_field_metadata_command)

        return all_field_metadata 


    @staticmethod
    def __parse_aoi_subcollection_info(tds_root_ctl_info):
        """
        Parse the aoi subcollection information from a TDSRootCtlInfo object
        
        :param tds_root_ctl_info: a TDSRootCtlInfo object
        :returns : a list of AOICollectionInfo objects
        """
        # How to store the path (absolute paths?)
        root_ctl_abs_folder= Path(tds_root_ctl_info.fn_path).absolute().parent

        aoi_collection_info_l = []

        for link in tds_root_ctl_info.tds_root_metadata_d.get('links'):
            if link['rel'] == 'child':
                # print(link)

                aoi_f_path = Path(link['href'])
                if not aoi_f_path.is_absolute():
                    aoi_f_path = root_ctl_abs_folder / aoi_f_path
                    if not aoi_f_path.is_file():
                        raise Exception(f'{aoi_f_path} is not an aoi json file')

                with open(aoi_f_path, 'r') as aoi_f:
                    aoi_collection_metadata_d = json.load(aoi_f)

                aoi_collection_info = AOICollectionInfo(fn_path=str(aoi_f_path),
                                                        aoi_collection_metadata_d=aoi_collection_metadata_d)

                aoi_collection_info_l.append(aoi_collection_info)

        return aoi_collection_info_l


    def add_field_schema(self, field_schema_d: typing.Dict) -> None:
        """
        Add the field schema to the TDS catalog object

        :param field_schema_d: the field schema

        """
        self.field_schema = FieldSchema(**field_schema_d)
        self.valid_field_schema = True



    def add_tds_root_metadata(self, core_metatdata_d, 
                        g_feature_metadata_d, 
                        g_ref_data_metadata_d, 
                        tds_root_path: typing.Optional[str] = None,
                        g_feature_profile_path_d: typing.Optional[typing.Dict[str, str]] = None,
                        g_ref_data_profile_path_d: typing.Optional[typing.Dict[str, str]] = None):
        """
        ADD TDS global core element metadata, and  global level profile metadata to the
        TDS DatasetSTACCatalog object.

        :param core_metatdata_d: dictionary that stores the TDS catalog root file metadata
        :param g_feature_metadata_d: dictionary which maps from each eo feature name to 
                the dictionary of root profile for that eo feature
        :param g_ref_data_metadata_d:  dictionary which maps from each reference data
                output name to the dictionary of root profile for that reference data name
        :param tds_root_path: path with file name (absolute path) to the root catalog json, 
                used when parsing an available EO TDS Catalog json hierarchy
        :param g_feature_profile_path_d: dictionary that maps from each eo feature name to the
                full path of its profile json file, used when parsing an EO TDS json hierarchy
        :param g_ref_data_profile_path_d: dictionary which maps from each reference data 
                output name to the the full path of its profile json file, used when 
                parsing an EO TDS catalog json hierarchy

        """
        self.valid_tds_root = False
        # validate the data, and if yes update the catalog object, and the corresponding flag
        core_metatdata_d['links'] = []
        core_metatdata_d['assets'] = {}
        if not DatasetSTACCatalog.validate_tds_root_dict(core_metatdata_d):
            return self.valid_tds_root

        self.add_field_schema(core_metatdata_d['field_schema'])

        for eo_feature in g_feature_metadata_d:
            valid_eo_feature_profile = DatasetSTACCatalog.validate_global_profile_dict(g_feature_metadata_d[eo_feature])
            if not valid_eo_feature_profile:
                return self.valid_tds_root

        for reference_data in g_ref_data_metadata_d:
            valid_ref_data_profile = \
            DatasetSTACCatalog.validate_global_profile_dict(g_ref_data_metadata_d[reference_data])
            if not valid_eo_feature_profile:
                return self.valid_ref_data_profile

        feature_field_profile_info_d = {}
        for eo_feature in g_feature_metadata_d:
            # generate FieldProfileInfo object for the feature
            if g_feature_profile_path_d:
                if not eo_feature in g_feature_profile_path_d:
                    raise Exception(f'{eo_feature} path is not in {g_feature_profile_path_d}!')

                feature_fn_path = g_feature_profile_path_d[eo_feature]
            else:
                feature_fn_path = ''

            # no asset here
            eo_feature_field_profile_info = \
                    FieldProfileInfo(fn_path=feature_fn_path, metadata_d=g_feature_metadata_d[eo_feature])
            feature_field_profile_info_d[eo_feature] = eo_feature_field_profile_info

        ref_data_field_profile_info_d = {}
        for ref_data in g_ref_data_metadata_d:
            # generate FieldProfileInfo object for the feature
            if g_ref_data_profile_path_d:
                if not ref_data in g_ref_data_profile_path_d:
                    raise Exception(f'{ref_data} path is not in {g_ref_data_profile_path_d}!')

                ref_data_fn_path = g_feature_profile_path_d[eo_feature]
            else:
                ref_data_fn_path = ''

            # no asset here
            ref_data_field_profile_info = \
                    FieldProfileInfo(fn_path=ref_data_fn_path, metadata_d=g_ref_data_metadata_d[ref_data])
            ref_data_field_profile_info_d[ref_data] = ref_data_field_profile_info


        g_all_field_metadata_info = AllFieldMetadata(features=feature_field_profile_info_d,
                                                     references=ref_data_field_profile_info_d)


        self.tds_ctl_root_info = TDSRootCtlInfo(fn_path=tds_root_path, tds_root_metadata_d=core_metatdata_d,
                                                g_all_field_metadata=g_all_field_metadata_info)

            

        self.valid_tds_root = True
        return self.valid_tds_root



    def add_aoi_metadata(self, aoi_metadata_d, 
                         aoi_feature_metadata_d, 
                         aoi_ref_data_metadata_d,
                         aoi_feature_asset_path_d: typing.Dict[str, str],
                         aoi_ref_data_asset_path_d: typing.Dict[str, str],
                         aoi_fn_path: typing.Optional[str] = '',
                         aoi_feature_profile_path_d: typing.Optional[typing.Dict] = None,
                         aoi_ref_data_profile_path_d: typing.Optional[typing.Dict] = None):
        """
        Add AOI metadata and profile metadata for one AOI to the TDS DatasetSTACCatalog object

        :param aoi_metadata_d: dictionary that stores the AOI metadata dictionary
        :param aoi_feature_metadata_d: dictionary which maps from each eo feature name to 
                the dictionary of the aoi profile for that eo feature
        :param aoi_ref_data_metadata_d: dictionary which maps from each reference data
                output name to the dictionary of the aoi profile for that reference data name
        :param aoi_feature_asset_path_d: dictionary which maps from each eo feature name
                to the full path of its asset 
        :param aoi_ref_data_asset_path_d: dictionary which maps from each reference data
                output name to the full path of its asset
        :param aoi_fn_path: full path to the aoi collection json file,
                used when parsing an available EO TDS Catalog json hierarchy
        :param aoi_feature_profile_path_d: dictionary that maps from each eo feature name to the
                full path of its AOI profile json file, used when parsing an EO TDS json 
                hierarchy
        :param aoi_ref_data_profile_path_d: dictionary which maps from each reference data 
                output name to the the full path of its AOIprofile json file, used when 
                parsing an EO TDS catalog json hierarchy
        """
        valid_aoi_metadata = False
       
        aoi_metadata_d['links'] = []
        aoi_metadata_d['assets'] = {}
        # validate the data, and if yes update the catalog object, and the corresponding flag
        if not DatasetSTACCatalog.validate_aoi_dict(aoi_metadata_d):
            return valid_aoi_metadata

        for eo_feature in aoi_feature_metadata_d:
            valid_eo_feature_profile = DatasetSTACCatalog.validate_aoi_profile_dict(aoi_feature_metadata_d[eo_feature])
            if not valid_eo_feature_profile:
                return valid_aoi_metadata

        for reference_data in aoi_ref_data_metadata_d:
            valid_ref_data_profile = \
            DatasetSTACCatalog.validate_aoi_profile_dict(aoi_ref_data_metadata_d[reference_data])
            if not valid_ref_data_profile:
                return valid_aoi_metadata

        feature_field_profile_info_d = {}
        for eo_feature in aoi_feature_metadata_d:
            # generate FieldProfileInfo object for the feature
            if aoi_feature_profile_path_d:
                if not eo_feature in aoi_feature_profile_path_d:
                    raise Exception(f'{eo_feature} path is not in {aoi_feature_profile_path_d}!')

                feature_fn_path = aoi_feature_profile_path_d[eo_feature]
            else:
                feature_fn_path = ''

            # only have href in asset dict
            eo_feature_data_asset_w_path = aoi_feature_asset_path_d[eo_feature]

            # include a link to the asset here
            eo_feature_field_profile_info = \
                    FieldProfileInfo(fn_path=feature_fn_path, metadata_d=aoi_feature_metadata_d[eo_feature],
                                     data_asset_w_path=str(eo_feature_data_asset_w_path))

            feature_field_profile_info_d[eo_feature] = eo_feature_field_profile_info

        ref_data_field_profile_info_d = {}
        for reference_data in aoi_ref_data_metadata_d:
            # generate FieldProfileInfo object for the feature
            if aoi_ref_data_profile_path_d:
                if not reference_data in aoi_ref_data_profile_path_d:
                    raise Exception(f'{reference_data} path is not in {aoi_ref_data_profile_path_d}!')

                ref_data_fn_path = aoi_feature_profile_path_d[reference_data]
            else:
                ref_data_fn_path = ''
            
            # only have href in asset dict
            ref_data_asset_w_path = aoi_ref_data_asset_path_d[reference_data]


            # no asset here
            ref_data_field_profile_info = \
                    FieldProfileInfo(fn_path=ref_data_fn_path, metadata_d=aoi_ref_data_metadata_d[reference_data], 
                                    data_asset_w_path=str(ref_data_asset_w_path))

            ref_data_field_profile_info_d[reference_data] = ref_data_field_profile_info


        aoi_all_field_metadata_info = AllFieldMetadata(features=feature_field_profile_info_d,
                                                     references=ref_data_field_profile_info_d)


        aoi_collection_info = AOICollectionInfo(fn_path=aoi_fn_path, aoi_collection_metadata_d=aoi_metadata_d,
                                                aoi_all_field_metadata=aoi_all_field_metadata_info)


        self.aoi_collection_info_l.append(aoi_collection_info)
        valid_aoi_metadata = True


        if valid_aoi_metadata and self.valid_tds_root and self.valid_field_schema:
            self.valid_tds = True

        return valid_aoi_metadata


    def compute_compliance_level(self):
        """
        Compute the compliance level of a valid TDS DatasetSTACCatalog object, uses only the 
        TDS catalog root metadata dictionary for now
        """
        # compute compliance level for the TDS core element
        assert self.valid_tds

        root_metadata_d = self.tds_ctl_root_info.tds_root_metadata_d

        available_root_metadata = set(root_metadata_d.keys())
        tds_core_metadata_req_info = ext_to_metadata_req_info_d['aireo_tds_core']

        common_root_required_metadata = \
                available_root_metadata.intersection(tds_core_metadata_req_info.required_metadata_set)
        common_root_recommended_metadata = \
                available_root_metadata.intersection(tds_core_metadata_req_info.recommended_metadata_set)
        common_root_optional_metadata = \
                available_root_metadata.intersection(tds_core_metadata_req_info.optional_metadata_set)
        tds_core_compliance_level = 1
        if len(common_root_recommended_metadata) == len(tds_core_metadata_req_info.recommended_metadata_set):
            tds_core_compliance_level = 2
        if (tds_core_compliance_level==2) and \
           (len(common_root_optional_metadata)==len(tds_core_metadata_req_info.optional_metadata_set)):
            tds_core_compliance_level = 3

        return tds_core_compliance_level

    def report_metadata_completeness(self):
        """
        Report the percentage of metadata completed at the CoreElments level        

        :returns: a dictionary which reports the percentage of metadata filled for 
                required metadata, recommended metadata, and optional metadata for
                the CoreElements metadata
        """
        
        # TODO: to report metadata completeness for  global profile level, and aoi profile level
        
        assert self.valid_tds

        root_metadata_d = self.tds_ctl_root_info.tds_root_metadata_d

        available_root_metadata = set(root_metadata_d.keys())
        tds_core_metadata_req_info = ext_to_metadata_req_info_d['aireo_tds_core']

        common_root_required_metadata = \
                available_root_metadata.intersection(tds_core_metadata_req_info.required_metadata_set)
        common_root_recommended_metadata = \
                available_root_metadata.intersection(tds_core_metadata_req_info.recommended_metadata_set)
        common_root_optional_metadata = \
                available_root_metadata.intersection(tds_core_metadata_req_info.optional_metadata_set)
        pct_root_required_metadata = len(common_root_required_metadata) /\
            len(tds_core_metadata_req_info.required_metadata_set) 
        pct_root_recommended_metadata = len(common_root_recommended_metadata) /\
            len(tds_core_metadata_req_info.recommended_metadata_set) 


        pct_root_optional_metadata = len(common_root_optional_metadata) /\
            len(tds_core_metadata_req_info.optional_metadata_set)
        

        metadata_completeness_d = {}
        metadata_completeness_d['tds_core_metadata'] = \
            {'required_metadata': pct_root_required_metadata,
             'recommended_metadata': pct_root_recommended_metadata,
             'optional_metadata': pct_root_optional_metadata}

        return metadata_completeness_d


    def write_TDS_STAC_Catalog(self, catalog_fn_w_path):
        """
        Write the TDS catalog json hierarchy and the corresponding assets to the 
        specified full path of the root TDS Catlog json file

        :param catalog_fn_w_path: full path to the root TDS Catalog json file
        """
        # Create a datasheet.md file in the root folder and add data to it
        def write_datasheet(core_metadata_d, root_ctl_path):
            with open(root_ctl_path / Path('datasheet.md'), 'w') as f:
                to_write = "# " + core_metadata_d['title'] + "\n\n\n### Description\n" + core_metadata_d[
                    'description'] + "\n\n"
                if 'purpose' in core_metadata_d:
                    to_write += "### What is the purpose of creating the dataset? \n" + core_metadata_d[
                        'purpose'] + "\n\n"

                to_write += "### What Machine learning task(s) the TDS is intended for? \n"
                if len(core_metadata_d['tasks']) > 1:
                    for task in core_metadata_d['tasks']:
                        to_write += task + ', '
                    to_write = to_write[:-2]  # removing last comma
                else:
                    to_write += core_metadata_d['tasks'][0]
                if 'funding_info' in core_metadata_d:
                    to_write += "\n\n### Funding information of the dataset \n" + core_metadata_d['funding_info']
                if 'collection_mechanism' in core_metadata_d:
                    to_write += "\n\n### Collection mechanism of the underlying data \n" + core_metadata_d[
                        'collection_mechanism']
                to_write += "\n\n### Pre-processing steps applied to the dataset \n" + core_metadata_d[
                    'data_preprocessing']

                # Converting field_schema to a human readable text
                to_write += "\n\n### What are the different variables and what AIREO profiles do they belong to?\n"
                to_write += f"All predictive feature variables and their profiles are:"
                for feature in core_metadata_d['field_schema']['features']:
                    to_write += f"\n{feature} belonging to profile(s) "
                    if len(core_metadata_d['field_schema']['features'][feature]) > 1:
                        for profile in core_metadata_d['field_schema']['features'][feature]:
                            to_write += profile + ", "
                        to_write = to_write[:-2]
                    else:
                        to_write += core_metadata_d['field_schema']['features'][feature][0]

                to_write += f"\nAll reference data variables and their profiles are:"
                for ref in core_metadata_d['field_schema']['references']:
                    to_write += f"\n{ref} belonging to profile(s)"
                    if len(core_metadata_d['field_schema']['references'][ref]) > 1:
                        for profile in core_metadata_d['field_schema']['references'][ref]:
                            to_write += profile + ", "
                        to_write = to_write[:-2]
                    else:
                        to_write += core_metadata_d['field_schema']['references'][ref][0]

                to_write += "\n\n### What does one training example or instance of the dataset include?\n" + \
                            core_metadata_d['example_definition'] + "\n\n"
                if 'dataset_split' in core_metadata_d:
                    to_write += "### Recommended train, test and validate splits of the dataset for training a Machine Learning model\n" + \
                                core_metadata_d['dataset_split'] + "\n\n"
                if 'data_completeness' in core_metadata_d:
                    to_write += "### Information on completeness of the dataset\n" + core_metadata_d[
                        'data_completeness'] + "\n\n"
                if 'data_sharing' in core_metadata_d:
                    to_write += "### How will the dataset be shared?\n" + core_metadata_d['data_sharing'] + "\n\n"
                f.write(to_write)
        
        def generate_aoi_collection_json_dict(aoi_collection_info, tds_catalog_root_folder, tds_catalog_root_fn):
            # update links of the metadata dict
            aoi_collection_metadata_d = aoi_collection_info.aoi_collection_metadata_d
            aoi_collection_fn = aoi_collection_metadata_d.get('id') + '.json'
            # set the links to be empty
            aoi_collection_metadata_d['links'] = []
            root_link = {'rel': 'root',
                         'href': '../' + str(tds_catalog_root_fn),
                         'type': 'application/json'}
            parent_link = {'rel': 'parent',
                         'href': '../' + str(tds_catalog_root_fn),
                         'type': 'application/json'}
            self_link = {'rel': 'self',
                         'href': './' + str(aoi_collection_fn),
                         'type': 'application/json'}

            aoi_collection_metadata_d['links'] = [root_link, parent_link, self_link]
            
            # add feature profile file links
            for eo_feature in aoi_collection_info.aoi_all_field_metadata.features:
                eo_feature_profile_fn =  'feature_' +  eo_feature + '.json'
                eo_feature_link = {'rel': 'metadata/features/' + eo_feature,
                                   'href':  './' + eo_feature_profile_fn,
                                   'type': 'application/geo+json' }
                aoi_collection_metadata_d['links'].append(eo_feature_link)


            for reference_data in aoi_collection_info.aoi_all_field_metadata.references:
                reference_data_profile_fn =  'reference_data_' +  reference_data + '.json'
                reference_data_link = {'rel': 'metadata/references/' + reference_data,
                                   'href':  './' + reference_data_profile_fn,
                                   'type': 'application/geo+json' }
                aoi_collection_metadata_d['links'].append(reference_data_link)

            return aoi_collection_metadata_d

        assert self.valid_tds

        catalog_fn_w_path = Path(catalog_fn_w_path)
        tds_catalog_root_folder = catalog_fn_w_path.parent
        tds_catalog_root_fn = catalog_fn_w_path.name

        # make root directory, needs to be a new directory
        tds_catalog_root_folder.mkdir(parents=True)

        tds_ctl_root_metadata_d = self.tds_ctl_root_info.tds_root_metadata_d
        tds_ctl_root_metadata_d['links'] = []

        tds_ctl_root_self_link =  {'rel': 'self',
                         'href': './' + str(tds_catalog_root_fn),
                         'type': 'application/json'}
        tds_ctl_root_metadata_d['links'].append(tds_ctl_root_self_link)


        write_datasheet(tds_ctl_root_metadata_d, tds_catalog_root_folder)

        # Add global feature and ref data profile links to tds_ctl_root_metadata_d
        # Save global feature and ref data profile jsons

        for eo_feature in self.field_schema.features:
            eo_feature_profile_fn =  'feature_' +  eo_feature + '.json'
            eo_feature_link = {'rel': 'metadata/features/' + eo_feature,
                               'href':  './' + eo_feature_profile_fn,
                               'type': 'application/geo+json' }
            tds_ctl_root_metadata_d['links'].append(eo_feature_link)
            
            # save global feature profile json
            eo_feature_profile_metadata_d = self.tds_ctl_root_info.g_all_field_metadata.features[eo_feature].metadata_d
            eo_feature_profile_metadata_d['links'] = []
            eo_feature_profile_self_link = \
                    {
                      'rel': 'self',
                       'href': './' + eo_feature_profile_fn,
                         'type': 'application/json'}
                    
            eo_feature_profile_metadata_d['links'].append(eo_feature_profile_self_link)
            eo_feature_profile_parent_link = \
                    {
                      'rel': 'parent',
                       'href': './' + str(tds_catalog_root_fn),
                         'type': 'application/json'}
                    
            eo_feature_profile_metadata_d['links'].append(eo_feature_profile_parent_link)
            eo_feature_profile_root_link = \
                    {
                      'rel': 'root',
                       'href': './' + str(tds_catalog_root_fn),
                         'type': 'application/json'}
                    
            eo_feature_profile_metadata_d['links'].append(eo_feature_profile_root_link)
            with open(tds_catalog_root_folder / eo_feature_profile_fn, 'w') as eo_feature_profile_f:
                json.dump(eo_feature_profile_metadata_d, eo_feature_profile_f, indent=4)


        for reference_data in self.field_schema.references:
            reference_data_profile_fn =  'reference_data_' +  reference_data + '.json'
            reference_data_link = {'rel': 'metadata/references/' + reference_data,
                               'href':  './' + reference_data_profile_fn,
                               'type': 'application/geo+json' }
            tds_ctl_root_metadata_d['links'].append(reference_data_link)
            # save global reference data profile json
            
            ref_data_profile_metadata_d = \
                self.tds_ctl_root_info.g_all_field_metadata.references[reference_data].metadata_d           
            ref_data_profile_metadata_d['links'] = []
            ref_data_profile_self_link = \
                    {
                      'rel': 'self',
                       'href': './' + reference_data_profile_fn,
                       'type': 'application/json'}
                    
            ref_data_profile_metadata_d['links'].append(ref_data_profile_self_link)
            ref_data_profile_parent_link = \
                    {
                      'rel': 'parent',
                       'href': './' + str(tds_catalog_root_fn),
                        'type': 'application/json'}
                    
            ref_data_profile_metadata_d['links'].append(ref_data_profile_parent_link)
            ref_data_profile_root_link = \
                    {
                      'rel': 'root',
                       'href': './' + str(tds_catalog_root_fn),
                       'type': 'application/json'}
                    
            ref_data_profile_metadata_d['links'].append(ref_data_profile_root_link)
            with open(tds_catalog_root_folder / reference_data_profile_fn, 'w') as ref_data_profile_f:
                json.dump(ref_data_profile_metadata_d, ref_data_profile_f, indent=4)



        # generate and create subfolders for all AOI + time
        for aoi_collection_info in self.aoi_collection_info_l:
            aoi_collection_id = aoi_collection_info.aoi_collection_metadata_d.get('id')
            aoi_collection_fn = aoi_collection_id + '.json'
            # use AOI identifier to  create its dictionary
            aoi_collection_folder = tds_catalog_root_folder / str(aoi_collection_id)
            aoi_collection_folder.mkdir(parents=True)
            # add aoi collection json link to tds_ctl_root_metadata_d['links'] 
            aoi_collection_child_link = \
                    {'rel': 'child',
                     'href': './' + str(aoi_collection_id) + '/' + str(aoi_collection_id) + '.json',
                     'type': 'application/json'}

            tds_ctl_root_metadata_d['links'].append(aoi_collection_child_link)
                     

            aoi_collection_metadata_d =  generate_aoi_collection_json_dict(aoi_collection_info, tds_catalog_root_folder, tds_catalog_root_fn)
            
            # save aoi_collection json file
            with open(aoi_collection_folder / aoi_collection_fn, 'w') as aoi_collection_f:
                json.dump(aoi_collection_metadata_d, aoi_collection_f, indent=4)

            # save aoi eo feature profile and ref data profile jsons
            # eo feature profile
            for eo_feature in self.field_schema.features:
                eo_feature_profile_metadata_d = aoi_collection_info.aoi_all_field_metadata.features[eo_feature].metadata_d
                eo_feature_profile_fn = 'feature_' + eo_feature + '.json'
                eo_feature_profile_metadata_d['links'] = []
                eo_feature_profile_self_link = \
                        {
                          'rel': 'self',
                           'href': './' + eo_feature_profile_fn,
                             'type': 'application/geo+json'}
                        
                eo_feature_profile_metadata_d['links'].append(eo_feature_profile_self_link)
                eo_feature_profile_parent_link = \
                        {
                          'rel': 'parent',
                           'href': './' + aoi_collection_fn,
                             'type': 'application/json'}
                        
                eo_feature_profile_metadata_d['links'].append(eo_feature_profile_parent_link)
                eo_feature_profile_root_link = \
                        {
                          'rel': 'root',
                           'href': '../' + str(tds_catalog_root_fn),
                             'type': 'application/json'}
                        
                eo_feature_profile_metadata_d['links'].append(eo_feature_profile_root_link)

                # copy eo feature asset over and add eo feature asset
                orig_eo_feature_asset_path = \
                        Path(aoi_collection_info.aoi_all_field_metadata.features[eo_feature].data_asset_w_path) 
                eo_feature_asset_fn = orig_eo_feature_asset_path.name
                dest_eo_feature_asset_path = aoi_collection_folder / eo_feature_asset_fn
                copyfile(orig_eo_feature_asset_path, dest_eo_feature_asset_path)

                eo_feature_profile_metadata_d['assets'] = {}
                eo_feature_profile_metadata_d['assets']['data'] = \
                        {
                            'href': './' + str(eo_feature_asset_fn),
                            'roles': 'data'
                        }


                with open(aoi_collection_folder / eo_feature_profile_fn, 'w') as eo_feature_profile_f:
                    json.dump(eo_feature_profile_metadata_d, eo_feature_profile_f, indent=4)

            for reference_data in self.field_schema.references:
                ref_data_profile_metadata_d = aoi_collection_info.aoi_all_field_metadata.references[reference_data].metadata_d
                ref_data_profile_fn = 'reference_data_' + reference_data + '.json'
                ref_data_profile_metadata_d['links'] = []
                ref_data_profile_self_link = \
                        {
                          'rel': 'self',
                           'href': './' + ref_data_profile_fn,
                             'type': 'application/geo+json'}
                        
                ref_data_profile_metadata_d['links'].append(ref_data_profile_self_link)
                
                ref_data_profile_parent_link = \
                        {
                          'rel': 'parent',
                           'href': './' + aoi_collection_fn,
                             'type': 'application/json'}
                        
                ref_data_profile_metadata_d['links'].append(ref_data_profile_parent_link)

                ref_data_profile_root_link = \
                        {
                          'rel': 'root',
                           'href': '../' + str(tds_catalog_root_fn),
                             'type': 'application/json'}
                        
                ref_data_profile_metadata_d['links'].append(ref_data_profile_root_link)

                # copy reference data asset over and add reference data asset
                orig_ref_data_asset_path = \
                        Path(aoi_collection_info.aoi_all_field_metadata.references[reference_data].data_asset_w_path) 
                ref_data_asset_fn = orig_ref_data_asset_path.name
                dest_ref_data_asset_path = aoi_collection_folder / ref_data_asset_fn
                copyfile(orig_ref_data_asset_path, dest_ref_data_asset_path)
                ref_data_profile_metadata_d['assets'] = {}
                ref_data_profile_metadata_d['assets']['data'] = \
                        {
                            'href': './' + str(ref_data_asset_fn),
                            'roles': 'data'
                        }

                with open(aoi_collection_folder / ref_data_profile_fn, 'w') as ref_data_profile_f:
                    json.dump(ref_data_profile_metadata_d, ref_data_profile_f, indent=4)


        # save root catalog json
        with open(tds_catalog_root_folder / tds_catalog_root_fn, 'w') as tds_catalog_root_f:
            json.dump(tds_ctl_root_metadata_d, tds_catalog_root_f, indent=4)


