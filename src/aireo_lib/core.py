from abc import abstractmethod

import numpy as np
import xarray as xr

#from collections import namedtuple
import typing
from typing import NamedTuple

from aireo_lib.tds_stac_io import DatasetSTACCatalog 
from aireo_lib import tds_stac_io


#TDSExIndexMap = namedtuple("TDSExIndexMap", ["aoi_idx", "aoi_ex_idx"])
class TDSExIdx2AOIIndexMap(NamedTuple):
    """
    Map from a TDS example index to a pair of aoi idx and the ex idx in that AOI
    """
    aoi_idx: int
    aoi_ex_idx: int

class TrainValTestSplit(NamedTuple):
    ds_split_exists: bool = False
    # list of aoi indexes for train split
    # Use None instead of empty list
    train_split: typing.Union[typing.List[int], None] = None
    val_split: typing.Union[typing.List[int], None] = None
    test_split: typing.Union[typing.List[int], None] = None

    


class EOTrainingDataset:
    """
    An abstract class that represents one EO training dataset, it uses a list of AOIDataset 
    objects to store data for each specific area of interest. If the dataset creator needs 
    to provide a customized functionality for a specific EO TDS 
    (e.g. returning train/validation/test splits, the dataset creator can create a subclass 
    of the class EOTrainingDataset for these functionalities. All the eo feature data and 
    reference data should be standardized  before being stored in a
    EOTrainingDataset object.

    The constructor function takes in the path to a TDS catalog and an AOIDataset class to initiate an EOTrainingDataset object. The AOIDataset_class class is a subclass of the class AOIDataset that corresponds to the specific EO TDS. Initially it needs to be implemented by the dataset creator/user, but potentially could be generated automatically from the data profile in future versions of
    the library.

    :param tds_catalog_path: Path to the training dataset catalog json.
    :type tds_catalog_path: str
    :param aoi_dataset_class: Class for the AOIDataset, defined by dataset creator
    :type aoi_dataset_class: class

    """

    def __init__(self, tds_catalog_path, aoi_dataset_class):

        self.tds_ctl_o = DatasetSTACCatalog.from_TDSCatalog(tds_catalog_path)

        self.aoi_ds_l = []

        for aoi_collection_info in self.tds_ctl_o.aoi_collection_info_l:
            aoi_ds = aoi_dataset_class(aoi_collection_info, self.tds_ctl_o)
            self.aoi_ds_l.append(aoi_ds)


        self.n_exs = self.__compute_ds_length()

        # do any  necessary preprocesing 
        self.pre_process()


    def __compute_ds_length(self):
        """
        Computes the number of examples in the EO TDS.
        Populates the mapping from each tds ex idx to a pair of aoi idx and the example index
        in that aoi
        """
        n_exs = 0

        aoi_2_n_ex = {}

        # map from one aoi_idx to the first tds ex idx  allocated to it in the tds 
        aoi_2_tds_start_idx = np.zeros(len(self.aoi_ds_l) + 1, dtype=int)
        for aoi_idx, aoi_ds in enumerate(self.aoi_ds_l):
            aoi_2_tds_start_idx[aoi_idx] = n_exs
            n_ex_aoi = aoi_ds.get_length()
            n_exs += n_ex_aoi

        aoi_2_tds_start_idx[len(self.aoi_ds_l)]  = n_exs 

        # To store the mapping from each tds example index to the corresponding
        # pair of aoi_idx, and aoi example idx
        self.tds_ex_idx_2_aoi_ex_idx = np.empty(n_exs, dtype=object)
        # map from on tds ex idx to a pair of aoi idx + aoi ex_idx
        for aoi_idx in range(len(self.aoi_ds_l)):
            aoi_tds_ex_idx_start = aoi_2_tds_start_idx[aoi_idx]
            aoi_tds_ex_idx_end = aoi_2_tds_start_idx[aoi_idx + 1]

            for tds_ex_idx in np.arange(aoi_tds_ex_idx_start, aoi_tds_ex_idx_end):
                aoi_ex_idx = tds_ex_idx - aoi_tds_ex_idx_start
                ex_idx_map = TDSExIdx2AOIIndexMap(aoi_idx, aoi_ex_idx)
                self.tds_ex_idx_2_aoi_ex_idx[tds_ex_idx] = ex_idx_map
        
        return n_exs 


    def __getitem__(self, ex_index):
        """
        Returns an example of the EO TDS given its index
        :param ex_index: Index of the example to return
        :type ex_index: int
        :return: an example of the TDS as an xarray dataset
        :rtype: xarray.Dataset
        """
        aoi_idx, aoi_ex_idx = self.tds_ex_idx_2_aoi_ex_idx[ex_index]
        return self.aoi_ds_l[aoi_idx][aoi_ex_idx]



    def __len__(self):
        """
        Returns the number of examples in the EO TDS
        :return: number of examples in the EO TDS
        """
        return self.n_exs

    

    def get_subset(self, index_arr, data_type='xarray'):
        """
        Returns a subset of examples of the dataset, the return type could be xarray dataset or numpy array.

        :param index_arr: the indexes of the examples
        :type index_arr: list[int]
        :param data_type: type of each returned example
        :return: A list of xarray's
        :rtype: xarray.Dataset
        """
        # will update this in future
        return [self.get_example(ex_idx) for ex_idx in index_arr]
        #raise Exception('Needs to be implemented in the subclass of EOTrainingDataset!')

    def pre_process(self):
        """
        Can be used to standardize data across different AOIs, will be implemented by the dataset creator/user in v0.
        """
        pass

    def get_example(self, index, data_type='xarray'):
        """
        Returns an example (pair of inputs/labels) given its index. If the data_type is ‘numpy’ it returns one example in the format tuple((inputs), (labels)), if the data_type is ‘xarray’ it returns an xarray dataset object.
        :param index: index of the example
        :type index: int
        :param data_type: type of the returned example (support's xarray)
        :type data_type: str
        :return: an example of the EO TDS
        :rtype: xarray.Dataset
        """
        return self.__getitem__(index) 

    def get_train_val_test_split(self):
        """
        Will be implemented by the dataset creator if it exists, it  returns a dictionary:{‘train’: index_array, ‘val’:index_array, ‘test: ‘index_array’}.
        :return: a dictionary that specifies the train split, the validation split, and the test split 
        """
        return TrainValTestSplit(ds_split_exists=False, train_split=None, val_split=None, test_split=None)

    def get_aoi_dataset(self, aoi_index):
        """
        Returns the AOIDataset object for one area of interest (AOI).

        :param aoi_index: The index of the AOI to return:
        :type aoi_index: int
        :return: the AOIDataset object
        """
        return self.aoi_ds_l[aoi_index] 

    def get_n_aoi(self):
        """
        Returns the number of AOIs in the dataset
        """
        return len(self.aoi_ds_l)

    def get_aoi_datasets(self):
        """
        Get the list the AOI dataset objects available in the EO TDS.

        :return: List of AOI datasets
        :rtype: list
        """
        return self.aoi_ds_l

    def get_field_names(self):
        """
        :returns: the field schema of the TDS
        :rtype: dict
        """
        return self.tds_ctl_o.field_schema


