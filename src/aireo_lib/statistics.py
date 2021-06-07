class EOTDSStatistics:
    """
    To provide different statistics of a training dataset.
    """

    @staticmethod
    def metadata_statistics(EOTDS):
        """
        Provide metadata completeness statistics for a training dataset. Returns the fraction
        of metadata elements present in each of core, recommended and optional elements.

        :param EOTDS: The training dataset object
        :type EOTDS: aireo_lib.core.EOTrainingDataset
        :returns: A dictionary of metadata statistics
        :rtype: dict

        **Example usage**
        ::
            from aireo_lib.core import EOTrainingDataset
            from aireo_lib.statistics import EOTDSStatistics as stats
            from pathlib import Path

            cap_tds_ctl_fn = Path('/home/jovyan/s3/CAP/cap_stac_generated/TDS.json')
            eo_tds_obj = EOTrainingDataset(cap_tds_ctl_fn, AOIDatasetCAP)

            print(stats.metadata_statistics(eo_tds_obj))

        """
        return EOTDS.tds_ctl_o.report_metadata_completeness()



    @staticmethod
    def feature_data_statistics(EOTDS):
        """
        Provides statistics for predictive feature variable of a training dataset.
        For georeferenced_eo_image and georeferenced_eo_datacube profiles, it returns a dictionary with
        min, max, std and mean for each Area of Interest (AOI) in the input and also each channel.

        :param EOTDS: The training dataset object
        :type EOTDS: aireo_lib.core.EOTrainingDataset
        :returns: A dictionary of different predictive feature variable statistics
        :rtype: dict

        **Example usage**
        ::
            from aireo_lib.core import EOTrainingDataset
            from aireo_lib.statistics import EOTDSStatistics as stats
            from pathlib import Path

            cap_tds_ctl_fn = Path('/home/jovyan/s3/CAP/cap_stac_generated/TDS.json')
            eo_tds_obj = EOTrainingDataset(cap_tds_ctl_fn, AOIDatasetCAP)

            print(stats.feature_data_statistics(eo_tds_obj))
        """
        all_stats = {}
        features_d = EOTDS.tds_ctl_o.tds_ctl_root_info.g_all_field_metadata.features
        for feature in features_d:
            var_name = 'features_' + feature
            if "georeferenced_eo_image" in features_d[feature].metadata_d['stac_extensions'] or \
                    "georeferenced_eo_datacube" in features_d[feature].metadata_d['stac_extensions']:
                for i, aoi in enumerate(EOTDS.get_aoi_datasets()):
                    for j in range(0, aoi.data[var_name].shape[0]):
                        stats = {}
#                         stats['AOI'] = i
#                         stats['Channel'] = j
                        stats['mean'] = aoi.data[var_name][j, :, :].mean().values.tolist()
                        stats['std'] = aoi.data[var_name][j, :, :].std().values.tolist()
                        stats['max'] = max(aoi.data[var_name][j, :, :].values.flatten())
                        stats['min'] = min(aoi.data[var_name][j, :, :].values.flatten())
                        all_stats[f'aoi_{i}_channel_{j}'] = stats
        return all_stats


    @staticmethod
    def reference_data_statistics(EOTDS):
        """
        Provides statistics for reference data variable of a training dataset. Dictionary with counts
        of all the reference data variables are returned for each AOI separately and also for the whole dataset.

        :param EOTDS: The training dataset object
        :type EOTDS: aireo_lib.core.EOTrainingDataset
        :returns: A dictionary of reference data variable statistics
        :rtype: dict

        **Example usage**
        ::
            from aireo_lib.core import EOTrainingDataset
            from aireo_lib.statistics import EOTDSStatistics as stats
            from pathlib import Path

            cap_tds_ctl_fn = Path('/home/jovyan/s3/CAP/cap_stac_generated/TDS.json')
            eo_tds_obj = EOTrainingDataset(cap_tds_ctl_fn, AOIDatasetCAP)

            print(stats.reference_data_statistics(eo_tds_obj))
        """
        from collections import Counter
        all_stats = {}
        stats = {}

        def update_stats(aoi_stats):
            for key in aoi_stats.keys():
                if key in stats.keys():
                    stats[key] += aoi_stats[key]
                else:
                    stats[key] = aoi_stats[key]

        for ref in EOTDS.tds_ctl_o.tds_ctl_root_info.g_all_field_metadata.references:
            var_name = 'references_'+ref
            for i, aoi in enumerate(EOTDS.get_aoi_datasets()):
                aoi_stats = Counter(aoi.data[var_name].values.flatten())
                # get the id of the aoi
                all_stats[var_name+'_aoi'+str(i)] = aoi_stats
                update_stats(aoi_stats)
        all_stats['whole_TDS_stats'] = stats
        return all_stats


    @staticmethod
    def dataset_statistics(EOTDS):
        """
        Provide statistics for reference and predictive feature variables for a training dataset.
        A wrapper around reference_data_statistics and feature_data_statistics. Additionally, returns the
        number of examples in a training dataset.

        :param EOTDS: The training dataset object
        :type EOTDS: aireo_lib.core.EOTrainingDataset
        :returns: A dictionary of different training dataset statistics
        :rtype: dict

        **Example usage**
        ::
            from aireo_lib.core import EOTrainingDataset
            from aireo_lib.statistics import EOTDSStatistics as stats
            from pathlib import Path

            cap_tds_ctl_fn = Path('/home/jovyan/s3/CAP/cap_stac_generated/TDS.json')
            eo_tds_obj = EOTrainingDataset(cap_tds_ctl_fn, AOIDatasetCAP)

            print(stats.dataset_statistics(eo_tds_obj))
        """
        all_stats = {}
        all_stats['num_examples'] = len(EOTDS)
        all_stats['references_stats'] = EOTDSStatistics.reference_data_statistics(EOTDS)
        all_stats['features_stats'] = EOTDSStatistics.feature_data_statistics(EOTDS)
        return all_stats
