#!/usr/bin/python
# coding: utf-8

""" Write the work of NARPS' team 0ED6 using Nipype """

from os.path import join
from itertools import product

from nipype import Workflow, Node, MapNode
from nipype.interfaces.utility import IdentityInterface, Function
from nipype.interfaces.utility.base import Merge, Split, Select
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.interfaces.spm import (
    Coregister, Segment, RealignUnwarp, FieldMap, Normalize,
    Smooth, Level1Design, OneSampleTTestDesign, TwoSampleTTestDesign,
    EstimateModel, EstimateContrast, Threshold, ApplyVDM
    )
from nipype.interfaces.spm.base import Info as SPMInfo
from nipype.algorithms.modelgen import SpecifySPMModel
from nipype.algorithms.misc import Gunzip

from narps_open.pipelines import Pipeline
from narps_open.core.interfaces.confounds import ComputeDVARS
from narps_open.data.task import TaskInformation
from narps_open.data.participants import get_group
from narps_open.utils.configuration import Configuration
from narps_open.core.common import (
    list_intersection, elements_in_string, clean_list
    )
from narps_open.core.interfaces import InterfaceFactory

class PipelineTeam0ED6(Pipeline):
    """ A class that defines the pipeline of team 0ED6. """

    def __init__(self):
        super().__init__()
        self.fwhm = 5.0
        self.team_id = '0ED6'
        self.contrast_list = ['0001', '0002', '0003', '0004']
        condition_names = ['task', 'taskxgain^1', 'taskxloss^1', 'taskxreaction_time^1']
        self.subject_level_contrasts = [
            ['task', 'T', condition_names, [1, 0, 0, 0]],
            ['gain', 'T', condition_names, [0, 1, 0, 0]],
            ['loss', 'T', condition_names, [0, 0, 1, 0]],
            ['reaction_time', 'T', condition_names, [0, 0, 0, 1]]
            ]

    def get_preprocessing(self):
        """
        Create the preprocessing workflow.

        Returns:
            - preprocessing : nipype.WorkFlow
        """
        # Initialize preprocessing workflow to connect nodes along the way
        preprocessing = Workflow(
            base_dir = self.directories.working_dir,
            name = 'preprocessing')

        # IDENTITY INTERFACE - To iterate on subjects and runs
        information_source = Node(IdentityInterface(
            fields = ['subject_id', 'run_id']),
            name = 'information_source')
        information_source.iterables = [
            ('subject_id', self.subject_list),
            ('run_id', self.run_list)
            ]

        # SELECT FILES - Select input files
        templates = {
            'anat' : join('sub-{subject_id}', 'anat', 'sub-{subject_id}_T1w.nii.gz'),
            'magnitude' : join('sub-{subject_id}', 'fmap', 'sub-{subject_id}_magnitude1.nii.gz'),
            'phase' : join('sub-{subject_id}', 'fmap', 'sub-{subject_id}_phasediff.nii.gz'),
            'func' : join('sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-{run_id}_bold.nii.gz'),
            'sbref' : join('sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-{run_id}_sbref.nii.gz')
        }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.dataset_dir
        preprocessing.connect(information_source, 'subject_id', select_files, 'subject_id')
        preprocessing.connect(information_source, 'run_id', select_files, 'run_id')

        # GUNZIP - gunzip files because SPM do not use .nii.gz files
        gunzip_anat = Node(Gunzip(), name = 'gunzip_anat')
        gunzip_func = Node(Gunzip(), name = 'gunzip_func')
        gunzip_sbref = Node(Gunzip(), name = 'gunzip_sbref')
        gunzip_magnitude = Node(Gunzip(), name = 'gunzip_magnitude')
        gunzip_phase = Node(Gunzip(), name = 'gunzip_phase')
        preprocessing.connect(select_files, 'anat', gunzip_anat, 'in_file')
        preprocessing.connect(select_files, 'func', gunzip_func, 'in_file')
        preprocessing.connect(select_files, 'sbref', gunzip_sbref, 'in_file')
        preprocessing.connect(select_files, 'magnitude', gunzip_magnitude, 'in_file')
        preprocessing.connect(select_files, 'phase', gunzip_phase, 'in_file')

        # IMCALC - Compute difference between the two magnitude maps

        # FIELD MAP - Compute a voxel displacement map from magnitude and phase data
        fieldmap = Node(FieldMap(), name = 'fieldmap')
        fieldmap.inputs.blip_direction = -1
        fieldmap.inputs.echo_times = (4.92, 7.38)
        fieldmap.inputs.total_readout_time = 29.15
        fieldmap.inputs.template = join(SPMInfo.getinfo()['path'], 'toolbox', 'FieldMap', 'T1.nii')
        preprocessing.connect(gunzip_magnitude, 'out_file', fieldmap, 'magnitude_file')
        preprocessing.connect(gunzip_phase, 'out_file', fieldmap, 'phase_file')
        preprocessing.connect(gunzip_sbref, 'out_file', fieldmap, 'epi_file')
        preprocessing.connect(gunzip_anat, 'out_file', fieldmap, 'anat_file')

        # APPLYVDM - Apply fieldmap to single band reference EPI (sbref)
        apply_fieldmap = Node(ApplyVDM(), name = 'apply_fieldmap')
        apply_fieldmap.inputs.distortion_direction = 2
        apply_fieldmap.inputs.write_which = [2, 0]
        apply_fieldmap.inputs.interpolation = 7
        preprocessing.connect(gunzip_sbref, 'out_file', apply_fieldmap, 'in_files')
        preprocessing.connect(fieldmap, 'vdm', apply_fieldmap, 'vdmfile')

        # MERGE - Merge files for the realign & unwarp node into one input.
        merge_sbref_func = Node(Merge(2), name = 'merge_sbref_func')
        merge_sbref_func.inputs.ravel_inputs = True
        preprocessing.connect(gunzip_sbref, 'out_file', merge_sbref_func, 'in1')
        preprocessing.connect(gunzip_func, 'out_file', merge_sbref_func, 'in2')

        # REALIGN UNWARP
        realign_unwarp = MapNode(RealignUnwarp(), name = 'realign_unwarp', iterfield = 'in_files')
        realign_unwarp.inputs.quality = 0.95
        realign_unwarp.inputs.separation = 3
        realign_unwarp.inputs.fwhm = 5
        realign_unwarp.inputs.register_to_mean = True
        realign_unwarp.inputs.interp = 7
        realign_unwarp.inputs.wrap = [0, 0, 0]
        realign_unwarp.inputs.weight = ''
        realign_unwarp.inputs.est_basis_func = [12, 12]
        realign_unwarp.inputs.est_reg_order = 1
        realign_unwarp.inputs.est_reg_factor = 100000
        realign_unwarp.inputs.est_jacobian_deformations = False
        realign_unwarp.inputs.est_first_order_effects = [4, 5]
        realign_unwarp.inputs.est_second_order_effects = []
        realign_unwarp.inputs.est_unwarp_fwhm = 4
        realign_unwarp.inputs.est_re_est_mov_par = True
        realign_unwarp.inputs.est_num_of_iterations = [5]
        realign_unwarp.inputs.est_taylor_expansion_point = 'Average'
        realign_unwarp.inputs.reslice_which = [1, 1]
        realign_unwarp.inputs.reslice_interp = 7
        realign_unwarp.inputs.reslice_wrap = [0, 0, 0]
        realign_unwarp.inputs.reslice_mask = True
        realign_unwarp.inputs.out_prefix = 'u'
        preprocessing.connect(fieldmap, 'vdm', realign_unwarp, 'phase_map')
        preprocessing.connect(merge_sbref_func, 'out', realign_unwarp, 'in_files')

        # SPLIT - Split the mean outputs of realign_unwarp
        #   * realigned+unwarped sbref mean
        #   * realigned+unwarped func mean
        split_realign_unwarp_means = Node(Split(), name = 'split_realign_unwarp_means')
        split_realign_unwarp_means.inputs.splits = [1, 1] # out1 is sbref; out2 is func
        split_realign_unwarp_means.inputs.squeeze = True # Unfold one-element splits
        preprocessing.connect(realign_unwarp, 'mean_image', split_realign_unwarp_means, 'inlist')

        # SPLIT - Split the output of realign_unwarp
        #   * realigned+unwarped sbref
        #   * realigned+unwarped func
        split_realign_unwarp_outputs = Node(Split(), name = 'split_realign_unwarp_outputs')
        split_realign_unwarp_outputs.inputs.splits = [1, 1] # out1 is sbref; out2 is func
        split_realign_unwarp_outputs.inputs.squeeze = True # Unfold one-element splits
        preprocessing.connect(
            realign_unwarp, 'realigned_unwarped_files',
            split_realign_unwarp_outputs, 'inlist')

        # COREGISTER - Coregister sbref to realigned and unwarped mean image of func
        coregister_sbref_to_func = Node(Coregister(), name = 'coregister_sbref_to_func')
        coregister_sbref_to_func.inputs.cost_function = 'nmi'
        coregister_sbref_to_func.inputs.separation = [4, 2]
        coregister_sbref_to_func.inputs.ctolerance = [
            0.02, 0.02, 0.02, 0.001, 0.001, 0.001, 0.01, 0.01, 0.01, 0.001, 0.001, 0.001]
        coregister_sbref_to_func.inputs.fwhm = [7, 7]
        coregister_sbref_to_func.inputs.jobtype = 'estimate'
        preprocessing.connect(
            split_realign_unwarp_means, 'out2',  # mean func
            coregister_sbref_to_func, 'target')
        preprocessing.connect(
            split_realign_unwarp_outputs, 'out1', # sbref
            coregister_sbref_to_func, 'source')

        # MERGE - Merge func + func mean image files for the coregister_sbref_to_anat
        #   node into one input.
        merge_func_before_coregister = Node(Merge(2), name = 'merge_func_before_coregister')
        merge_func_before_coregister.inputs.ravel_inputs = True
        preprocessing.connect( # out2 is func
            split_realign_unwarp_outputs, 'out2', merge_func_before_coregister, 'in1')
        preprocessing.connect( # out2 is func mean
            split_realign_unwarp_means, 'out2', merge_func_before_coregister, 'in2')

        # COREGISTER - Coregister sbref to anat
        coregister_sbref_to_anat = Node(Coregister(), name = 'coregister_sbref_to_anat')
        coregister_sbref_to_anat.inputs.cost_function = 'nmi'
        coregister_sbref_to_anat.inputs.separation = [4, 2]
        coregister_sbref_to_anat.inputs.ctolerance = [
            0.02, 0.02, 0.02, 0.001, 0.001, 0.001, 0.01, 0.01, 0.01, 0.001, 0.001, 0.001]
        coregister_sbref_to_anat.inputs.fwhm = [7, 7]
        coregister_sbref_to_anat.inputs.jobtype = 'estimate'
        coregister_sbref_to_anat.inputs.target = join(
            SPMInfo.getinfo()['path'], 'toolbox', 'OldSeg', 'grey.nii')
        preprocessing.connect(
            coregister_sbref_to_func, 'coregistered_source', coregister_sbref_to_anat, 'source')
        preprocessing.connect(# out[0] is func, out[1] is func mean
            merge_func_before_coregister, 'out', coregister_sbref_to_anat, 'apply_to_files')

        # SEGMENT - First step of sbref normalization.
        segmentation_sbref = Node(Segment(), name = 'segmentation_sbref')
        segmentation_sbref.inputs.csf_output_type = [False, False, False] # No output for CSF
        segmentation_sbref.inputs.gm_output_type = [False, False, False] # No output for GM
        segmentation_sbref.inputs.wm_output_type = [False, False, False] # No output for WM
        segmentation_sbref.inputs.save_bias_corrected = False
        segmentation_sbref.inputs.warp_frequency_cutoff = 45
        segmentation_sbref.inputs.sampling_distance = 2.0
        preprocessing.connect(
            coregister_sbref_to_anat, 'coregistered_source', segmentation_sbref, 'data')

        # NORMALIZE - Deformation computed by the segmentation_sbref step is applied to
        #   the func, mean func, and sbref.
        normalize = Node(Normalize(), name = 'normalize')
        normalize.inputs.write_voxel_sizes = [2, 2, 2]
        normalize.inputs.jobtype = 'write' # Estimation was done on previous step
        preprocessing.connect(
            segmentation_sbref, 'transformation_mat', normalize, 'parameter_file')
        preprocessing.connect(# coregistered_files[0] is func, coregistered_files[1] is func mean
            coregister_sbref_to_anat, 'coregistered_files', normalize, 'apply_to_files')

        # SMOOTH - Spatial smoothing of fMRI data
        smoothing = Node(Smooth(), name = 'smoothing')
        smoothing.inputs.fwhm = [self.fwhm] * 3
        smoothing.inputs.data_type = 0
        smoothing.inputs.implicit_masking = False
        smoothing.inputs.prefix = 's'
        preprocessing.connect(normalize, 'normalized_files', smoothing, 'in_files')

        # SELECT - Select the smoothed func.
        select_func = Node(Select(), name = 'select_func')
        select_func.inputs.index = [0] # func file
        preprocessing.connect(smoothing, 'smoothed_files', select_func, 'inlist')

        # COMPUTE DVARS - Identify corrupted time-points from func
        compute_dvars = Node(ComputeDVARS(), name = 'compute_dvars')
        compute_dvars.inputs.out_file_name = 'dvars_out'
        preprocessing.connect(select_func, 'out', compute_dvars, 'in_file')

        # DATA SINK - store the wanted results in the wanted repository
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        preprocessing.connect(smoothing, 'smoothed_files', data_sink, 'preprocessing.@smoothed')
        preprocessing.connect(
            realign_unwarp, 'realignment_parameters',
            data_sink, 'preprocessing.@realignement_parameters')
        preprocessing.connect(
            compute_dvars, 'dvars_out_file', data_sink, 'preprocessing.@dvars_out_file')
        preprocessing.connect(
            compute_dvars, 'inference_out_file', data_sink, 'preprocessing.@inference_out_file')

        # Remove large files, if requested
        if Configuration()['pipelines']['remove_unused_data']:

            # MERGE - Merge all temporary outputs once they are no longer needed
            merge_temp_files = Node(Merge(8), name = 'merge_temp_files')
            preprocessing.connect(gunzip_anat, 'out_file', merge_temp_files, 'in1')
            preprocessing.connect(gunzip_func, 'out_file', merge_temp_files, 'in2')
            preprocessing.connect(gunzip_sbref, 'out_file', merge_temp_files, 'in3')
            preprocessing.connect(gunzip_magnitude, 'out_file', merge_temp_files, 'in4')
            preprocessing.connect(gunzip_phase, 'out_file', merge_temp_files, 'in5')
            preprocessing.connect(
                realign_unwarp, 'realigned_unwarped_files',
                merge_temp_files, 'in6')
            preprocessing.connect(normalize, 'normalized_files', merge_temp_files, 'in7')
            preprocessing.connect(
                coregister_sbref_to_anat, 'coregistered_files', merge_temp_files, 'in8')

            # FUNCTION - Remove gunziped files once they are no longer needed
            remove_gunziped = MapNode(
                InterfaceFactory.create('remove_parent_directory'),
                name = 'remove_gunziped',
                iterfield = 'file_name'
                )
            preprocessing.connect(merge_temp_files, 'out', remove_gunziped, 'file_name')
            preprocessing.connect(data_sink, 'out_file', remove_gunziped, '_')

        return preprocessing

    def get_preprocessing_outputs(self):
        """ Return the names of the files the preprocessing is supposed to generate. """

        output_dir = join(self.directories.output_dir, 'preprocessing',
            '_run_id_{run_id}_subject_id_{subject_id}')

        # Smoothing outputs
        templates = [
            join(output_dir, 'swusub-{subject_id}_task-MGT_run-{run_id}_bold.nii'),
            join(output_dir, 'swmeanusub-{subject_id}_task-MGT_run-{run_id}_bold.nii')
            ]

        # DVARS output
        templates += [
            join(output_dir, 'dvars_out_DVARS.tsv'),
            join(output_dir, 'dvars_out_Inference.tsv')
            ]

        # Realignement parameters
        templates += [
            join(output_dir, '_realign_unwarp0',
                'rp_sub-{subject_id}_task-MGT_run-{run_id}_sbref.txt'),
            join(output_dir, '_realign_unwarp1',
                'rp_sub-{subject_id}_task-MGT_run-{run_id}_bold.txt')
            ]

        # Format with subject_ids and run_ids
        return [t.format(subject_id = s, run_id = r)
            for t in templates for s in self.subject_list for r in self.run_list]

    def get_run_level_analysis(self):
        """ No run level analysis has been done by team 0ED6 """
        return None

    def get_subject_information(event_file):
        """
        Create Bunchs for specifySPMModel, from data extracted from an event_file.

        Parameters :
        - event_files: str, event file (one per run) for the subject

        Returns :
        - subject_information: Bunch, relevant event information for subject level analysis.
        """
        from nipype.interfaces.base import Bunch

        # Init empty lists inside directiries
        onsets = []
        durations = []
        gain_value = []
        loss_value = []
        reaction_time = []

        with open(event_file, 'rt') as file:
            next(file)  # skip the header

            for line in file:
                info = line.strip().split()

                onsets.append(float(info[0]))
                durations.append(float(info[1]))
                gain_value.append(float(info[2]))
                loss_value.append(float(info[3]))
                reaction_time.append(float(info[4]))

        # TODO : SPM automatically mean-centers regressors ???
        # TODO : SPM automatically orthoganalizes regressors ???

        # Fill Bunch
        return Bunch(
                conditions = ['task'],
                onsets = [onsets],
                durations = [durations],
                amplitudes = None,
                tmod = None,
                pmod = [
                    Bunch(
                        name = ['gain', 'loss', 'reaction_time'],
                        poly = [1, 1, 1],
                        param = [gain_value, loss_value, reaction_time]
                    )
                ],
                regressor_names = None,
                regressors = None
            )

    def get_confounds_file(
        dvars_file: str,
        dvars_inference_file: str,
        realignement_parameters: str,
        subject_id: str,
        run_id: str) -> str:
        """
        Create a tsv file with only desired confounds per subject per run.

        Parameters :
        - dvars_file: str, path to the output values of DVARS computation
        - dvars_inference_file: str, path to the output values of DVARS computation (inference)
        - realignement_parameters : path to the realignment parameters file
        - subject_id : related subject id
        - run_id : related run id

        Return :
        - confounds_file : path to new file containing only desired confounds
        """
        from os.path import abspath

        from pandas import DataFrame, read_csv
        from numpy import array, insert, c_

        # Get the dataframe containing the 6 head motion parameter regressors
        realign_array = array(read_csv(realignement_parameters, sep = r'\s+', header = None))
        nb_time_points = realign_array.shape[0]

        # Get the dataframes containing dvars values
        dvars_data_frame = read_csv(dvars_file, sep = '\t', header = 0)
        dvars_inference_data_frame = read_csv(dvars_inference_file, sep = '\t', header = 0)

        # Create a "corrupted points" regressor as indicated in the DVARS repo
        #   find(Stat.pvals<0.05./(T-1) & Stat.DeltapDvar>5) %print corrupted DVARS data-points
        dvars_regressor = insert(array(
            (dvars_inference_data_frame['Pval'] < (0.05/(nb_time_points-1))) \
            & (dvars_data_frame['DeltapDvar'] > 5.0)),
            0, 0, axis = 0) # Add a value of 0 at the beginning (first frame)

        # Concatenate all parameters
        retained_parameters = DataFrame(c_[realign_array, dvars_regressor])

        # Write confounds to a file
        confounds_file = abspath(f'confounds_file_sub-{subject_id}_run-{run_id}.tsv')
        with open(confounds_file, 'w', encoding = 'utf-8') as writer:
            writer.write(retained_parameters.to_csv(
                sep = '\t', index = False, header = False, na_rep = '0.0'))

        return confounds_file

    def get_subject_level_analysis(self):
        """
        Create the subject level analysis workflow.

        Returns:
            - subject_level : nipype.WorkFlow
                WARNING: the name attribute of the workflow is 'subject_level_analysis'
        """
        # Create subject level analysis workflow
        subject_level = Workflow(
            base_dir = self.directories.working_dir,
            name = 'subject_level_analysis')

        # IDENTITY INTERFACE - To iterate on subjects
        information_source = Node(IdentityInterface(
            fields = ['subject_id']),
            name = 'information_source')
        information_source.iterables = [('subject_id', self.subject_list)]

        # SELECT FILES - to select necessary files
        templates = {
            'dvars_file' : join(self.directories.output_dir, 'preprocessing',
                '_run_id_*_subject_id_{subject_id}',
                'dvars_out_DVARS.tsv'),
            'dvars_inference_file' : join(self.directories.output_dir, 'preprocessing',
                '_run_id_*_subject_id_{subject_id}',
                'dvars_out_Inference.tsv'),
            'realignement_parameters' : join(self.directories.output_dir, 'preprocessing',
                '_run_id_*_subject_id_{subject_id}', '_realign_unwarp1',
                'rp_sub-{subject_id}_task-MGT_run-*_bold.txt'),
            'func' : join(self.directories.output_dir, 'preprocessing',
                '_run_id_*_subject_id_{subject_id}', 'swusub-{subject_id}_task-MGT_run-*_bold.nii'),
            'event' : join('sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-*_events.tsv')
        }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.dataset_dir
        subject_level.connect(information_source, 'subject_id', select_files, 'subject_id')

        # FUNCTION get_subject_information - generate files with event data
        subject_information = MapNode(Function(
            function = self.get_subject_information,
            input_names = ['event_file'],
            output_names = ['subject_info']),
            iterfield = 'event_file',
            name = 'subject_information')
        subject_level.connect(select_files, 'event', subject_information, 'event_file')

        # FUNCTION node get_confounds_file - generate files with confounds data
        confounds = MapNode(
            Function(
                function = self.get_confounds_file,
                input_names = ['dvars_file', 'dvars_inference_file', 'realignement_parameters',
                    'subject_id', 'run_id'],
                output_names = ['confounds_file']
            ),
            name = 'confounds',
            iterfield = ['dvars_file', 'dvars_inference_file', 'realignement_parameters',
                'run_id'])
        confounds.inputs.run_id = self.run_list
        subject_level.connect(information_source, 'subject_id', confounds, 'subject_id')
        subject_level.connect(select_files, 'dvars_file', confounds, 'dvars_file')
        subject_level.connect(
            select_files, 'dvars_inference_file', confounds, 'dvars_inference_file')
        subject_level.connect(
            select_files, 'realignement_parameters', confounds, 'realignement_parameters')

        # SPECIFY MODEL - generates SPM-specific Model
        specify_model = Node(SpecifySPMModel(), name = 'specify_model')
        specify_model.inputs.input_units = 'secs'
        specify_model.inputs.output_units = 'secs'
        specify_model.inputs.time_repetition = TaskInformation()['RepetitionTime']
        specify_model.inputs.high_pass_filter_cutoff = 128
        subject_level.connect(select_files, 'func', specify_model, 'functional_runs')
        subject_level.connect(confounds, 'confounds_file', specify_model, 'realignment_parameters')
        subject_level.connect(subject_information, 'subject_info', specify_model, 'subject_info')

        # LEVEL 1 DESIGN - Generates an SPM design matrix
        model_design = Node(Level1Design(), name = 'model_design')
        model_design.inputs.bases = {'hrf': {'derivs': [1,0]}} # Temporal derivative
        model_design.inputs.timing_units = 'secs'
        model_design.inputs.interscan_interval = TaskInformation()['RepetitionTime']
        subject_level.connect(specify_model, 'session_info', model_design, 'session_info')

        # ESTIMATE MODEL - estimate the parameters of the model
        model_estimate = Node(EstimateModel(), name = 'model_estimate')
        model_estimate.inputs.estimation_method = {'Classical': 1}
        subject_level.connect(model_design, 'spm_mat_file', model_estimate, 'spm_mat_file')

        # ESTIMATE CONTRAST - estimates contrasts
        contrast_estimate = Node(EstimateContrast(), name = 'contrast_estimate')
        contrast_estimate.inputs.contrasts = self.subject_level_contrasts
        subject_level.connect([
            (model_estimate, contrast_estimate, [
                ('spm_mat_file', 'spm_mat_file'),
                ('beta_images', 'beta_images'),
                ('residual_image', 'residual_image')
            ])
        ])

        # DATA SINK - store the wanted results in the wanted repository
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        subject_level.connect([
            (contrast_estimate, data_sink, [
                ('con_images', 'subject_level_analysis.@con_images'),
                ('spmT_images', 'subject_level_analysis.@spmT_images'),
                ('spm_mat_file', 'subject_level_analysis.@spm_mat_file')
            ])
        ])

        return subject_level

    def get_subject_level_outputs(self):
        """ Return the names of the files the subject level analysis is supposed to generate. """

        # Contrat maps
        templates = [join(
            self.directories.output_dir,
            'subject_level_analysis', '_subject_id_{subject_id}', f'con_{contrast_id}.nii')\
            for contrast_id in self.contrast_list]

        # SPM.mat file
        templates += [join(
            self.directories.output_dir,
            'subject_level_analysis', '_subject_id_{subject_id}', 'SPM.mat')]

        # spmT maps
        templates += [join(
            self.directories.output_dir,
            'subject_level_analysis', '_subject_id_{subject_id}', f'spmT_{contrast_id}.nii')\
            for contrast_id in self.contrast_list]

        # Format with subject_ids
        return_list = []
        for template in templates:
            return_list += [template.format(subject_id = s) for s in self.subject_list]

        return return_list

    def get_group_level_analysis(self):
        """
        Return all workflows for the group level analysis.

        Returns;
            - a list of nipype.WorkFlow
        """

        methods = ['equalRange', 'equalIndifference', 'groupComp']
        return [self.get_group_level_analysis_sub_workflow(method) for method in methods]

    def get_group_level_analysis_sub_workflow(self, method):
        """
        Return a workflow for the group level analysis.

        Parameters:
            - method: one of 'equalRange', 'equalIndifference' or 'groupComp'

        Returns:
            - group_level_analysis: nipype.WorkFlow
        """
        # Compute the number of participants used to do the analysis
        nb_subjects = len(self.subject_list)

        # Infosource - a function free node to iterate over the list of subject names
        information_source = Node(
            IdentityInterface(
                fields=['contrast_id']),
                name='information_source')
        information_source.iterables = [('contrast_id', self.contrast_list)]

        # SelectFiles
        templates = {
            # Contrasts for all participants
            'contrasts' : join(self.directories.output_dir,
                'subject_level_analysis', '_subject_id_*', 'con_{contrast_id}.nii')
        }

        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.results_dir
        select_files.inputs.force_lists = True

        # Datasink - save important files
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir

        # Function Node get_equal_range_subjects
        #   Get subjects in the equalRange group and in the subject_list
        get_equal_range_subjects = Node(Function(
            function = list_intersection,
            input_names = ['list_1', 'list_2'],
            output_names = ['out_list']
            ),
            name = 'get_equal_range_subjects'
        )
        get_equal_range_subjects.inputs.list_1 = get_group('equalRange')
        get_equal_range_subjects.inputs.list_2 = self.subject_list

        # Function Node get_equal_indifference_subjects
        #   Get subjects in the equalIndifference group and in the subject_list
        get_equal_indifference_subjects = Node(Function(
            function = list_intersection,
            input_names = ['list_1', 'list_2'],
            output_names = ['out_list']
            ),
            name = 'get_equal_indifference_subjects'
        )
        get_equal_indifference_subjects.inputs.list_1 = get_group('equalIndifference')
        get_equal_indifference_subjects.inputs.list_2 = self.subject_list

        # Create a function to complete the subject ids out from the get_equal_*_subjects nodes
        #   If not complete, subject id '001' in search patterns
        #   would match all contrast files with 'con_0001.nii'.
        complete_subject_ids = lambda l : [f'_subject_id_{a}' for a in l]

        # Function Node elements_in_string
        #   Get contrast files for required subjects
        # Note : using a MapNode with elements_in_string requires using clean_list to remove
        #   None values from the out_list
        get_contrasts = MapNode(Function(
            function = elements_in_string,
            input_names = ['input_str', 'elements'],
            output_names = ['out_list']
            ),
            name = 'get_contrasts', iterfield = 'input_str'
        )

        # Estimate model
        estimate_model = Node(EstimateModel(), name = 'estimate_model')
        estimate_model.inputs.estimation_method = {'Classical':1}

        # Estimate contrasts
        estimate_contrast = Node(EstimateContrast(), name = 'estimate_contrast')
        estimate_contrast.inputs.group_contrast = True

        ## Create thresholded maps
        threshold = MapNode(Threshold(),
            name = 'threshold',
            iterfield = ['stat_image', 'contrast_index'])
        threshold.inputs.use_fwe_correction = False
        threshold.inputs.height_threshold = 0.001
        threshold.inputs.extent_fdr_p_threshold = 0.05
        threshold.inputs.use_topo_fdr = False
        threshold.inputs.force_activation = True
        threshold.synchronize = True

        group_level_analysis = Workflow(
            base_dir = self.directories.working_dir,
            name = f'group_level_analysis_{method}_nsub_{nb_subjects}')
        group_level_analysis.connect([
            (information_source, select_files, [('contrast_id', 'contrast_id')]),
            (select_files, get_contrasts, [('contrasts', 'input_str')]),
            (estimate_model, estimate_contrast, [
                ('spm_mat_file', 'spm_mat_file'),
                ('residual_image', 'residual_image'),
                ('beta_images', 'beta_images')]),
            (estimate_contrast, threshold, [
                ('spm_mat_file', 'spm_mat_file'),
                ('spmT_images', 'stat_image')]),
            (estimate_model, data_sink, [
                ('mask_image', f'group_level_analysis_{method}_nsub_{nb_subjects}.@mask')]),
            (estimate_contrast, data_sink, [
                ('spm_mat_file', f'group_level_analysis_{method}_nsub_{nb_subjects}.@spm_mat'),
                ('spmT_images', f'group_level_analysis_{method}_nsub_{nb_subjects}.@T'),
                ('con_images', f'group_level_analysis_{method}_nsub_{nb_subjects}.@con')]),
            (threshold, data_sink, [
                ('thresholded_map', f'group_level_analysis_{method}_nsub_{nb_subjects}.@thresh')])])

        if method in ('equalRange', 'equalIndifference'):
            estimate_contrast.inputs.contrasts = [
                ('Group', 'T', ['mean'], [1]),
                ('Group', 'T', ['mean'], [-1])
                ]

            threshold.inputs.contrast_index = [1, 2]

            # Specify design matrix
            one_sample_t_test_design = Node(OneSampleTTestDesign(),
                name = 'one_sample_t_test_design')
            group_level_analysis.connect([
                (get_contrasts, one_sample_t_test_design, [
                    (('out_list', clean_list), 'in_files')
                    ]),
                (one_sample_t_test_design, estimate_model, [('spm_mat_file', 'spm_mat_file')])
                ])

        if method == 'equalRange':
            group_level_analysis.connect([
                (get_equal_range_subjects, get_contrasts, [
                    (('out_list', complete_subject_ids), 'elements')
                ])
            ])

        elif method == 'equalIndifference':
            group_level_analysis.connect([
                (get_equal_indifference_subjects, get_contrasts, [
                    (('out_list', complete_subject_ids), 'elements')
                ])
            ])

        elif method == 'groupComp':
            estimate_contrast.inputs.contrasts = [
                ('Eq range vs Eq indiff in loss', 'T', ['Group_{1}', 'Group_{2}'], [1, -1])
                ]

            threshold.inputs.contrast_index = [1]

            # Function Node elements_in_string
            #   Get contrast files for required subjects
            # Note : using a MapNode with elements_in_string requires using clean_list to remove
            #   None values from the out_list
            get_contrasts_2 = MapNode(Function(
                function = elements_in_string,
                input_names = ['input_str', 'elements'],
                output_names = ['out_list']
                ),
                name = 'get_contrasts_2', iterfield = 'input_str'
            )

            # Specify design matrix
            two_sample_t_test_design = Node(TwoSampleTTestDesign(),
                name = 'two_sample_t_test_design')
            two_sample_t_test_design.inputs.unequal_variance = True

            group_level_analysis.connect([
                (select_files, get_contrasts_2, [('contrasts', 'input_str')]),
                (get_equal_range_subjects, get_contrasts, [
                    (('out_list', complete_subject_ids), 'elements')
                ]),
                (get_equal_indifference_subjects, get_contrasts_2, [
                    (('out_list', complete_subject_ids), 'elements')
                ]),
                (get_contrasts, two_sample_t_test_design, [
                    (('out_list', clean_list), 'group1_files')
                ]),
                (get_contrasts_2, two_sample_t_test_design, [
                    (('out_list', clean_list), 'group2_files')
                ]),
                (two_sample_t_test_design, estimate_model, [('spm_mat_file', 'spm_mat_file')])
            ])

        return group_level_analysis

    def get_group_level_outputs(self):
        """ Return all names for the files the group level analysis is supposed to generate. """

        # Handle equalRange and equalIndifference
        parameters = {
            'contrast_id': self.contrast_list,
            'method': ['equalRange', 'equalIndifference'],
            'file': [
                'con_0001.nii', 'con_0002.nii', 'mask.nii', 'SPM.mat',
                'spmT_0001.nii', 'spmT_0002.nii',
                join('_threshold0', 'spmT_0001_thr.nii'), join('_threshold1', 'spmT_0002_thr.nii')
                ],
            'nb_subjects' : [str(len(self.subject_list))]
        }
        parameter_sets = product(*parameters.values())
        template = join(
            self.directories.output_dir,
            'group_level_analysis_{method}_nsub_{nb_subjects}',
            '_contrast_id_{contrast_id}',
            '{file}'
            )

        return_list = [template.format(**dict(zip(parameters.keys(), parameter_values)))\
            for parameter_values in parameter_sets]

        # Handle groupComp
        parameters = {
            'contrast_id': self.contrast_list,
            'method': ['groupComp'],
            'file': [
                'con_0001.nii', 'mask.nii', 'SPM.mat', 'spmT_0001.nii',
                join('_threshold0', 'spmT_0001_thr.nii')
                ],
            'nb_subjects' : [str(len(self.subject_list))]
        }
        parameter_sets = product(*parameters.values())
        template = join(
            self.directories.output_dir,
            'group_level_analysis_{method}_nsub_{nb_subjects}',
            '_contrast_id_{contrast_id}',
            '{file}'
            )

        return_list += [template.format(**dict(zip(parameters.keys(), parameter_values)))\
            for parameter_values in parameter_sets]

        return return_list

    def get_hypotheses_outputs(self):
        """ Return all hypotheses output file names.
            Note that hypotheses 5 to 8 correspond to the maps given by the team in their results ;
            but they are not fully consistent with the hypotheses definitions as expected by NARPS.
        """
        nb_sub = len(self.subject_list)
        files = [
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0001.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0001.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0001.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0001.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0003', '_threshold1', 'spmT_0002_thr.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0003', 'spmT_0002.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0003', '_threshold1', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0003', 'spmT_0001.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0003', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0003', 'spmT_0001.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0003', '_threshold0', 'spmT_0002_thr.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0003', 'spmT_0002.nii'),
            join(f'group_level_analysis_groupComp_nsub_{nb_sub}',
                '_contrast_id_0003', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_groupComp_nsub_{nb_sub}',
                '_contrast_id_0003', 'spmT_0001.nii')
        ]
        return [join(self.directories.output_dir, f) for f in files]
