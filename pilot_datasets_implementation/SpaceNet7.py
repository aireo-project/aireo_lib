import rioxarray
import os
import math
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import math
import sys


class AOIDatasetSpaceNet:
    """
    This class is to load and to store all data (input features/ reference data) for one area of interest. An area of interest is defined by its bounding box, its geometry, and its time interval. For each specific EO TDS the user needs to create a subclass of AOIDataset and implements its abstract methods.
    """

    def __init__(self, AOI_path, metadata = {'window_size':100,'stride':100}):
        
        
        
        #load images with unusable data masks applied
        feature_data = xr.open_dataarray(AOI_path+'/images_masked.nc')        
        #load building masks
        reference_data = xr.open_dataarray(AOI_path+'/building_masks.nc').rename({'band':'mask'})       
        #load matched label dataframes

        self.timesteps = self.feature_data['date'].values

        self.data = self.feature_data.to_dataset(name='feature_data')

        # Add second DataArray to existing dataset
        self.data['reference_data'] = self.reference_data


        self.metadata = metadata

    def __getitem__(self, index):        

        if index >= len(self):
            sys.exit('index out of range')

        sample_image = self.feature_data[0]
        x1_ceiling = int((sample_image.shape[1]-self.metadata['window_size'])/self.metadata['stride']) +1
        y1_ceiling = int((sample_image.shape[2]-self.metadata['window_size'])/self.metadata['stride']) +1
        single_image_examples = x1_ceiling*y1_ceiling
        timestep = int(index/single_image_examples)
        image = self.feature_data[timestep]
        image_index = index - timestep*single_image_examples
        x1 = self.metadata['stride']*(image_index%x1_ceiling)
        y1 = self.metadata['stride']*(int(image_index/x1_ceiling))
        x2 = x1+self.metadata['window_size']
        y2 = y1+self.metadata['window_size']
        date = self.timesteps[timestep]

        image = image[:,x1:x2,y1:y2]
        building_mask = self.reference_data[timestep,x1:x2,y1:y2]
        
        
        ds = self.data.isel(date=[timestep],band=[0,1,2,3],x=slice(x1,x2),y=slice(y1,y2)).squeeze()
        
        return ds

    # return the number of timesteps     
    def __len__(self):
        sample_image = self.feature_data[0]
        x1_ceiling = int((sample_image.shape[1]-self.metadata['window_size'])/self.metadata['stride']) +1
        y1_ceiling = int((sample_image.shape[2]-self.metadata['window_size'])/self.metadata['stride']) +1
        single_image_examples = int(x1_ceiling)*int(y1_ceiling)
        return len(self.timesteps)*single_image_examples


        


class EOTDSPlot:
    """
    To provide visualization functions.
    """

    @staticmethod
    def plot_example(EOTDS, ex_index, field_names):
        """
        Plot one example
        :param EOTDS:
        :param ex_index:
        :param field_names:
        :return:
        """
        data = EOTDS[ex_index]
        figs = []
        for field_name in field_names:

            fig = plt.figure()
            if field_name == 'reference_data':
                data[field_name].plot()
            elif field_name == 'feature_data':
                data[field_name].plot.imshow()
            else:
                raise ValueError('field_names not found in dataset')
            figs.append(fig)
        return figs

    @staticmethod
    def plot_aoi_dataset(AOIDataset_object):
        """
        Plot the geometry of one area of interest object
        :param AOIDataset_object:
        :return:
        """
        feature_img = plt.figure()
        xr.DataArray(AOIDataset_object.feature_data).plot.imshow()
        reference_img = plt.figure()
        xr.DataArray(AOIDataset_object.reference_data).plot()
        return feature_img, reference_img


