#!/usr/bin/python
# coding: utf-8

""" Write the work of NARPS team 3C6G using Nipype """

from os.path import join
from itertools import product

from nipype import Node, Workflow, MapNode
from nipype.interfaces.utility import IdentityInterface, Function, Merge
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.algorithms.misc import Gunzip
from nipype.algorithms.modelgen import SpecifySPMModel
from nipype.interfaces.spm import (
   Realign, Coregister, NewSegment, Normalize12, Smooth,
   Level1Design, OneSampleTTestDesign, TwoSampleTTestDesign,
   EstimateModel, EstimateContrast, Threshold
   )
from nipype.interfaces.spm.base import Info as SPMInfo
from nipype.interfaces.fsl import (
    ExtractROI
    )

from narps_open.pipelines import Pipeline
from narps_open.data.task import TaskInformation
from narps_open.data.participants import get_group
from narps_open.core.common import (
    remove_parent_directory, list_intersection, elements_in_string, clean_list
    )
from narps_open.utils.configuration import Configuration

class PipelineTeam3C6G(Pipeline):
    """ A class that defines the pipeline of team 3C6G """

    def __init__(self):
        super().__init__()
        self.fwhm = 6.0
        self.team_id = '3C6G'
        self.contrast_list = ['0001', '0002', '0003', '0004', '0005']

        # Create contrasts
        conditions = ['trial', 'trialxgain^1', 'trialxloss^1']
        self.subject_level_contrasts = [
            ['trial', 'T', conditions, [1, 0, 0]],
            ['effect_of_gain', 'T', conditions, [0, 1, 0]],
            ['neg_effect_of_gain', 'T', conditions, [0, -1, 0]],
            ['effect_of_loss', 'T', conditions, [0, 0, 1]],
            ['neg_effect_of_loss', 'T', conditions, [0, 0, -1]]
            ]

    def get_preprocessing(self):
        """ Return a Nipype workflow describing the prerpocessing part of the pipeline """

        # Workflow initialization
        preprocessing = Workflow(
            base_dir = self.directories.working_dir,
            name = 'preprocessing'
        )
        # IDENTITY INTERFACE - allows to iterate over subjects
        information_source_subject = Node(IdentityInterface(
            fields = ['subject_id']),
            name = 'information_source_subject'
        )
        information_source_subject.iterables = ('subject_id', self.subject_list)

        # IDENTITY INTERFACE - allows to iterate over runs
        information_source_runs = Node(IdentityInterface(
            fields = ['subject_id', 'run_id']),
            name = 'information_source_runs'
        )
        information_source_runs.iterables = ('run_id', self.run_list)
        preprocessing.connect(
            information_source_subject, 'subject_id', information_source_runs, 'subject_id')

        # SELECT FILES - to select subject files
        file_templates = {'anat': join('sub-{subject_id}', 'anat', 'sub-{subject_id}_T1w.nii.gz')}
        select_subject_files = Node(SelectFiles(file_templates), name = 'select_subject_files')
        select_subject_files.inputs.base_directory = self.directories.dataset_dir
        preprocessing.connect(
            information_source_subject, 'subject_id', select_subject_files, 'subject_id')

        # SELECT FILES - to select run files
        file_templates = {
            'func': join('sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-{run_id}_bold.nii.gz')
        }
        select_run_files = Node(SelectFiles(file_templates), name = 'select_run_files')
        select_run_files.inputs.base_directory = self.directories.dataset_dir
        preprocessing.connect(
            information_source_runs, 'subject_id', select_run_files, 'subject_id')
        preprocessing.connect(information_source_runs, 'run_id', select_run_files, 'run_id')

        # GUNZIP input files
        gunzip_func = Node(Gunzip(), name = 'gunzip_func')
        gunzip_anat = Node(Gunzip(), name = 'gunzip_anat')
        preprocessing.connect(select_run_files, 'func', gunzip_func, 'in_file')
        preprocessing.connect(select_subject_files, 'anat', gunzip_anat, 'in_file')

        # REALIGN - rigid-body realignment in SPM12 using 1st scan as referenced scan
        # and normalized mutual information.
        realign = Node(Realign(), name = 'realign')
        realign.inputs.register_to_mean = False
        preprocessing.connect(gunzip_func, 'out_file', realign, 'in_files')

        # EXTRACTROI - extracting the first image of func
        extract_first_image = Node(ExtractROI(), name = 'extract_first_image')
        extract_first_image.inputs.t_min = 1
        extract_first_image.inputs.t_size = 1
        extract_first_image.inputs.output_type='NIFTI'
        preprocessing.connect(realign, 'realigned_files', extract_first_image, 'in_file')

        # COREGISTER - Co-registration in SPM12 using default parameters.
        coregister = Node(Coregister(), name = 'coregister')
        coregister.inputs.cost_function='nmi'
        preprocessing.connect(extract_first_image, 'roi_file', coregister, 'source')
        preprocessing.connect(gunzip_anat, 'out_file', coregister, 'target')
        preprocessing.connect(realign, 'realigned_files', coregister, 'apply_to_files')

        # Get SPM Tissue Probability Maps file
        spm_tissues_file = join(SPMInfo.getinfo()['path'], 'tpm', 'TPM.nii')

        # NEW SEGMENT - Unified segmentation using tissue probability maps in SPM12.
        # Unified segmentation in SPM12 to MNI space
        # (the MNI-space tissue probability maps used in segmentation) using default parameters.
        # Bias-field correction in the context of unified segmentation in SPM12.
        segmentation = Node(NewSegment(), name = 'segmentation')
        segmentation.inputs.write_deformation_fields = [True, True]
        segmentation.inputs.tissues = [
            [(spm_tissues_file, 1), 1, (True,False), (True, False)],
            [(spm_tissues_file, 2), 1, (True,False), (True, False)],
            [(spm_tissues_file, 3), 2, (True,False), (True, False)],
            [(spm_tissues_file, 4), 3, (True,False), (True, False)],
            [(spm_tissues_file, 5), 4, (True,False), (True, False)],
            [(spm_tissues_file, 6), 2, (True,False), (True, False)]
        ]
        preprocessing.connect(gunzip_anat, 'out_file', segmentation, 'channel_files')

        # NORMALIZE12 - Spatial normalization of functional images
        normalize = Node(Normalize12(), name = 'normalize')
        normalize.inputs.jobtype = 'write'
        preprocessing.connect(
            segmentation, 'forward_deformation_field', normalize, 'deformation_file')
        preprocessing.connect(coregister, 'coregistered_files', normalize, 'apply_to_files')

        # SMOOTHING - 6 mm fixed FWHM smoothing in MNI volume
        smoothing = Node(Smooth(), name = 'smoothing')
        smoothing.inputs.fwhm = self.fwhm
        preprocessing.connect(normalize, 'normalized_files', smoothing, 'in_files')

        # DATASINK - store the wanted results in the wanted repository
        data_sink = Node(DataSink(), name='data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        preprocessing.connect(
            realign, 'realignment_parameters', data_sink, 'preprocessing.@motion_parameters')
        preprocessing.connect(smoothing, 'smoothed_files', data_sink, 'preprocessing.@smoothed')

        # Remove large files, if requested
        if Configuration()['pipelines']['remove_unused_data']:
            # Function Nodes remove_files - Remove sizeable anat files once they aren't needed
            remove_anat_after_datasink = Node(Function(
                function = remove_parent_directory,
                input_names = ['_', 'file_name'],
                output_names = []
                ), name = 'remove_anat_after_datasink')
            preprocessing.connect([
                (gunzip_anat, remove_anat_after_datasink, [('out_file', 'file_name')]),
                (data_sink, remove_anat_after_datasink, [('out_file', '_')])
            ])

            # Merge Node - Merge file names to be removed after datasink node is performed
            merge_removable_func_files = Node(Merge(6), name = 'merge_removable_func_files')
            merge_removable_func_files.inputs.ravel_inputs = True

            # Function Nodes remove_files - Remove sizeable files once they aren't needed
            remove_func_after_datasink = MapNode(Function(
                function = remove_parent_directory,
                input_names = ['_', 'file_name'],
                output_names = []
                ), name = 'remove_func_after_datasink', iterfield = 'file_name')
            preprocessing.connect([
                (gunzip_func, merge_removable_func_files, [('out_file', 'in1')]),
                (realign, merge_removable_func_files, [('realigned_files', 'in2')]),
                (extract_first_image, merge_removable_func_files, [('roi_file', 'in3')]),
                (coregister, merge_removable_func_files, [('coregistered_files', 'in4')]),
                (normalize, merge_removable_func_files, [('normalized_files', 'in5')]),
                (smoothing, merge_removable_func_files, [('smoothed_files', 'in6')]),
                (merge_removable_func_files, remove_func_after_datasink, [('out', 'file_name')]),
                (data_sink, remove_func_after_datasink, [('out_file', '_')])
            ])

        return preprocessing

    def get_preprocessing_outputs(self):
        """ Return the names of the files the preprocessing analysis is supposed to generate. """

        # Smoothed maps
        templates = [join(
            self.directories.output_dir,
            'preprocessing', '_subject_id_{subject_id}', '_run_id_{run_id}',
            'swrrsub-{subject_id}_task-MGT_run-{run_id}_bold.nii')]

        # Motion parameters file
        templates += [join(
            self.directories.output_dir,
            'preprocessing', '_subject_id_{subject_id}', '_run_id_{run_id}',
            'rp_sub-{subject_id}_task-MGT_run-{run_id}_bold.txt')]

        # Format with subject_ids
        return_list = []
        for template in templates:
            return_list += [template.format(subject_id = s, run_id = r)\
                for r in self.run_list for s in self.subject_list]

        return return_list

    def get_run_level_analysis(self):
        """ Return a Nipype workflow describing the run level analysis part of the pipeline """
        return None

    def get_subject_information(event_file: str):
        """
        Create Bunchs of subject event information for specifySPMModel.

        Parameters :
        - event_file: str, events file for a run of a subject

        Returns :
        - subject_info : Bunch corresponding to the event file
        """
        from nipype.interfaces.base import Bunch

        onsets = []
        durations = []
        weights_gain = []
        weights_loss = []

        # Parse event file
        with open(event_file, 'rt') as file:
            next(file)  # skip the header

            for line in file:
                info = line.strip().split()

                onsets.append(float(info[0]))
                durations.append(4.0)
                weights_gain.append(float(info[2]))
                weights_loss.append(float(info[3]))

        # Create bunch
        return Bunch(
            conditions = [f'trial'],
            onsets = [onsets],
            durations = [durations],
            amplitudes = None,
            tmod = None,
            pmod = [
                Bunch(
                    name = [f'gain', f'loss'],
                    poly = [1, 1],
                    param = [weights_gain, weights_loss]
                )
            ],
            regressor_names = None,
            regressors = None
        )

    def get_subject_level_analysis(self):
        """ Return a Nipype workflow describing the subject level analysis part of the pipeline """

        # Workflow initialization
        subject_level_analysis = Workflow(
            base_dir = self.directories.working_dir,
            name = 'subject_level_analysis'
        )

        # IDENTITY INTERFACE - Allows to iterate on subjects
        information_source = Node(IdentityInterface(fields = ['subject_id']),
            name = 'information_source')
        information_source.iterables = [('subject_id', self.subject_list)]

        # SELECTFILES - to select necessary files
        templates = {
            'func': join(self.directories.output_dir, 'preprocessing',
                '_subject_id_{subject_id}', '_run_id_*',
                'swrrsub-{subject_id}_task-MGT_run-*_bold.nii',
            ),
            'event': join(self.directories.dataset_dir, 'sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-*_events.tsv',
            ),
            'parameters': join(self.directories.output_dir, 'preprocessing',
                '_subject_id_{subject_id}', '_run_id_*',
                'rp_sub-{subject_id}_task-MGT_run-*_bold.txt',
            )
        }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.dataset_dir
        subject_level_analysis.connect(information_source, 'subject_id', select_files, 'subject_id')

        # FUNCTION node get_subject_information - get subject specific condition information
        subject_information = MapNode(Function(
                function = self.get_subject_information,
                input_names = ['event_file'],
                output_names = ['subject_info']),
            name = 'subject_information', iterfield = ['event_file'])
        subject_level_analysis.connect(select_files, 'event', subject_information, 'event_file')

        # SPECIFY MODEL - generates SPM-specific Model
        specify_model = Node(SpecifySPMModel(), name = 'specify_model')
        specify_model.inputs.concatenate_runs = True
        specify_model.inputs.input_units = 'secs'
        specify_model.inputs.output_units = 'secs'
        specify_model.inputs.time_repetition = TaskInformation()['RepetitionTime']
        specify_model.inputs.high_pass_filter_cutoff = 128
        subject_level_analysis.connect(
            subject_information, 'subject_info', specify_model, 'subject_info')
        subject_level_analysis.connect(select_files, 'func', specify_model, 'functional_runs')
        subject_level_analysis.connect(
            select_files, 'parameters', specify_model, 'realignment_parameters')

        # LEVEL1 DESIGN - generates an SPM design matrix
        model_design = Node(Level1Design(), name = 'model_design')
        model_design.inputs.bases = {'hrf': {'derivs': [0, 0]}}
        model_design.inputs.timing_units = 'secs'
        model_design.inputs.interscan_interval = TaskInformation()['RepetitionTime']
        model_design.inputs.model_serial_correlations = 'AR(1)'
        subject_level_analysis.connect(specify_model, 'session_info', model_design, 'session_info')

        # ESTIMATE MODEL - estimate the parameters of the model
        model_estimate = Node(EstimateModel(), name = 'model_estimate')
        model_estimate.inputs.estimation_method = {'Classical': 1}
        subject_level_analysis.connect(
            model_design, 'spm_mat_file', model_estimate, 'spm_mat_file')

        # ESTIMATE CONTRAST - estimates contrasts
        contrast_estimate = Node(EstimateContrast(), name = 'contrast_estimate')
        contrast_estimate.inputs.contrasts = self.subject_level_contrasts
        subject_level_analysis.connect(
            model_estimate, 'spm_mat_file', contrast_estimate, 'spm_mat_file')
        subject_level_analysis.connect(
            model_estimate, 'beta_images', contrast_estimate, 'beta_images')
        subject_level_analysis.connect(
            model_estimate, 'residual_image', contrast_estimate, 'residual_image')

        # DataSink Node - store the wanted results in the wanted repository
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        subject_level_analysis.connect(
            contrast_estimate, 'con_images', data_sink, 'subject_level_analysis.@con_images')
        subject_level_analysis.connect(
            contrast_estimate, 'spmT_images', data_sink, 'subject_level_analysis.@spmT_images')
        subject_level_analysis.connect(
            contrast_estimate, 'spm_mat_file', data_sink, 'subject_level_analysis.@spm_mat_file')

        return subject_level_analysis

    def get_subject_level_outputs(self):
        """ Return the names of the files the subject level analysis is supposed to generate. """

        # Contrat maps
        templates = [join(self.directories.output_dir, 'subject_level_analysis',
            '_subject_id_{subject_id}', f'con_{contrast_id}.nii')\
            for contrast_id in self.contrast_list]

        # SPM.mat file
        templates += [join(self.directories.output_dir, 'subject_level_analysis',
            '_subject_id_{subject_id}', 'SPM.mat')]

        # spmT maps
        templates += [join(self.directories.output_dir, 'subject_level_analysis',
            '_subject_id_{subject_id}', f'spmT_{contrast_id}.nii')\
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

        # Initialize workflow
        group_level_analysis = Workflow(
            base_dir = self.directories.working_dir,
            name = f'group_level_analysis_{method}_nsub_{nb_subjects}')

        # IDENTITY INTERFACE - iterate over the list of contrasts
        information_source = Node(
            IdentityInterface(
                fields = ['contrast_id', 'subjects']),
                name = 'information_source')
        information_source.iterables = [('contrast_id', self.contrast_list)]

        # SELECT FILES - select contrasts for all subjects
        templates = {
            'contrasts' : join('subject_level_analysis', '_subject_id_*', 'con_{contrast_id}.nii')
            }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.output_dir
        select_files.inputs.force_list = True
        group_level_analysis.connect(
            information_source, 'contrast_id', select_files, 'contrast_id')

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
        group_level_analysis.connect(select_files, 'contrasts', get_contrasts, 'input_str')

        # ESTIMATE MODEL - (inputs are set below, depending on the method used)
        estimate_model = Node(EstimateModel(), name = 'estimate_model')
        estimate_model.inputs.estimation_method = {'Classical':1}

        # Estimate contrasts
        estimate_contrast = Node(EstimateContrast(), name = 'estimate_contrast')
        estimate_contrast.inputs.group_contrast = True
        group_level_analysis.connect(
            estimate_model, 'spm_mat_file', estimate_contrast, 'spm_mat_file')
        group_level_analysis.connect(
            estimate_model, 'residual_image', estimate_contrast, 'residual_image')
        group_level_analysis.connect(
            estimate_model, 'beta_images', estimate_contrast, 'beta_images')

        # Create thresholded maps
        threshold = MapNode(Threshold(),
            name = 'threshold', iterfield = ['stat_image', 'contrast_index'])
        threshold.inputs.height_threshold = 0.001
        threshold.inputs.height_threshold_type = 'p-value'
        threshold.inputs.extent_fdr_p_threshold = 0.05
        threshold.inputs.force_activation = True
        group_level_analysis.connect(
            estimate_contrast, 'spm_mat_file', threshold, 'spm_mat_file')
        group_level_analysis.connect(
            estimate_contrast, 'spmT_images', threshold, 'stat_image')

        if method in ('equalRange', 'equalIndifference'):
            estimate_contrast.inputs.contrasts = [
                ('Group', 'T', ['mean'], [1]), ('Group', 'T', ['mean'], [-1])
                ]

            threshold.inputs.contrast_index = [1, 2]
            threshold.synchronize = True

            # Specify design matrix
            one_sample_t_test_design = Node(OneSampleTTestDesign(),
                name = 'one_sample_t_test_design')
            group_level_analysis.connect(
                one_sample_t_test_design, 'spm_mat_file', estimate_model, 'spm_mat_file')
            group_level_analysis.connect(
                get_contrasts, ('out_list', clean_list), one_sample_t_test_design, 'in_files')

        if method == 'equalRange':
            group_level_analysis.connect(
                get_equal_range_subjects, ('out_list', complete_subject_ids),
                get_contrasts, 'elements'
                )

        elif method == 'equalIndifference':
            group_level_analysis.connect(
                get_equal_indifference_subjects, ('out_list', complete_subject_ids),
                get_contrasts, 'elements'
                )

        elif method == 'groupComp':
            estimate_contrast.inputs.contrasts = [
                ('Eq range vs Eq indiff in loss', 'T', ['Group_{1}', 'Group_{2}'], [-1, 1])
                ]

            threshold.inputs.contrast_index = [1]
            threshold.synchronize = True

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

            # Node for the design matrix
            two_sample_t_test_design = Node(TwoSampleTTestDesign(),
                name = 'two_sample_t_test_design')

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

        # Datasink - save important files
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        group_level_analysis.connect(estimate_model, 'mask_image',
            data_sink, f'group_level_analysis_{method}_nsub_{nb_subjects}.@mask')
        group_level_analysis.connect(estimate_contrast, 'spm_mat_file',
            data_sink, f'group_level_analysis_{method}_nsub_{nb_subjects}.@spm_mat')
        group_level_analysis.connect(estimate_contrast, 'spmT_images',
            data_sink, f'group_level_analysis_{method}_nsub_{nb_subjects}.@T')
        group_level_analysis.connect(estimate_contrast, 'con_images',
            data_sink, f'group_level_analysis_{method}_nsub_{nb_subjects}.@con')
        group_level_analysis.connect(threshold, 'thresholded_map',
            data_sink, f'group_level_analysis_{method}_nsub_{nb_subjects}.@thresh')

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
        template = join(self.directories.output_dir,
            'group_level_analysis_{method}_nsub_{nb_subjects}', '_contrast_id_{contrast_id}',
            '{file}')

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
        """ Return all hypotheses output file names. """
        nb_sub = len(self.subject_list)
        files = [
            # Hypothesis 1
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0001.nii'),
            # Hypothesis 2
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0001.nii'),
            # Hypothesis 3
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0001.nii'),
            # Hypothesis 4
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0001.nii'),
            # Hypothesis 5
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0005', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0005', 'spmT_0001.nii'),
            # Hypothesis 6
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0005', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0005', 'spmT_0001.nii'),
            # Hypothesis 7
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0003', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0003', 'spmT_0001.nii'),
            # Hypothesis 8
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0003', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0003', 'spmT_0001.nii'),
            # Hypothesis 9
            join(f'group_level_analysis_groupComp_nsub_{nb_sub}',
                '_contrast_id_0003', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_groupComp_nsub_{nb_sub}',
                '_contrast_id_0003', 'spmT_0001.nii')
        ]
        return [join(self.directories.output_dir, f) for f in files]
