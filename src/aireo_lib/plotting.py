import matplotlib.pyplot as plt


class EOTDSPlot:
    """
    To provide visualization functions for a training dataset object.
    """

    @staticmethod
    def plot_example(EOTDS, ex_index, field_names):
        """
        Plots all the fields in field_names and returns a dictionary of matplotlib figures for each field.

        :param EOTDS: The training dataset object
        :type EOTDS: aireo_lib.core.EOTrainingDataset
        :param ex_index: Index of the example of the training dataset to plot
        :type ex_index: int
        :param field_names: List of fields or variables in the dataset to plot
        :type field_names: list
        :returns: A dictionary of plots of different fields in field_names
        :rtype: dict

        **Example usage**
        ::
            from aireo_lib.core import EOTrainingDataset
            from aireo_lib.plotting import EOTDSPlot as aireo_viz
            from pathlib import Path

            cap_tds_ctl_fn = Path('/home/jovyan/s3/CAP/cap_stac_generated/TDS.json')
            eo_tds_obj = EOTrainingDataset(cap_tds_ctl_fn, AOIDatasetCAP)

            plot_d = aireo_viz.plot_example(EOTDS=eo_tds_obj,
                                               ex_index=-50,
                                               field_names=['features_input1', 'references_output1'])
            plot_d
        """
        figs = {}
        data = EOTDS[ex_index]
        for field_name in data.data_vars:
            if field_name in field_names:
                fig = plt.figure()
                data[field_name].plot()
                figs[field_name] = fig
            else:
                raise ValueError('field_names not found in dataset')
        return figs


    @staticmethod
    def plot_aoi_dataset(AOIDataset_object):
        """
        Plots all the variables of an AOI object (Area of Interest)
         and returns a dictionary of matplotlib figures for each variable.

        :param EOTDS: The training dataset object
        :type EOTDS: aireo_lib.core.EOTrainingDataset
        :returns: A dictionary of plots of different fields in field_names
        :rtype: dict

        **Example usage**
        ::
            from aireo_lib.core import EOTrainingDataset
            from aireo_lib.plotting import EOTDSPlot as aireo_viz
            from pathlib import Path

            cap_tds_ctl_fn = Path('/home/jovyan/s3/CAP/cap_stac_generated/TDS.json')
            eo_tds_obj = EOTrainingDataset(cap_tds_ctl_fn, AOIDatasetCAP)
            aoi_obj = eo_tds_obj.get_aoi_dataset(2) # get second AOI object from the TDS

            aoi_plots_d = aireo_viz.plot_aoi_dataset(aoi_obj)

        """
        figs = {}
        for field_name in AOIDataset_object.data.data_vars:
            fig = plt.figure()
            AOIDataset_object.data[field_name].plot()
            figs[field_name] = fig
        return figs
        # # determine which data profiles are present
        # data_profiles = AOIDataset_object.metadata['stac_extensions']
        # features_d = EOTDS.tds_ctl_o.tds_ctl_root_info.g_all_field_metadata.features
        # #if geoimage then simply plot
        #
        # if "georeferenced_eo_image" in data_profile:
        #     feature_img = plt.figure()
        #     xr.DataArray(AOIDataset_object.data.feature_data).plot.imshow()
        #     reference_img = plt.figure()
        #     xr.DataArray(AOIDataset_object.data.reference_data).plot()
        #     return feature_img, reference_img
        #
        # # if datacube then just plot first slice
        #
        # elif "georeferenced_eo_datacube" in data_profiles:
        #     feature_img = plt.figure()
        #     xr.DataArray(AOIDataset_object.data['feature_data'][0]).plot.imshow()
        #     reference_img = plt.figure()
        #     xr.DataArray(AOIDataset_object.data['reference_data'][0]).plot()
        #     return feature_img, reference_img




    @staticmethod
    def plot_eotds(EOTDS, AOI_indexes):
        """
        Plots all the AOIs (Area of Interests) in AOI_indexes of a training dataset.
         All variables of an AOI object are plotted. It returns a list with dictionaries
         of matplotlib figures for each AOI.

        :param EOTDS: The training dataset object
        :type EOTDS: aireo_lib.core.EOTrainingDataset
        :param AOI_indexes: A list of indexes of the AOIs to plot.
        :type AOI_indexes: list[int]
        :returns: A dictionary of plots of different fields in field_names
        :rtype: list[dict]

        **Example usage**
        ::
            from aireo_lib.core import EOTrainingDataset
            from aireo_lib.plotting import EOTDSPlot as aireo_viz
            from pathlib import Path

            cap_tds_ctl_fn = Path('/home/jovyan/s3/CAP/cap_stac_generated/TDS.json')
            eo_tds_obj = EOTrainingDataset(cap_tds_ctl_fn, AOIDatasetCAP)
            aoi_idxs = [0, 1, 3, 5]

            aoi_plots_d = aireo_viz.plot_eotds(EOTDS=eo_tds_obj, AOI_indexes=aoi_idxs)

        """
        figures = []

        for index in AOI_indexes:
            aoi_object = EOTDS.get_aoi_dataset(index)
            figures.append(plot_aoi_dataset(aoi_object))
        return figures

    @staticmethod
    def map_aois(EOTDS):
        """
        Plots the location of all AOIs (Area of Interests) on a map of the world. AOIs are
        plotted as points.

        :param EOTDS: The training dataset object
        :type EOTDS: aireo_lib.core.EOTrainingDataset
        :returns: The plot of AOIs on the map of the world
        :rtype: matplotlib.figure.Figure

        **Example usage**
        ::
            from aireo_lib.core import EOTrainingDataset
            from aireo_lib.plotting import EOTDSPlot as aireo_viz
            from pathlib import Path

            cap_tds_ctl_fn = Path('/home/jovyan/s3/CAP/cap_stac_generated/TDS.json')
            eo_tds_obj = EOTrainingDataset(cap_tds_ctl_fn, AOIDatasetCAP)


            fig = aireo_viz.map_aois(eo_tds_obj)

        """
        from pyproj import Proj, transform
        import geopandas
        import warnings
        warnings.filterwarnings("ignore")
        fig, ax = plt.subplots()
        world = geopandas.read_file(geopandas.datasets.get_path('naturalearth_lowres'))
        world.plot(ax=ax, color='white',edgecolor='black')
        # need to extactract coorinates of each AIOs and map
        x = []
        y = []
        outProj = Proj(init='epsg:4326')
        for aoi in EOTDS.aoi_ds_l:

            # need to get x and y coordinate and crs from xarray metadata
            sample = aoi[0]
            x1 = sample.coords['x'][0].values
            y1 = sample.coords['y'][0].values
            # get crs from reference metadata
            d = aoi.AOI_STAC_collection.aoi_all_field_metadata
            crs = d.references['output1'].metadata_d['properties']['CRS'].lower()
            inProj = Proj(init=crs)
            x2,y2 = transform(inProj,outProj,x1,y1)
            x.append(x2)
            y.append(y2)
        ax.scatter(x,y,s=10)  
        return fig           