class EOTrainingDataset:
    """
    An abstract class that represents one EO training dataset, it uses a list of AOIDataset objects to store data for each specific area of interest. For each specific EO TDS the user needs to create a subclass of the class EOTrainingDataset and implements the abstract methods. All the data has been standardized (for each field) when being stored in a EODataset object.
    """

    def __init__(self, tds_catalog_path, aoi_dataset_class):
        """
        The constructor function takes in the path to a TDS catalog and an AOIDataset class to initiate an EOTrainingDataset object. The AOIDataset_class class is a subclass of the class AOIDataset that corresponds to the specific EO TDS. Initially it needs to be implemented by the dataset creator/user, but potentially could be generated automatically from the data profile in future versions of
        the library.
        :param tds_catalog_path:
        :param aoi_dataset_class:
        """
        AOI_folders = os.listdir('./spacenet-netcdf-1000x1000')
        self.aoi_objs = []
        for folder in AOI_folders[0:5]:
            if folder[0] != '.':
                path = './spacenet-netcdf-1000x1000/'+folder
                self.aoi_objs.append(aoi_dataset_class(path))
            else:
                next

        self.tds_catalog_path = tds_catalog_path

    def __getitem__(self, index):
        """
        Returns an example of the EO TDS given its index
        :param index:
        :return:
        """
        TDS_length = len(self)
        if index > TDS_length:
            sys.exit("index out of range")
        counter = 0
        AOI_index = 0
        while counter < len(self):
            aoi = self.aoi_objs[AOI_index]
            if index < len(aoi) + counter:
                return aoi[index-counter]
            else:
                counter += len(aoi)
                AOI_index += 1

    def __len__(self):
        """
        Returns the number of examples in the EO TDS
        :return:
        """
        ctr = 0
        for obj in self.aoi_objs:
            ctr += len(obj)
        return ctr

    def get_subset(self, index_arr, data_type='xarray'):
        """
        Returns a subset of examples of the dataset, the return type could be xarray dataset or numpy array.

        :param index_arr:
        :param data_type:
        :return:
        """
        subset = []
        if data_type == 'xarray':
            for i in index_arr:
                subset.append(self[i])
        elif data_type == 'numpy':
            for i in index_arr:
                example = self[i]
                feature = example['feature_data'].values
                ref = example['reference_data'].values
                subset.append((feature,ref))
        return subset

    def pre_process(self):
        """
        Can be used to standardize data across different AOIs, will be implemented by the dataset creator/user in v0.
        :return:
        """
        pass

    def get_example(self, index, data_type='xarray'):
        """
        Returns an example (pair of inputs/labels) given its index. If the data_type is ‘numpy’ it returns one example in the format tuple((inputs), (labels)), if the data_type is ‘xarray’ it returns an xarray dataset object.
        :param index:
        :param data_type:
        :return:
        """
        
        if data_type == 'xarray':
            return self[index]
        elif data_type == 'numpy':
            feature_data = self[index]['feature_data'].values
            reference_data = self[index]['reference_data'].values
            return feature_data, reference_data

    def get_train_val_test_split(self):
        """
        Will be implemented by the dataset user, it  returns a dictionary:{‘train’: index_array, ‘val’:index_array, ‘test: ‘index_array’}.
        :return:
        """
        pass

    def get_aoi_dataset(self, aoi_index):
        """
        Returns the AOIDataset object for one area of interest.

        :param aoi_index:
        :return:
        """
        return self.aoi_objs[aoi_index]

    def list_aoi_datasets(self):
        """
        Lists the AOI dataset objects available in the EO TDS.

        :return:
        """
        print(self.aoi_objs)

    def get_field_names(self):
        """
        Lists the fields in TDS.
        :return:
        """
        pass


class EOTDSStatistics:
    """
    To provide statistics of an EO TDS. Statistics calculated on first call, then cached (?)
    """

    @staticmethod
    def describe(EOTDS, field_name):
        """
        Provide statistics of one field of an EO TDS.
        :param EOTDS:
        :param field_name:
        :return:
        """
        pass

    @staticmethod
    def metadata_statistics(EOTDS):
        """
        Provide metadata statistics for one EO TDS.
        :param EOTDS:
        :return:
        """
        pass

    @staticmethod
    def feature_data_statistics(EOTDS):
        """
        Provide statistics for feature data of an EO TDS
        :param EOTDS:
        :return:
        """
        #stats of each channel aoi feature_data
        all_stats = []
        for i, obj in enumerate(EOTDS.aoi_objs):
            for j, image in enumerate(obj.data['feature_data']):
                for k in range(0, image.shape[0]):
                    stats = {}
                    stats['AOI'] = i
                    stats['image'] = j
                    stats['Channel'] = k
                    stats['mean'] = image[k, :, :].mean().values.tolist()
                    stats['std'] = image[k, :, :].std().values.tolist()
                    all_stats.append(stats)
        return all_stats

    @staticmethod
    def reference_data_statistics(EOTDS):
        """
        Provide statistics for reference data of an EO TDS
        :param EOTDS:
        :return:
        """
        # returns number of pixels for each field type
        from collections import Counter
        stats = {}

        def update_stats(aoi_stats):
            for key in aoi_stats.keys():
                if key in stats.keys():
                    stats[key] += aoi_stats[key]
                else:
                    stats[key] = aoi_stats[key]

        for obj in EOTDS.aoi_objs:
            update_stats(Counter(obj.data['reference_data'].values.flatten()))
        return stats

    @staticmethod
    def dataset_statistics(EOTDS):
        """
        Provide statistics for one EO TDS: number of examples, statistics for its fields.
        :param EOTDS:
        :return:
        """
        pass