class AOIDataset:
    """
    This class is to load and to store all data (input EO features/ reference data) for one 
    area of interest (AOI). An AOI is defined by its bounding box, its geometry,
    and its time interval. For each specific EO TDS the dataset
    creator needs to create a subclass of AOIDataset and implements its abstract methods.

    Parse and load data for one area of interest given the aoi collection information,
    and the EOTDS STAC catalog object

    :param aoi_collection_info: Dictionary of AOI metadata
    :type aoi_colllection_info: dict
    :param tds_ctl_o: The training dataset catalog object
    :type tds_ctl_o: aireo_lib.core.EOTrainingDataset

    """
    def __init__(self, aoi_collection_info, tds_ctl_o):

        aoi_collection_fn = aoi_collection_info.fn_path
        # TO be implemented in the subclass

    @abstractmethod
    def __getitem__(self, index):
        """
        Function to return one example of the AOI given its index, to be implemented by the 
        dataset creator.
        :param index: the example index to return
        :type index: int
        :return: an example in  the xarray dataset format
        """
        pass

    @abstractmethod
    def get_length(self):
        """
        Function to return the number of examples in one area of interest, to be implemented
        by the dataset creator/user. In future we will consider the case where the dataset can 
        generate examples dynamically
        :return: number of examples in the AOI
        :rtype: int
        """
        pass

    def pre_proces(self):
        """
        If necessary the dataset creator/user can implement this method to do
        all  the necessary preprocessing steps here, including data alignment
        """
        pass



