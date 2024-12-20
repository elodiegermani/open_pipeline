#!/usr/bin/python
# coding: utf-8

""" Write the work of NARPS team 0I4U using Nipype """
from os.path import join
from itertools import product

from nipype import Workflow, Node, MapNode
from nipype.interfaces.utility import IdentityInterface, Function, Merge, Split
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.algorithms.misc import Gunzip
from nipype.interfaces.spm import (
    Coregister, OneSampleTTestDesign,
    EstimateModel, EstimateContrast, Level1Design,
    TwoSampleTTestDesign, RealignUnwarp, NewSegment,
    FieldMap, Threshold, Normalize12, Smooth
    )
from nipype.interfaces.spm.base import Info as SPMInfo
from nipype.interfaces.fsl import ApplyMask, ExtractROI, MathsCommand
from nipype.algorithms.modelgen import SpecifySPMModel

from narps_open.pipelines import Pipeline
from narps_open.data.task import TaskInformation
from narps_open.data.participants import get_group, get_participants_information
from narps_open.core.common import (
    remove_parent_directory, list_intersection, elements_in_string, clean_list
    )
from narps_open.utils.configuration import Configuration

class PipelineTeam0I4U(Pipeline):
    """ A class that defines the pipeline of team 0I4U. """

    def __init__(self):
        super().__init__()
        self.fwhm = 5.0
        self.team_id = '0I4U'
        self.contrast_list = ['0001', '0002']

        # Define contrasts
        gain_conditions = [f'trial_run{r}xgain^1' for r in range(1,len(self.run_list) + 1)]
        loss_conditions = [f'trial_run{r}xloss^1' for r in range(1,len(self.run_list) + 1)]
        self.subject_level_contrasts = [
            ('gain', 'T', gain_conditions, [1] * len(self.run_list)),
            ('loss', 'T', loss_conditions, [1] * len(self.run_list))
            ]

    def get_preprocessing(self):
        """ Return a nipype.WorkFlow for the preprocessing part of the pipeline. """

        # Initialize workflow
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

        # SELECT FILES - select subject files
        templates = {
            'anat' : join('sub-{subject_id}', 'anat', 'sub-{subject_id}_T1w.nii.gz'),
            'magnitude' : join('sub-{subject_id}', 'fmap', 'sub-{subject_id}_magnitude1.nii.gz'),
            'phasediff' : join('sub-{subject_id}', 'fmap', 'sub-{subject_id}_phasediff.nii.gz')
        }
        select_subject_files = Node(SelectFiles(templates), name = 'select_subject_files')
        select_subject_files.inputs.base_directory = self.directories.dataset_dir
        preprocessing.connect(
            information_source_subject, 'subject_id', select_subject_files, 'subject_id')

        # SELECT FILES - select run files
        template = {
            'func' : join('sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-{run_id}_bold.nii.gz')
        }
        select_run_files = Node(SelectFiles(template), name = 'select_run_files')
        select_run_files.inputs.base_directory = self.directories.dataset_dir
        preprocessing.connect(
            information_source_runs, 'subject_id', select_run_files, 'subject_id')
        preprocessing.connect(information_source_runs, 'run_id', select_run_files, 'run_id')

        # GUNZIP NODE - SPM do not use .nii.gz files
        gunzip_anat = Node(Gunzip(), name = 'gunzip_anat')
        gunzip_func = Node(Gunzip(), name = 'gunzip_func')
        gunzip_magnitude = Node(Gunzip(), name = 'gunzip_magnitude')
        gunzip_phasediff = Node(Gunzip(), name = 'gunzip_phasediff')
        preprocessing.connect(select_subject_files, 'anat', gunzip_anat, 'in_file')
        preprocessing.connect(select_subject_files, 'magnitude', gunzip_magnitude, 'in_file')
        preprocessing.connect(select_subject_files, 'phasediff', gunzip_phasediff, 'in_file')
        preprocessing.connect(select_run_files, 'func', gunzip_func, 'in_file')

        # FIELDMAP - create field map from phasediff and magnitude file
        fieldmap = Node(FieldMap(), name = 'fieldmap')
        fieldmap.inputs.blip_direction = -1
        fieldmap.inputs.echo_times = (4.92, 7.38)
        fieldmap.inputs.total_readout_time = 29.15
        fieldmap.inputs.matchanat = True
        fieldmap.inputs.matchvdm = True
        fieldmap.inputs.writeunwarped = True
        fieldmap.inputs.maskbrain = False
        fieldmap.inputs.thresh = 0
        preprocessing.connect(gunzip_anat, 'out_file', fieldmap, 'anat_file')
        preprocessing.connect(gunzip_magnitude, 'out_file', fieldmap, 'magnitude_file')
        preprocessing.connect(gunzip_phasediff, 'out_file', fieldmap, 'phase_file')
        preprocessing.connect(gunzip_func, 'out_file', fieldmap, 'epi_file')

        # REALIGN UNWARP - motion correction
        motion_correction = Node(RealignUnwarp(), name = 'motion_correction')
        motion_correction.inputs.interp = 4
        motion_correction.inputs.register_to_mean = False
        preprocessing.connect(fieldmap, 'vdm', motion_correction, 'phase_map')
        preprocessing.connect(gunzip_func, 'out_file', motion_correction, 'in_files')

        # EXTRACTROI - extracting the first image of func
        extract_first_image = Node(ExtractROI(), name = 'extract_first_image')
        extract_first_image.inputs.t_min = 1
        extract_first_image.inputs.t_size = 1
        extract_first_image.inputs.output_type='NIFTI'
        preprocessing.connect(
            motion_correction, 'realigned_unwarped_files', extract_first_image, 'in_file')

        # COREGISTER - Co-registration in SPM12 using default parameters.
        coregistration = Node(Coregister(), name = 'coregistration')
        coregistration.inputs.jobtype = 'estimate'
        coregistration.inputs.write_mask = False
        preprocessing.connect(gunzip_anat, 'out_file', coregistration, 'target')
        preprocessing.connect(extract_first_image, 'roi_file', coregistration, 'source')
        preprocessing.connect(
            motion_correction, 'realigned_unwarped_files', coregistration, 'apply_to_files')

        # Get SPM Tissue Probability Maps file
        spm_tissues_file = join(SPMInfo.getinfo()['path'], 'tpm', 'TPM.nii')

        # NEW SEGMENT - Unified segmentation using tissue probability maps in SPM12.
        segmentation = Node(NewSegment(), name = 'segmentation')
        segmentation.inputs.write_deformation_fields = [False, True]
        segmentation.inputs.tissues = [
            [(spm_tissues_file, 1), 2, (True, False), (True, False)], # Grey matter
            [(spm_tissues_file, 2), 2, (True, False), (True, False)], # White matter
            [(spm_tissues_file, 3), 2, (True, False), (True, False)], # CSF
            [(spm_tissues_file, 4), 3, (True, False), (True, False)], # Bone
            [(spm_tissues_file, 5), 4, (True, False), (True, False)], # Soft tissue
            [(spm_tissues_file, 6), 2, (True, False), (True, False)] # Air / background
        ]
        preprocessing.connect(gunzip_anat, 'out_file', segmentation, 'channel_files')

        # NORMALIZE12 - Spatial normalization of functional images
        normalize = Node(Normalize12(), name = 'normalize')
        normalize.inputs.write_voxel_sizes = [1.5, 1.5, 1.5]
        normalize.inputs.jobtype = 'write'
        preprocessing.connect(
            segmentation, 'forward_deformation_field', normalize, 'deformation_file')
        preprocessing.connect(coregistration, 'coregistered_files', normalize, 'apply_to_files')

        # SPLIT - Split probability maps as they output from the segmentation node
        #   outputs.out1 is Grey matter (c1*)
        #   outputs.out2 is White matter (c2*)
        #   outputs.out3 is CSF (c3*)
        split_segmentation_maps = Node(Split(), name = 'split_segmentation_maps')
        split_segmentation_maps.inputs.splits = [1, 1, 1, 3]
        split_segmentation_maps.inputs.squeeze = True # Unfold one-element splits removing the list
        preprocessing.connect(
            segmentation, 'normalized_class_images', split_segmentation_maps, 'inlist')

        # MATHS COMMAND - create grey-matter mask
        #     Values below 0.2 will be set to 0.0, others to 1.0
        threshold_grey_matter = Node(MathsCommand(), name = 'threshold_grey_matter')
        threshold_grey_matter.inputs.args = '-thr 0.2 -bin'
        threshold_grey_matter.inputs.output_type = 'NIFTI'
        preprocessing.connect(split_segmentation_maps, 'out1', threshold_grey_matter, 'in_file')

        # MASKING - Mask func using segmented and normalized grey matter mask
        mask_func = MapNode(ApplyMask(), name = 'mask_func', iterfield = 'in_file')
        preprocessing.connect(normalize, 'normalized_files', mask_func, 'in_file')
        preprocessing.connect(threshold_grey_matter, 'out_file', mask_func, 'mask_file')

        # SMOOTHING - 5 mm fixed FWHM smoothing
        smoothing = Node(Smooth(), name = 'smoothing')
        smoothing.inputs.fwhm = self.fwhm
        preprocessing.connect(mask_func, 'out_file', smoothing, 'in_files')

        # DATASINK - store the wanted results in the wanted repository
        data_sink = Node(DataSink(), name='data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        preprocessing.connect(
            motion_correction,'realignment_parameters', data_sink, 'preprocess.@realign_par')
        preprocessing.connect(smoothing, 'smoothed_files', data_sink, 'preprocessing.@smoothed')

        # Remove large files, if requested
        if Configuration()['pipelines']['remove_unused_data']:

            # Merge Node - Merge anat file names to be removed after datasink node is performed
            merge_removable_anat_files = Node(Merge(5), name = 'merge_removable_anat_files')
            merge_removable_anat_files.inputs.ravel_inputs = True

            # Function Nodes remove_files - Remove sizeable anat files once they aren't needed
            remove_anat_after_datasink = MapNode(Function(
                function = remove_parent_directory,
                input_names = ['_', 'file_name'],
                output_names = []
                ), name = 'remove_anat_after_datasink', iterfield = 'file_name')
            # Add connections
            preprocessing.connect([
                (gunzip_anat, merge_removable_anat_files, [('out_file', 'in1')]),
                (gunzip_phasediff, merge_removable_anat_files, [('out_file', 'in2')]),
                (gunzip_magnitude, merge_removable_anat_files, [('out_file', 'in3')]),
                (fieldmap, merge_removable_anat_files, [('vdm', 'in4')]),
                (segmentation, merge_removable_anat_files, [('forward_deformation_field', 'in5')]),
                (merge_removable_anat_files, remove_anat_after_datasink, [('out', 'file_name')]),
                (data_sink, remove_anat_after_datasink, [('out_file', '_')])
            ])

            # Merge Node - Merge func file names to be removed after datasink node is performed
            merge_removable_func_files = Node(Merge(11), name = 'merge_removable_func_files')
            merge_removable_func_files.inputs.ravel_inputs = True

            # Function Nodes remove_files - Remove sizeable func files once they aren't needed
            remove_func_after_datasink = MapNode(Function(
                function = remove_parent_directory,
                input_names = ['_', 'file_name'],
                output_names = []
                ), name = 'remove_func_after_datasink', iterfield = 'file_name')
            preprocessing.connect([
                (gunzip_func, merge_removable_func_files, [('out_file', 'in1')]),
                (motion_correction, merge_removable_func_files, [
                    ('realigned_unwarped_files', 'in2')]),
                (extract_first_image, merge_removable_func_files, [('roi_file', 'in3')]),
                (coregistration, merge_removable_func_files, [('coregistered_files', 'in4')]),
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

    def get_subject_information(event_file: str, short_run_id: int):
        """
        Create Bunchs of subject event information for specifySPMModel.

        Event-related design, 4 within subject sessions
        1 Condition: Stimulus presentation, onsets based on tsv file, duration 4 seconds
        2 Parametric modulators: Gain and loss modelled with 1st order polynomial expansion
        1 Condition: button press, onsets based on tsv file, duration 0 seconds

        Parameters :
        - event_file: str, events file for a run of a subject
        - short_run_id: str, an identifier for the run corresponding to the event_file
            must be '1' for the first run, '2' for the second run, etc.

        Returns :
        - subject_info : Bunch corresponding to the event file
        """
        from nipype.interfaces.base import Bunch

        onset_trial = []
        duration_trial = []
        weights_gain = []
        weights_loss = []
        onset_button = []
        duration_button = []

        with open(event_file, 'rt') as file:
            next(file)  # skip the header

            for line in file:
                info = line.strip().split()

                onset_trial.append(float(info[0]))
                duration_trial.append(4.0)
                weights_gain.append(float(info[2]))
                weights_loss.append(float(info[3]))
                onset_button.append(float(info[0]) + float(info[4]))
                duration_button.append(0.0)

        # Create bunch
        return Bunch(
            conditions = [f'trial_run{short_run_id}', f'button_run{short_run_id}'],
            onsets = [onset_trial, onset_button],
            durations = [duration_trial, duration_button],
            amplitudes = None,
            tmod = None,
            pmod = [
                Bunch(
                    name = ['gain', 'loss'],
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
                'wusub-{subject_id}_task-MGT_run-*_bold.nii',
            ),
            'event': join('sub-{subject_id}', 'func', 'sub-{subject_id}_task-MGT_run-*_events.tsv',
            ),
            'parameters': join(self.directories.output_dir, 'preprocessing',
                '_subject_id_{subject_id}', '_run_id_*',
                'rp_sub-{subject_id}_task-MGT_run-*_bold.txt',
            )
        }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.dataset_dir
        subject_level_analysis.connect(
            information_source, 'subject_id', select_files, 'subject_id')

        # FUNCTION node get_subject_information - get subject specific condition information
        subject_information = MapNode(Function(
                function = self.get_subject_information,
                input_names = ['event_file', 'short_run_id'],
                output_names = ['subject_info']),
            name = 'subject_information', iterfield = ['event_file', 'short_run_id'])
        subject_information.inputs.short_run_id = list(range(1, len(self.run_list) + 1))
        subject_level_analysis.connect(select_files, 'event', subject_information, 'event_file')

        # SPECIFY MODEL - Generates SPM-specific Model
        specify_model = Node(SpecifySPMModel(), name='specify_model')
        specify_model.inputs.concatenate_runs = False
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
        model_design.inputs.bases = {'hrf': {'derivs': [1, 0]}}
        model_design.inputs.timing_units = 'secs'
        model_design.inputs.interscan_interval = TaskInformation()['RepetitionTime']
        model_design.inputs.model_serial_correlations = 'AR(1)'
        subject_level_analysis.connect(specify_model, 'session_info', model_design, 'session_info')

        # ESTIMATE MODEL - estimate the parameters of the model
        model_estimate = Node(EstimateModel(), name = 'model_estimate')
        model_estimate.inputs.estimation_method = {'Classical': 1}
        model_estimate.inputs.write_residuals = False
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

    def get_covariates_single_group(subject_list: list, participants):
        """
        From a list of subjects, create covariates (age, gender) for the group level model,
        in the case of single group (equalRange or equalIndifference) models.

        Parameters :
        - subject_list : list of subject IDs that are in the wanted group for the analysis
            note that this list will be sorted
        - participants: pandas.DataFrame, file containing participants characteristics

        Returns : list, formatted covariates for group level analysis. As specified in nipype doc:
            Covariate dictionary {vector, name, interaction, centering}
        """
        # Filter participant data
        sub_list = [f'sub-{s}' for s in subject_list]
        sub_list.sort()
        filtered = participants[participants['participant_id'].isin(sub_list)]

        # Create age and gender covariates
        ages = [float(a) for a in filtered['age'].tolist()]
        genders = [0 if g =='M' else 1 for g in filtered['gender'].tolist()]

        # Return covariates dict
        return [
            {'vector': ages, 'name': 'age', 'centering': [1]},
            {'vector': genders, 'name': 'gender', 'centering': [1]}
            ]

    def get_covariates_group_comp(subject_list_g1: list, subject_list_g2: list, participants):
        """
        From a list of subjects, create covariates (age, gender) for the group level model,
            in the case of group comparison model.

        Parameters :
        - subject_list_g1 : list of subject ids in the analysis and in the first group
            note that this list will be sorted
        - subject_list_g2 : list of subject ids in the analysis and in the second group
            note that this list will be sorted
        - participants: pandas.DataFrame, file containing participants characteristics

        Returns : list, formatted covariates for group level analysis. As specified in nipype doc:
            Covariate dictionary {vector, name, interaction, centering}
        """
        # Filter participant data
        sub_list_g1 = [f'sub-{s}' for s in subject_list_g1]
        sub_list_g1.sort()
        filtered_g1 = participants[participants['participant_id'].isin(sub_list_g1)]
        sub_list_g2 = [f'sub-{s}' for s in subject_list_g2]
        sub_list_g2.sort()
        filtered_g2 = participants[participants['participant_id'].isin(sub_list_g2)]

        # Create age and gender covariates
        ages = [float(a) for a in filtered_g1['age'].tolist()]
        ages += [float(a) for a in filtered_g2['age'].tolist()]
        genders = [0.0 if g =='M' else 1.0 for g in filtered_g1['gender'].tolist()]
        genders += [0.0 if g =='M' else 1.0 for g in filtered_g2['gender'].tolist()]

        # Return covariates dict
        return [
            {'vector': ages, 'name': 'age', 'centering': [1]},
            {'vector': genders, 'name': 'gender', 'centering': [1]},
            ]

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
            'contrast' : join('subject_level_analysis', '_subject_id_*', 'con_{contrast_id}.nii'),
            'participants' : join(self.directories.dataset_dir, 'participants.tsv')
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

        # ESTIMATE CONTRASTS
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
        threshold.inputs.use_fwe_correction = True
        threshold.inputs.height_threshold_type = 'p-value'
        threshold.inputs.force_activation = False
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

            # Function Node get_covariates_single_group
            #   Get covariates for the single group analysis model
            get_covariates = Node(Function(
                function = self.get_covariates_single_group,
                input_names = ['subject_list', 'participants'],
                output_names = ['covariates']
                ),
                name = 'get_covariates'
            )
            get_covariates.inputs.participants = get_participants_information()

            # Specify design matrix
            one_sample_t_test_design = Node(OneSampleTTestDesign(),
                name = 'one_sample_t_test_design')
            group_level_analysis.connect(
                one_sample_t_test_design, 'spm_mat_file', estimate_model, 'spm_mat_file')
            group_level_analysis.connect(
                get_contrasts, ('out_list', clean_list), one_sample_t_test_design, 'in_files')
            group_level_analysis.connect(
                get_covariates, 'covariates', one_sample_t_test_design, 'covariates')

        if method == 'equalRange':
            group_level_analysis.connect(
                get_equal_range_subjects, ('out_list', complete_subject_ids),
                get_contrasts, 'elements'
                )
            group_level_analysis.connect(
                get_equal_range_subjects, 'out_list', get_covariates, 'subject_list')

        elif method == 'equalIndifference':
            group_level_analysis.connect(
                get_equal_indifference_subjects, ('out_list', complete_subject_ids),
                get_contrasts, 'elements'
                )
            group_level_analysis.connect(
                get_equal_indifference_subjects, 'out_list' , get_covariates, 'subject_list')

        elif method == 'groupComp':
            estimate_contrast.inputs.contrasts = [
                ('Eq range vs Eq indiff in loss', 'T', ['Group_{1}', 'Group_{2}'], [-1, 1])
                ]

            threshold.inputs.contrast_index = [1]
            threshold.synchronize = True

            group_level_analysis.connect(
                get_equal_range_subjects, ('out_list', complete_subject_ids),
                get_contrasts, 'elements')

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
            group_level_analysis.connect(select_files, 'contrasts', get_contrasts_2, 'input_str')
            group_level_analysis.connect(
                get_equal_indifference_subjects, ('out_list', complete_subject_ids),
                get_contrasts_2, 'elements')

            # Function Node get_covariates_group_comp
            #   Get covariates for the group comparison analysis model
            get_covariates = Node(Function(
                function = self.get_covariates_group_comp,
                input_names = ['subject_list_g1', 'subject_list_g2', 'participants'],
                output_names = ['covariates']
                ),
                name = 'get_covariates'
            )
            get_covariates.inputs.participants = get_participants_information()
            group_level_analysis.connect(
                get_equal_range_subjects, 'out_list' , get_covariates, 'subject_list_g1')
            group_level_analysis.connect(
                get_equal_indifference_subjects, 'out_list' , get_covariates, 'subject_list_g2')

            # Node for the design matrix
            two_sample_t_test_design = Node(TwoSampleTTestDesign(),
                name = 'two_sample_t_test_design')
            group_level_analysis.connect(
                get_contrasts, ('out_list', clean_list),
                two_sample_t_test_design, 'group1_files')
            group_level_analysis.connect(
                get_contrasts_2, ('out_list', clean_list),
                two_sample_t_test_design, 'group2_files')
            group_level_analysis.connect(
                get_covariates, 'covariates', two_sample_t_test_design, 'covariates')

            # Connect to model estimation
            group_level_analysis.connect(
                two_sample_t_test_design, 'spm_mat_file', estimate_model, 'spm_mat_file')

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