if __name__ == "__main__":
    metadata = {'aoi_feature_data_path': 'AIREO_datasets/cap_tiff/patch_2.tif',
                'aoi_reference_data_path': 'AIREO_datasets/cap_tiff_mask/patch_mask_2.tif',
                'stride': 26,
                'window_size': 256
                }
    AOI_obj = AOIDatasetCAP('test', metadata)
    data_xar = AOI_obj.__getitem__(6)
    print(data_xar.reference_data)
    print(data_xar.feature_data)
    plots = EOTDSPlot.plot_aoi_dataset(AOI_obj)
    tds_catalog_metadata = {}
    tds_catalog_metadata['aois_stac_collection'] = ['test' for i in range(7)]
    tds_catalog_metadata['aois_metadata'] = [{'aoi_feature_data_path': 'AIREO_datasets/cap_tiff/patch_0.tif',
                                              'aoi_reference_data_path': 'AIREO_datasets/cap_tiff_mask/patch_mask_0.tif',
                                              'stride': 26,
                                              'window_size': 256},
                                             {'aoi_feature_data_path': 'AIREO_datasets/cap_tiff/patch_1.tif',
                                              'aoi_reference_data_path': 'AIREO_datasets/cap_tiff_mask/patch_mask_1.tif',
                                              'stride': 26,
                                              'window_size': 256},
                                             {'aoi_feature_data_path': 'AIREO_datasets/cap_tiff/patch_2.tif',
                                              'aoi_reference_data_path': 'AIREO_datasets/cap_tiff_mask/patch_mask_2.tif',
                                              'stride': 26,
                                              'window_size': 256},
                                             {'aoi_feature_data_path': 'AIREO_datasets/cap_tiff/patch_3.tif',
                                              'aoi_reference_data_path': 'AIREO_datasets/cap_tiff_mask/patch_mask_3.tif',
                                              'stride': 26,
                                              'window_size': 256},
                                             {'aoi_feature_data_path': 'AIREO_datasets/cap_tiff/patch_4.tif',
                                              'aoi_reference_data_path': 'AIREO_datasets/cap_tiff_mask/patch_mask_4.tif',
                                              'stride': 26,
                                              'window_size': 256},
                                             {'aoi_feature_data_path': 'AIREO_datasets/cap_tiff/patch_5.tif',
                                              'aoi_reference_data_path': 'AIREO_datasets/cap_tiff_mask/patch_mask_5.tif',
                                              'stride': 26,
                                              'window_size': 256},
                                             {'aoi_feature_data_path': 'AIREO_datasets/cap_tiff/patch_6.tif',
                                              'aoi_reference_data_path': 'AIREO_datasets/cap_tiff_mask/patch_mask_6.tif',
                                              'stride': 26,
                                              'window_size': 256},
                                             ]
    cap_TDS = EOTrainingDataset(tds_catalog_metadata, AOIDatasetCAP)
    EOTDSPlot.plot_example(cap_TDS, 2, ['feature_data', 'reference_data'])
    plots = EOTDSPlot.plot_aoi_dataset(AOI_obj)
    print(EOTDSStatistics.reference_data_statistics(cap_TDS))
    EOTDSStatistics.feature_data_statistics(cap_TDS)

