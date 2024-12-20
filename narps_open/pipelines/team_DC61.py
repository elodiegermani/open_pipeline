#!/usr/bin/python
# coding: utf-8

""" Write the work of NARPS' team DC61 using Nipype """

from os.path import join
from itertools import product

from nipype import Workflow, Node, MapNode
from nipype.interfaces.utility import IdentityInterface, Function
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.interfaces.spm import (
    Smooth,
    OneSampleTTestDesign, EstimateModel, EstimateContrast,
    Level1Design, TwoSampleTTestDesign, Threshold
    )
from nipype.algorithms.modelgen import SpecifySPMModel
from nipype.algorithms.misc import Gunzip

from narps_open.pipelines import Pipeline
from narps_open.data.task import TaskInformation
from narps_open.data.participants import get_group
from narps_open.core.interfaces import InterfaceFactory
from narps_open.core.common import list_intersection, elements_in_string, clean_list
from narps_open.utils.configuration import Configuration

class PipelineTeamDC61(Pipeline):
    """ A class that defines the pipeline of team DC61. """

    def __init__(self):
        super().__init__()
        self.fwhm = 5.0
        self.team_id = 'DC61'
        self.contrast_list = ['0001', '0002']

        # Give a weight of 1/N to each regressor, N being the number of runs
        nb_runs = len(self.run_list)
        self.subject_level_contrasts = [
            ('effect_of_gain', 'T',
                [f'gamble_run{r}xgain_param^1' for r in range(1, nb_runs + 1)],
                [1.0 / nb_runs] * nb_runs),
            ('effect_of_loss', 'T',
                [f'gamble_run{r}xloss_param^1' for r in range(1, nb_runs + 1)],
                [1.0 / nb_runs] * nb_runs)
        ]

    def get_preprocessing(self):
        """ No preprocessing has been done by team DC61 """
        return None

    def get_run_level_analysis(self):
        """ No run level analysis has been done by team DC61 """
        return None

    # @staticmethod # Starting python 3.10, staticmethod should be used here
    # Otherwise it produces a TypeError: 'staticmethod' object is not callable
    def get_subject_information(event_file: str, short_run_id: str):
        """ Create Bunchs for SpecifySPMModel.

        Parameters :
        - event_file: str, events file for the run
        - short_run_id: int, 1-based shortened run id (1 for for first run, etc...)

        Returns :
        - subject_info: Bunch with event info for 1st level analysis
        """
        from nipype.interfaces.base import Bunch

        onsets = []
        durations = []
        gain_value = []
        loss_value = []
        reaction_time = []

        # Parse the events file
        with open(event_file, 'rt') as file:
            next(file)  # skip the header

            for line in file:
                info = line.strip().split()

                onsets.append(float(info[0]))
                durations.append(float(info[1]))
                gain_value.append(float(info[2]))
                loss_value.append(float(info[3]))
                reaction_time.append(float(info[4]))

        # Create a Bunch for the run
        return Bunch(
                conditions = [f'gamble_run{short_run_id}'],
                onsets = [onsets],
                durations = [durations],
                amplitudes = None,
                tmod = None,
                pmod = [
                    Bunch(
                        name = ['gain_param', 'loss_param', 'rt_param'],
                        poly = [1, 1, 1],
                        param = [gain_value, loss_value, reaction_time]
                    )
                ],
                regressor_names = None,
                regressors = None
            )

    # @staticmethod # Starting python 3.10, staticmethod should be used here
    # Otherwise it produces a TypeError: 'staticmethod' object is not callable
    def get_confounds_file(filepath, subject_id, run_id, working_dir):
        """
        Create a new tsv files with only desired confounds per subject per run.
        Also computes the first derivative of the motion parameters.

        Parameters :
        - filepath : path to the subject confounds file
        - subject_id : related subject id
        - run_id : related run id
        - working_dir: str, name of the directory for intermediate results

        Return :
        - confounds_file : path to new file containing only desired confounds
        """
        from os import makedirs
        from os.path import join

        from pandas import DataFrame, read_csv
        from numpy import array, transpose, diff, square, insert

        # Open original confounds file
        data_frame = read_csv(filepath, sep = '\t', header=0)

        # Extract confounds we want to use for the model
        retained_parameters = DataFrame(transpose(array([
            data_frame['X'], data_frame['Y'], data_frame['Z'],
            data_frame['RotX'], data_frame['RotY'], data_frame['RotZ'],
            insert(diff(data_frame['X']), 0, 0),
            insert(diff(data_frame['Y']), 0, 0),
            insert(diff(data_frame['Z']), 0, 0),
            insert(diff(data_frame['RotX']), 0, 0),
            insert(diff(data_frame['RotY']), 0, 0),
            insert(diff(data_frame['RotZ']), 0, 0),
            square(data_frame['X']), square(data_frame['Y']), square(data_frame['Z']),
            square(data_frame['RotX']), square(data_frame['RotY']), square(data_frame['RotZ']),
            insert(square(diff(data_frame['X'])), 0, 0),
            insert(square(diff(data_frame['Y'])), 0, 0),
            insert(square(diff(data_frame['Z'])), 0, 0),
            insert(square(diff(data_frame['RotX'])), 0, 0),
            insert(square(diff(data_frame['RotY'])), 0, 0),
            insert(square(diff(data_frame['RotZ'])), 0, 0)
            ])))

        # Write confounds to a file
        confounds_file = join(working_dir, 'confounds_files',
            f'confounds_file_sub-{subject_id}_run-{run_id}.tsv')

        makedirs(join(working_dir, 'confounds_files'), exist_ok = True)

        with open(confounds_file, 'w', encoding = 'utf-8') as writer:
            writer.write(retained_parameters.to_csv(
                sep = '\t', index = False, header = False, na_rep = '0.0'))

        return confounds_file

    def get_subject_level_analysis(self):
        """
        Create the subject level analysis workflow.

        Returns:
            - subject_level : nipype.WorkFlow
        """
        # Initialize preprocessing workflow to connect nodes along the way
        subject_level = Workflow(
            base_dir = self.directories.working_dir, name = 'subject_level'
            )

        # Identity interface Node - to iterate over subject_id and run
        info_source = Node(
            IdentityInterface(fields = ['subject_id']),
            name = 'info_source')
        info_source.iterables = [('subject_id', self.subject_list)]

        # Select files from derivatives
        templates = {
            'func': join('derivatives', 'fmriprep', 'sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-*_bold_space-MNI152NLin2009cAsym_preproc.nii.gz'),
            'confounds' : join('derivatives', 'fmriprep', 'sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-*_bold_confounds.tsv'),
            'events': join('sub-{subject_id}', 'func',
               'sub-{subject_id}_task-MGT_run-*_events.tsv')
        }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.dataset_dir
        select_files.inputs.sort_filelist = True
        subject_level.connect(info_source, 'subject_id', select_files, 'subject_id')

        # Gunzip - gunzip files because SPM do not use .nii.gz files
        gunzip = MapNode(Gunzip(), name = 'gunzip', iterfield=['in_file'])
        subject_level.connect(select_files, 'func', gunzip, 'in_file')

        # Smoothing - smooth the func data
        smooth = Node(Smooth(), name = 'smooth')
        smooth.inputs.fwhm = self.fwhm
        smooth.overwrite = False
        subject_level.connect(gunzip, 'out_file', smooth, 'in_files')

        # Function node get_subject_info - get subject specific condition information
        subject_info = MapNode(Function(
            function = self.get_subject_information,
            input_names = ['event_file', 'short_run_id'],
            output_names = ['subject_info']
            ),
            name = 'subject_info', iterfield = ['event_file', 'short_run_id'])
        subject_info.inputs.short_run_id = list(range(1, len(self.run_list) + 1))
        subject_level.connect(select_files, 'events', subject_info, 'event_file')

        # Function node get_confounds_file - Generate confounds files
        confounds = MapNode(Function(
            function = self.get_confounds_file,
            input_names = ['filepath', 'subject_id', 'run_id', 'working_dir'],
            output_names = ['confounds_file']),
            name = 'confounds', iterfield = ['filepath', 'run_id'])
        confounds.inputs.working_dir = self.directories.working_dir
        confounds.inputs.run_id = self.run_list
        subject_level.connect(info_source, 'subject_id', confounds, 'subject_id')
        subject_level.connect(select_files, 'confounds', confounds, 'filepath')

        specify_model = Node(SpecifySPMModel(), name = 'specify_model')
        specify_model.inputs.concatenate_runs = False
        specify_model.inputs.input_units = 'secs'
        specify_model.inputs.output_units = 'secs'
        specify_model.inputs.time_repetition = TaskInformation()['RepetitionTime']
        specify_model.inputs.high_pass_filter_cutoff = 128
        specify_model.overwrite = False
        subject_level.connect(subject_info, 'subject_info', specify_model, 'subject_info')
        subject_level.connect(confounds, 'confounds_file', specify_model, 'realignment_parameters')
        subject_level.connect(smooth, 'smoothed_files', specify_model, 'functional_runs')

        model_design = Node(Level1Design(), name = 'model_design')
        model_design.inputs.bases = {'hrf': {'derivs': [1, 0]}} # Temporal derivatives
        model_design.inputs.timing_units = 'secs'
        model_design.inputs.interscan_interval = TaskInformation()['RepetitionTime']
        model_design.overwrite = False
        subject_level.connect(specify_model, 'session_info', model_design, 'session_info')

        model_estimate = Node(EstimateModel(), name = 'model_estimate')
        model_estimate.inputs.estimation_method = {'Classical': 1}
        model_estimate.overwrite = False
        subject_level.connect(model_design, 'spm_mat_file', model_estimate, 'spm_mat_file')

        contrast_estimate = Node(EstimateContrast(), name = 'contraste_estimate')
        contrast_estimate.inputs.contrasts = self.subject_level_contrasts
        contrast_estimate.config = {'execution': {'remove_unnecessary_outputs': False}}
        contrast_estimate.overwrite = False
        subject_level.connect(model_estimate, 'spm_mat_file', contrast_estimate, 'spm_mat_file')
        subject_level.connect(model_estimate, 'beta_images', contrast_estimate, 'beta_images')
        subject_level.connect(
            model_estimate, 'residual_image', contrast_estimate, 'residual_image')

        # DataSink - store the wanted results in the wanted repository
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        subject_level.connect(
            contrast_estimate, 'con_images', data_sink, f'{subject_level.name}.@con_images')
        subject_level.connect(
            contrast_estimate, 'spm_mat_file', data_sink, f'{subject_level.name}.@spm_mat_file')

        # Remove large files, if requested
        if Configuration()['pipelines']['remove_unused_data']:

            # Remove Node - Remove gunzip files once they are no longer needed
            remove_gunzip = MapNode(
                InterfaceFactory.create('remove_parent_directory'),
                name = 'remove_gunzip',
                iterfield = ['file_name']
                )

            # Remove Node - Remove smoothed files once they are no longer needed
            remove_smooth = MapNode(
                InterfaceFactory.create('remove_parent_directory'),
                name = 'remove_smooth',
                iterfield = ['file_name']
                )

            # Add connections
            subject_level.connect([
                (smooth, remove_gunzip, [('smoothed_files', '_')]),
                (gunzip, remove_gunzip, [('out_file', 'file_name')]),
                (data_sink, remove_smooth, [('out_file', '_')]),
                (smooth, remove_smooth, [('smoothed_files', 'file_name')])
                ])

        return subject_level

    def get_subject_level_outputs(self):
        """ Return the names of the files the subject level analysis is supposed to generate. """

        templates = [join(
            self.directories.output_dir,
            'subject_level', '_subject_id_{subject_id}', f'con_{contrast_id}.nii')\
            for contrast_id in self.contrast_list]
        templates += [join(
            self.directories.output_dir,
            'subject_level', '_subject_id_{subject_id}', 'SPM.mat')]

        # Format with subject_ids
        return_list = []
        for template in templates:
            return_list += [template.format(subject_id = s) for s in self.subject_list]

        return return_list

    def get_group_level_contrasts(subject_level_contrast: str):
        """ Return a contrast list for EstimateContrast

        Parameters :
        - subject_level_contrast: str, id of the subject level contrast :
            either 'effect_of_gain'
            or 'effect_of_loss'

        Returns :
        - list of contrasts for the EstimateContrast interface.
        """
        if subject_level_contrast == 'effect_of_gain':
            return [
                ['gain_param_range', 'T', ['equalIndifference', 'equalRange'], [0, 1]],
                ['gain_param_indiff', 'T', ['equalIndifference', 'equalRange'], [1, 0]]
            ]

        if subject_level_contrast == 'effect_of_loss':
            range_con = ['loss_param_range', 'T', ['equalIndifference', 'equalRange'], [0, 1]]
            indiff_con = ['loss_param_indiff', 'T', ['equalIndifference', 'equalRange'], [1, 0]]
            return [
                range_con,
                indiff_con,
                ['loss_param_range_f', 'F', [range_con]],
                ['loss_param_indiff_f', 'F', [indiff_con]]
            ]

    def get_group_covariates(subjects: list):
        """ Return a covariates list for OneSampleTTestDesign

        Parameters :
        - subjects: list, list of the subjects involved in the design

        Returns :
        - list of covariates for the OneSampleTTestDesign interface.
        """
        from narps_open.data.participants import get_group

        # Sort the subject list to match with the collected contrast file list that
        # is going to be sorted as well
        sorted_subjects = subjects
        sorted_subjects.sort()

        return [
            dict(
                vector = [1.0 if s in get_group('equalRange')\
                              else 0.0 for s in sorted_subjects],
                name = 'equalRange'),
            dict(
                vector = [1.0 if s in get_group('equalIndifference')\
                              else 0.0 for s in sorted_subjects],
                name = 'equalIndifference')
        ]

    def get_group_level_analysis(self):
        """
        Return all workflows for the group level analysis.

        Returns;
            - a list of nipype.WorkFlow
        """
        return [
            self.get_group_level_analysis_single_group(),
            self.get_group_level_analysis_group_comparison()
            ]

    def get_group_level_analysis_single_group(self):
        """
        Return a workflow for the group level analysis.

        Returns:
            - group_level: nipype.WorkFlow
        """
        # Compute the number of participants used to do the analysis
        nb_subjects = len(self.subject_list)

        # Create the group level workflow
        group_level = Workflow(
            base_dir = self.directories.working_dir,
            name = f'group_level_analysis_nsub_{nb_subjects}')

        # IDENTITY INTERFACE - Iterate over the list of subject-level contrasts
        info_source = Node(IdentityInterface(fields=['contrast_id', 'contrast_name']),
                          name = 'info_source')
        info_source.iterables = [
            ('contrast_id', self.contrast_list),
            ('contrast_name', [c[0] for c in self.subject_level_contrasts])
            ]
        info_source.synchronize = True

        # SELECT FILES - Get files from subject-level analysis
        templates = {
            'contrasts': join(self.directories.output_dir,
                'subject_level', '_subject_id_*', 'con_{contrast_id}.nii')
            }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.sort_filelist = True
        select_files.inputs.base_directory = self.directories.dataset_dir
        group_level.connect(info_source, 'contrast_id', select_files, 'contrast_id')

        # Create a function to complete the subject ids out from the get_equal_*_subjects nodes
        #   If not complete, subject id '001' in search patterns
        #   would match all contrast files with 'con_0001.nii'.
        complete_subject_ids = lambda l : [f'_subject_id_{a}' for a in l]

        # GET CONTRAST FILES
        # Function Node elements_in_string
        #   Get contrast files for required subjects
        # Note : using a MapNode with elements_in_string requires using clean_list to remove
        #   None values from the out_list
        get_contrast_files = MapNode(Function(
            function = elements_in_string,
            input_names = ['input_str', 'elements'],
            output_names = ['out_list']
            ),
            name = 'get_contrast_files', iterfield = 'input_str'
        )
        get_contrast_files.inputs.elements = complete_subject_ids(self.subject_list)
        group_level.connect(select_files, 'contrasts', get_contrast_files, 'input_str')

        # GET COVARIATES
        # Function Node get_group_covariates
        #   Get groups as covariates input for OneSampleTTestDesign
        get_covariates = Node(Function(
            function = self.get_group_covariates,
            input_names = ['subjects'],
            output_names = ['covariates']
            ),
            name = 'get_covariates'
        )
        get_covariates.inputs.subjects = self.subject_list

        # ONE SAMPLE T-TEST DESIGN - Create a t test design for hypothesis testing inside a group
        one_sample_t_test = Node(OneSampleTTestDesign(), name = 'one_sample_t_test')
        group_level.connect(get_covariates, 'covariates', one_sample_t_test, 'covariates')
        group_level.connect(
            get_contrast_files, ('out_list', clean_list), one_sample_t_test, 'in_files')

        # ESTIMATE MODEL - estimate the parameters of the model
        # Even for second level it should be 'Classical': 1.
        model_estimate = Node(EstimateModel(), name = 'model_estimate')
        model_estimate.inputs.estimation_method = {'Classical': 1}
        group_level.connect(one_sample_t_test, 'spm_mat_file', model_estimate, 'spm_mat_file')

        # Function Node get_group_level_contrasts
        #   Get a contrast list for EstimateContrast
        get_contrasts = Node(Function(
            function = self.get_group_level_contrasts,
            input_names = ['subject_level_contrast'],
            output_names = ['contrasts']
            ),
            name = 'get_contrasts'
        )
        group_level.connect(info_source, 'contrast_name', get_contrasts, 'subject_level_contrast')

        # ESTIMATE CONTRASTS - estimates simple group contrast
        contrast_estimate = Node(EstimateContrast(), name = 'contrast_estimate')
        contrast_estimate.inputs.group_contrast = True
        group_level.connect(get_contrasts, 'contrasts', contrast_estimate, 'contrasts')
        group_level.connect(model_estimate, 'spm_mat_file', contrast_estimate, 'spm_mat_file')
        group_level.connect(model_estimate, 'beta_images', contrast_estimate, 'beta_images')
        group_level.connect(model_estimate, 'residual_image', contrast_estimate, 'residual_image')

        # THRESHOLD - Create thresholded maps
        threshold = MapNode(Threshold(), name = 'threshold',
            iterfield = ['stat_image', 'contrast_index'])
        threshold.inputs.use_fwe_correction = True
        threshold.inputs.height_threshold_type = 'p-value'
        threshold.inputs.force_activation = False
        threshold.inputs.height_threshold = 0.05
        threshold.inputs.contrast_index = [1, 2]
        group_level.connect(contrast_estimate, 'spm_mat_file', threshold, 'spm_mat_file')
        group_level.connect(contrast_estimate, 'spmT_images', threshold, 'stat_image')

        # Datasink - save important files
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        group_level.connect([
            (contrast_estimate, data_sink, [
                ('spm_mat_file', f'{group_level.name}.@spm_mat'),
                ('spmT_images', f'{group_level.name}.@T'),
                ('con_images', f'{group_level.name}.@con')]),
            (threshold, data_sink, [
                ('thresholded_map', f'{group_level.name}.@thresh')])
            ])

        return group_level

    def get_group_level_analysis_group_comparison(self):
        """
        Return a workflow for the group level analysis in the group comparison case.

        Returns:
            - group_level_analysis: nipype.WorkFlow
        """
        # Compute the number of participants used to do the analysis
        nb_subjects = len(self.subject_list)

        # Create the group level workflow
        group_level_analysis = Workflow(
            base_dir = self.directories.working_dir,
            name = f'group_level_analysis_groupComp_nsub_{nb_subjects}')

        # SELEC FILES - Get files from subject level analysis (effect_of_loss contrast only)
        templates = {
            'contrasts': join(self.directories.output_dir,
                'subject_level', '_subject_id_*', 'con_0002.nii')
            }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.sort_filelist = True
        select_files.inputs.base_directory = self.directories.dataset_dir

        # GET SUBJECT LIST IN EACH GROUP
        # Function Node get_group_subjects
        #   Get subjects in the group and in the subject_list
        get_equal_indifference_subjects = Node(Function(
            function = list_intersection,
            input_names = ['list_1', 'list_2'],
            output_names = ['out_list']
            ),
            name = 'get_equal_indifference_subjects'
        )
        get_equal_indifference_subjects.inputs.list_1 = get_group('equalIndifference')
        get_equal_indifference_subjects.inputs.list_2 = self.subject_list

        # Function Node get_group_subjects
        #   Get subjects in the group and in the subject_list
        get_equal_range_subjects = Node(Function(
            function = list_intersection,
            input_names = ['list_1', 'list_2'],
            output_names = ['out_list']
            ),
            name = 'get_equal_range_subjects'
        )
        get_equal_range_subjects.inputs.list_1 = get_group('equalRange')
        get_equal_range_subjects.inputs.list_2 = self.subject_list

        # Create a function to complete the subject ids out from the get_equal_*_subjects nodes
        #   If not complete, subject id '001' in search patterns
        #   would match all contrast files with 'con_0001.nii'.
        complete_subject_ids = lambda l : [f'_subject_id_{a}' for a in l]

        # GET CONTRAST FILES
        # Function Node elements_in_string
        #   Get contrast files for required subjects
        # Note : using a MapNode with elements_in_string requires using clean_list to remove
        #   None values from the out_list
        get_equal_indifference_contrasts = MapNode(Function(
            function = elements_in_string,
            input_names = ['input_str', 'elements'],
            output_names = ['out_list']
            ),
            name = 'get_equal_indifference_contrasts', iterfield = 'input_str'
        )
        group_level_analysis.connect(
            select_files, 'contrasts', get_equal_indifference_contrasts, 'input_str')
        group_level_analysis.connect(
            get_equal_indifference_subjects, ('out_list', complete_subject_ids),
            get_equal_indifference_contrasts, 'elements')

        get_equal_range_contrasts = MapNode(Function(
            function = elements_in_string,
            input_names = ['input_str', 'elements'],
            output_names = ['out_list']
            ),
            name = 'get_equal_range_contrasts', iterfield = 'input_str'
        )
        group_level_analysis.connect(
            select_files, 'contrasts', get_equal_range_contrasts, 'input_str')
        group_level_analysis.connect(
            get_equal_range_subjects, ('out_list', complete_subject_ids),
            get_equal_range_contrasts, 'elements')

        # TWO SAMPLE T-TEST DESIGN - Create a t test design for group comparison
        two_sample_t_test = Node(TwoSampleTTestDesign(), name = 'two_sample_t_test')
        group_level_analysis.connect(
            get_equal_range_contrasts, ('out_list', clean_list),
            two_sample_t_test, 'group1_files')
        group_level_analysis.connect(
            get_equal_indifference_contrasts, ('out_list', clean_list),
            two_sample_t_test, 'group2_files')

        # ESTIMATE MODEL - Estimate the parameters of the model
        # Even for second level it should be 'Classical': 1.
        model_estimate = Node(EstimateModel(), name = 'model_estimate')
        model_estimate.inputs.estimation_method = {'Classical': 1}
        group_level_analysis.connect(
            two_sample_t_test, 'spm_mat_file', model_estimate, 'spm_mat_file')

        # ESTIMATE CONTRASTS - Estimates contrasts
        contrast_estimate = Node(EstimateContrast(), name = 'contrast_estimate')
        contrast_estimate.inputs.group_contrast = True
        contrast_estimate.inputs.contrasts = [
            ['Eq range vs Eq indiff in loss', 'T', ['Group_{1}', 'Group_{2}'], [1, -1]]
        ]
        group_level_analysis.connect([
            (model_estimate, contrast_estimate, [
                ('spm_mat_file', 'spm_mat_file'),
                ('beta_images', 'beta_images'),
                ('residual_image', 'residual_image')
                ])])

        # THRESHOLD - Create thresholded maps
        threshold = Node(Threshold(), name = 'threshold')
        threshold.inputs.use_fwe_correction = True
        threshold.inputs.height_threshold_type = 'p-value'
        threshold.inputs.force_activation = False
        threshold.inputs.height_threshold = 0.05
        threshold.inputs.contrast_index = 1
        group_level_analysis.connect([
            (contrast_estimate, threshold, [
                ('spm_mat_file', 'spm_mat_file'),
                ('spmT_images', 'stat_image')
                ])])

        # DATA SINK - save important files
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        group_level_analysis.connect([
            (contrast_estimate, data_sink, [
                ('spm_mat_file', f'{group_level_analysis.name}.@spm_mat'),
                ('spmT_images', f'{group_level_analysis.name}.@T'),
                ('con_images', f'{group_level_analysis.name}.@con')]),
            (threshold, data_sink, [
                ('thresholded_map', f'{group_level_analysis.name}.@thresh')])
            ])

        return group_level_analysis

    def get_group_level_outputs(self):
        """ Return all names for the files the group level analysis is supposed to generate. """

        # Handle equalRange and equalIndifference
        parameters = {
            'contrast_dir': [
                f'_contrast_id_{i}_contrast_name_{n[0]}' \
                for i,n in zip(self.contrast_list, self.subject_level_contrasts)
                ],
            'file': [
                'con_0001.nii', 'con_0002.nii', 'SPM.mat',
                'spmT_0001.nii', 'spmT_0002.nii',
                join('_threshold0', 'spmT_0001_thr.nii'), join('_threshold1', 'spmT_0002_thr.nii')
                ],
            'nb_subjects' : [str(len(self.subject_list))]
        }

        parameter_sets = product(*parameters.values())
        template = join(
            self.directories.output_dir,
            'group_level_analysis_nsub_{nb_subjects}',
            '{contrast_dir}',
            '{file}'
            )
        return_list = [template.format(**dict(zip(parameters.keys(), parameter_values)))\
            for parameter_values in parameter_sets]

        # Handle groupComp
        parameters = {
            'contrast_id': self.contrast_list,
            'method': ['groupComp'],
            'file': [
                'con_0001.nii', 'SPM.mat', 'spmT_0001.nii', 'spmT_0001_thr.nii'
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
                '_contrast_id_0001', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0001', 'spmT_0001.nii'),
            # Hypothesis 2
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0001', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0001', 'spmT_0001.nii'),
            # Hypothesis 3
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0001', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0001', 'spmT_0001.nii'),
            # Hypothesis 4
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0001', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0001', 'spmT_0001.nii'),
            # Hypothesis 5
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold1', 'spmT_0002_thr.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0002.nii'),
            # Hypothesis 6
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold1', 'spmT_0002_thr.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0002.nii'),
            # Hypothesis 7
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0001.nii'),
            # Hypothesis 8
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0001.nii'),
            # Hypothesis 9
            join(f'group_level_analysis_groupComp_nsub_{nb_sub}',
                '_contrast_id_0002', '_threshold0', 'spmT_0001_thr.nii'),
            join(f'group_level_analysis_groupComp_nsub_{nb_sub}',
                '_contrast_id_0002', 'spmT_0001.nii')
        ]
        return [join(self.directories.output_dir, f) for f in files]
