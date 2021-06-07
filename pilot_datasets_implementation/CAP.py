import rioxarray
import os
import math
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt


class AOIDatasetCAP:
    """
    This class is to load and to store all data (input features/ reference data) for one area of interest. An area of interest is defined by its bounding box, its geometry, and its time interval. For each specific EO TDS the user needs to create a subclass of AOIDataset and implements its abstract methods.
    """

    def __init__(self, AOI_STAC_collection, metadata):
        """
        Parse and load data for one area of interest given the aoi json file, and additional metadata (e.g. provided by an EOTrainingDataset object )
        :param AOI_STAC_collection:
        :param metadata:
        """
        self.AOI_STAC_collection = AOI_STAC_collection
        self.metadata = metadata
        feature_x = rioxarray.open_rasterio(metadata['aoi_feature_data_path'])
        #         self.feature_data = gdal.Open(metadata['aoi_feature_data_path']).ReadAsArray()
        reference_x = rioxarray.open_rasterio(metadata['aoi_reference_data_path']).rename({'band': 'mask'})
        #         self.reference_data = gdal.Open(metadata['aoi_reference_data_path']).ReadAsArray()

        self.data = feature_x.to_dataset(name='feature_data')

        # Add second DataArray to existing dataset
        self.data['reference_data'] = reference_x

    def __getitem__(self, index):
        """
        Function to return one example of the AOI given its index, to be implemented by the dataset user.
        :param index:
        :return:
        """

        along_x = int((self.data.feature_data.shape[1] - self.metadata['window_size']) / self.metadata['stride'])
        along_y = int((self.data.feature_data.shape[-1] - self.metadata['window_size']) / self.metadata['stride'])
        x1 = self.metadata['stride'] * int(index % along_x)
        y1 = self.metadata['stride'] * int(index / along_y)
        x2 = x1 + self.metadata['window_size']
        y2 = y1 + self.metadata['window_size']

        # store feature and reference data in same xarray, name the axes
        ds = self.data.isel(band=[0, 1, 2, 3], mask=[0], x=slice(x1, x2), y=slice(y1, y2))
        return ds

    def __len__(self):
        """
        Function to return the number of examples in one area of interest, to be implemented by the dataset user. In future we will consider the case where the dataset can generate examples dynamically
        :return:
        """
        along_x = int((self.data.feature_data.shape[1] - self.metadata['window_size']) / self.metadata['stride'])
        along_y = int((self.data.feature_data.shape[-1] - self.metadata['window_size']) / self.metadata['stride'])
        return along_x * along_y


import matplotlib.pyplot as plt


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
        data = EOTDS.__getitem__(ex_index)
        figs = []
        for field_name in field_names:

            fig = plt.figure()
            if field_name == 'reference_data':
                # adding a color palette
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
        xr.DataArray(AOIDataset_object.data.feature_data).plot.imshow()
        reference_img = plt.figure()
        xr.DataArray(AOIDataset_object.data.reference_data).plot()
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
        self.tds_catalog = tds_catalog_path  # change later
        self.aoi_objs = []
        self.lengths = []
        # assuming paths to all aoi are stored in tds_catalog
        for aoi_stac, aoi_metadata in zip(self.tds_catalog['aois_stac_collection'], self.tds_catalog['aois_metadata']):
            self.aoi_objs.append(aoi_dataset_class(aoi_stac, aoi_metadata))

        ctr = 0
        for obj in self.aoi_objs:
            ctr += len(obj)
            self.lengths.append(ctr)

    def __getitem__(self, index):
        """
        Returns an example of the EO TDS given its index
        :param index:
        :return:
        """

        # get AOI index
        found = False
        for idx, length in enumerate(self.lengths):
            if length > index and not found and idx == 0:
                found = True
                loc = 0
            elif length > index and not found:
                found = True
                loc = idx - 1
            elif length == index and not found:
                found = True
                loc = idx
        aoi = self.aoi_objs[loc]
        zero_idx = self.lengths[loc]
        return aoi.__getitem__(index - zero_idx)

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
        from operator import itemgetter
        return list(itemgetter(*index_arr)(self))

    #         subset = self.__getitem__(index_arr[0])
    #         if data_type=='xarray':
    #             for idx in index_arr[1:]:
    #                 subset = xr.concat([subset, self.__getitem__(idx)], dim='instance')
    #         return subset

    def pre_process(self):
        """
        Can be used to standardize data across different AOIs, will be implemented by the dataset creator/user in v0.
        :return:
        """

        def select_top_10(x):
            top_10 = [990, 717, 138, 716, 105, 110, 109, 715, 308,
                      707, ]  # 116, 636, 771, 634, 142, 901, 301, 111, 651, 751]
            if x in top_10:
                return x
            else:
                return 0

        vfunc = np.vectorize(select_top_10)

        for obj in self.aoi_objs:
            #             obj.data.update({'reference_data': ('mask', vfunc(obj.data.reference_data.values))})
            obj.data['reference_data'].values = vfunc(obj.data.reference_data.values)

    def get_example(self, index, data_type='xarray'):
        """
        Returns an example (pair of inputs/labels) given its index. If the data_type is ‘numpy’ it returns one example in the format tuple((inputs), (labels)), if the data_type is ‘xarray’ it returns an xarray dataset object.
        :param index:
        :param data_type:
        :return:
        """
        pass

    def get_train_val_test_split(self):
        """
        Will be implemented by the dataset user, it  returns a dictionary:{‘train’: index_array, ‘val’:index_array, ‘test: ‘index_array’}.
        :return:
        """
        import os
        patches = [i[i.rfind('_') + 1:i.find('.')] for i in os.listdir('./AIREO_datasets/cap_tiff_mask')]
        patches.remove('')
        patches = [int(patch) for patch in patches]
        patches.sort()
        num_test = int(len(patches) * 0.15)
        splits = {'test': patches[:num_test],
                  'validation': patches[num_test:2 * num_test],
                  'train': patches[2 * num_test:]}
        return splits

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
        # stats of each channel aoi feature_data
        all_stats = []
        for i, obj in enumerate(EOTDS.aoi_objs):
            for j in range(0, obj.data.feature_data.shape[0]):
                stats = {}
                stats['AOI'] = i
                stats['Channel'] = j
                stats['mean'] = AOI_obj.data.feature_data[j, :, :].mean().values.tolist()
                stats['std'] = AOI_obj.data.feature_data[j, :, :].std().values.tolist()
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
            update_stats(Counter(obj.data.reference_data.values.flatten()))
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

