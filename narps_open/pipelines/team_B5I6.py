#!/usr/bin/python
# coding: utf-8

""" Write the work of NARPS team B5I6 using Nipype """

from os.path import join
from itertools import product

from nipype import Workflow, Node, MapNode
from nipype.interfaces.utility import IdentityInterface, Function, Split
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.interfaces.fsl import (
    IsotropicSmooth, Level1Design, FEATModel,
    L2Model, Merge, FLAMEO, FILMGLS, MultipleRegressDesign,
    FSLCommand, Randomise
    )
from nipype.algorithms.modelgen import SpecifyModel
from nipype.interfaces.fsl.maths import MathsCommand

from narps_open.utils.configuration import Configuration
from narps_open.pipelines import Pipeline
from narps_open.data.task import TaskInformation
from narps_open.data.participants import get_group
from narps_open.core.common import list_intersection, elements_in_string, clean_list
from narps_open.core.interfaces import InterfaceFactory

# Setup FSL
FSLCommand.set_default_output_type('NIFTI_GZ')

class PipelineTeamB5I6(Pipeline):
    """ A class that defines the pipeline of team B5I6 """

    def __init__(self):
        super().__init__()
        self.fwhm = 5.0
        self.team_id = 'B5I6'
        self.contrast_list = ['1', '2', '3', '4', '5', '6']
        self.run_level_contrasts = [
            ('positive_main_effect_of_decision', 'T', ['trial', 'gain', 'loss'], [1, 0, 0]),
            ('negative_main_effect_of_decision', 'T', ['trial', 'gain', 'loss'], [-1, 0, 0]),
            ('positive_parametric_effect_of_gain', 'T', ['trial', 'gain', 'loss'], [0, 1, 0]),
            ('negative_parametric_effect_of_gain', 'T', ['trial', 'gain', 'loss'], [0, -1, 0]),
            ('positive_parametric_effect_of_loss', 'T', ['trial', 'gain', 'loss'], [0, 0, 1]),
            ('negative_parametric_effect_of_loss', 'T', ['trial', 'gain', 'loss'], [0, 0, -1])
            ]

    def get_preprocessing(self):
        """ No preprocessing has been done by team B5I6 """
        return None

    def get_subject_information(event_file):
        """
        Create Bunchs for specifyModel.

        Parameters :
        - event_file : str, file corresponding to the run and the subject to analyze

        Returns :
        - subject_info : list of Bunch for 1st level analysis.
        """
        from numpy import mean
        from nipype.interfaces.base import Bunch

        onsets_trial = []
        onsets_missed = []
        durations_trial = []
        durations_missed = []
        amplitudes_trial = []
        amplitudes_missed = []
        amplitudes_gain = []
        amplitudes_loss = []

        with open(event_file, 'rt') as file:
            next(file)  # skip the header

            for line in file:
                info = line.strip().split()

                if 'NoResp' in info[5]:
                    onsets_missed.append(float(info[0]))
                    durations_missed.append(float(info[1]))
                    amplitudes_missed.append(1.0)
                else:
                    onsets_trial.append(float(info[0]))
                    durations_trial.append(float(info[1]))
                    amplitudes_trial.append(1.0)
                    amplitudes_gain.append(float(info[2]))
                    amplitudes_loss.append(float(info[3]))

        # Mean center magnitudes
        amplitudes_gain = amplitudes_gain - mean(amplitudes_gain)
        amplitudes_loss = amplitudes_loss - mean(amplitudes_loss)

        # Add missed trials if any
        conditions = ['trial', 'gain', 'loss']
        onsets = [onsets_trial, onsets_trial, onsets_trial]
        durations = [durations_trial, durations_trial, durations_trial]
        amplitudes = [amplitudes_trial, amplitudes_gain, amplitudes_loss]
        if onsets_missed:
            conditions.append('missed')
            onsets.append(onsets_missed)
            durations.append(durations_missed)
            amplitudes.append(amplitudes_missed)

        return [
            Bunch(
                conditions = conditions,
                onsets = onsets,
                durations = durations,
                amplitudes = amplitudes
                )
            ]

    def get_confounds_file(filepath, subject_id, run_id):
        """
        Create a tsv file with only desired confounds per subject per run.

        Parameters :
        - filepath : path to the subject confounds file (i.e. one per run)
        - subject_id : subject for whom the 1st level analysis is made
        - run_id: run for which the 1st level analysis is made

        Return :
        - confounds_file : paths to new files containing only desired confounds.
        """
        from os.path import abspath

        from pandas import read_csv, DataFrame
        from numpy import array, transpose, insert, diff, square, nanpercentile, c_

        data_frame = read_csv(filepath, sep = '\t', header=0)
        motion_regressors = array([
            # Motion regressors
            data_frame['X'], data_frame['Y'], data_frame['Z'],
            data_frame['RotX'], data_frame['RotY'], data_frame['RotZ'],
            # Derivatives
            insert(diff(data_frame['X']), 0, 0),
            insert(diff(data_frame['Y']), 0, 0),
            insert(diff(data_frame['Z']), 0, 0),
            insert(diff(data_frame['RotX']), 0, 0),
            insert(diff(data_frame['RotY']), 0, 0),
            insert(diff(data_frame['RotZ']), 0, 0),
            # Squared motion regressors
            square(data_frame['X']), square(data_frame['Y']), square(data_frame['Z']),
            square(data_frame['RotX']), square(data_frame['RotY']), square(data_frame['RotZ']),
            # Squared derivatives
            insert(square(diff(data_frame['X'])), 0, 0),
            insert(square(diff(data_frame['Y'])), 0, 0),
            insert(square(diff(data_frame['Z'])), 0, 0),
            insert(square(diff(data_frame['RotX'])), 0, 0),
            insert(square(diff(data_frame['RotY'])), 0, 0),
            insert(square(diff(data_frame['RotZ'])), 0, 0),
        ])

        # Compute outliers of `non-stdDVARS`
        dvars_outliers = array(data_frame['non-stdDVARS'])
        percentile_75 = nanpercentile(dvars_outliers, 75)
        interquartile_range = percentile_75 - nanpercentile(dvars_outliers, 25)
        dvars_outliers = (dvars_outliers > (percentile_75 + 1.5 * interquartile_range)).astype(int)

        # Compute outliers of `FramewiseDisplacement`
        fd_outliers = array(data_frame['FramewiseDisplacement'])
        percentile_75 = nanpercentile(fd_outliers, 75)
        interquartile_range = percentile_75 - nanpercentile(fd_outliers, 25)
        fd_outliers = (fd_outliers > (percentile_75 + 1.5 * interquartile_range)).astype(int)

        # Build an outlier regressor
        outlier_regressor = fd_outliers | dvars_outliers

        # Add the regressor if any outliers in the run
        if outlier_regressor.any():
            retained_confounds = DataFrame(c_[transpose(motion_regressors), outlier_regressor])
        else :
            retained_confounds = DataFrame(transpose(motion_regressors))

        # Write confounds to a file
        confounds_file = abspath(f'confounds_file_sub-{subject_id}_run-{run_id}.tsv')
        with open(confounds_file, 'w', encoding = 'utf-8') as writer:
            writer.write(retained_confounds.to_csv(
                sep = '\t', index = False, header = False, na_rep = '0.0'))

        return confounds_file

    def get_run_level_analysis(self):
        """
        Create the run level analysis workflow.

        Returns:
            - run_level : nipype.WorkFlow
        """
        # Create run level analysis workflow and connect its nodes
        run_level = Workflow(
            base_dir = self.directories.working_dir,
            name = 'run_level_analysis'
            )

        # IdentityInterface Node - Iterate on subject and runs
        information_source = Node(IdentityInterface(
            fields = ['subject_id', 'run_id']),
            name = 'information_source')
        information_source.iterables = [
            ('subject_id', self.subject_list),
            ('run_id', self.run_list)
            ]

        # SelectFiles - Get necessary files
        templates = {
            'func' : join('derivatives', 'fmriprep', 'sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-{run_id}_bold_space-MNI152NLin2009cAsym_preproc.nii.gz'),
            'events' : join('sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-{run_id}_events.tsv'),
            'confounds' : join('derivatives', 'fmriprep', 'sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-{run_id}_bold_confounds.tsv')
        }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.dataset_dir
        run_level.connect(information_source, 'subject_id', select_files, 'subject_id')
        run_level.connect(information_source, 'run_id', select_files, 'run_id')

        # IsotropicSmooth Node - Smoothing data
        smoothing_func = Node(IsotropicSmooth(), name = 'smoothing_func')
        smoothing_func.inputs.fwhm = self.fwhm
        run_level.connect(select_files, 'func', smoothing_func, 'in_file')

        # Get Subject Info - get subject specific condition information
        subject_information = Node(Function(
            function = self.get_subject_information,
            input_names = ['event_file'],
            output_names = ['subject_info']
            ), name = 'subject_information')
        run_level.connect(select_files, 'events', subject_information, 'event_file')

        # Function Node get_confounds_file - Get files with movement confounds
        confounds = Node(Function(
            function = self.get_confounds_file,
            input_names = ['filepath', 'subject_id', 'run_id'],
            output_names = ['confounds_file']),
             name = 'confounds')
        run_level.connect(information_source, 'subject_id', confounds, 'subject_id')
        run_level.connect(information_source, 'run_id', confounds, 'run_id')
        run_level.connect(select_files, 'confounds', confounds, 'filepath')

        # SpecifyModel Node - Generate run level model
        specify_model = Node(SpecifyModel(), name = 'specify_model')
        specify_model.inputs.high_pass_filter_cutoff = 100
        specify_model.inputs.input_units = 'secs'
        specify_model.inputs.time_repetition = TaskInformation()['RepetitionTime']
        run_level.connect(confounds, 'confounds_file', specify_model, 'realignment_parameters')
        run_level.connect(smoothing_func, 'out_file', specify_model, 'functional_runs')
        run_level.connect(subject_information, 'subject_info', specify_model, 'subject_info')

        # Level1Design Node - Generate files for run level computation
        model_design = Node(Level1Design(), name = 'model_design')
        model_design.inputs.bases = {'dgamma' : {'derivs' : False }}
        model_design.inputs.interscan_interval = TaskInformation()['RepetitionTime']
        model_design.inputs.model_serial_correlations = True
        model_design.inputs.contrasts = self.run_level_contrasts
        run_level.connect(specify_model, 'session_info', model_design, 'session_info')

        # FEATModel Node - Generate run level model
        model_generation = Node(FEATModel(), name = 'model_generation')
        run_level.connect(model_design, 'ev_files', model_generation, 'ev_files')
        run_level.connect(model_design, 'fsf_files', model_generation, 'fsf_file')

        # FILMGLS Node - Estimate first level model
        model_estimate = Node(FILMGLS(), name='model_estimate')
        run_level.connect(smoothing_func, 'out_file', model_estimate, 'in_file')
        run_level.connect(model_generation, 'con_file', model_estimate, 'tcon_file')
        run_level.connect(model_generation, 'design_file', model_estimate, 'design_file')

        # DataSink Node - store the wanted results in the wanted directory
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        run_level.connect(model_estimate, 'results_dir', data_sink, 'run_level_analysis.@results')
        run_level.connect(
            model_generation, 'design_file', data_sink, 'run_level_analysis.@design_file')
        run_level.connect(
            model_generation, 'design_image', data_sink, 'run_level_analysis.@design_img')

        # Remove large files, if requested
        if Configuration()['pipelines']['remove_unused_data']:
            remove_smooth = Node(
                InterfaceFactory.create('remove_parent_directory'),
                name = 'remove_smooth')
            run_level.connect(data_sink, 'out_file', remove_smooth, '_')
            run_level.connect(smoothing_func, 'out_file', remove_smooth, 'file_name')

        return run_level

    def get_run_level_outputs(self):
        """ Return the names of the files the run level analysis is supposed to generate. """

        parameters = {
            'run_id' : self.run_list,
            'subject_id' : self.subject_list,
            'contrast_id' : self.contrast_list,
        }
        parameter_sets = product(*parameters.values())
        output_dir = join(self.directories.output_dir,
            'run_level_analysis', '_run_id_{run_id}_subject_id_{subject_id}')
        templates = [
                join(output_dir, 'results', 'cope{contrast_id}.nii.gz'),
                join(output_dir, 'results', 'tstat{contrast_id}.nii.gz'),
                join(output_dir, 'results', 'varcope{contrast_id}.nii.gz'),
                join(output_dir, 'results', 'zstat{contrast_id}.nii.gz')
            ]
        return [template.format(**dict(zip(parameters.keys(), parameter_values)))\
            for parameter_values in parameter_sets for template in templates]

    def get_subject_level_analysis(self):
        """
        Create the subject level analysis workflow.

        Returns:
        - subject_level_analysis : nipype.WorkFlow
        """
        # Second level (single-subject, mean of all four scans) analysis workflow.
        subject_level = Workflow(
            base_dir = self.directories.working_dir,
            name = 'subject_level_analysis')

        # Infosource Node - To iterate on subject and runs
        information_source = Node(IdentityInterface(
            fields = ['subject_id', 'contrast_id']),
            name = 'information_source')
        information_source.iterables = [
            ('subject_id', self.subject_list),
            ('contrast_id', self.contrast_list)
            ]

        # SelectFiles node - to select necessary files
        templates = {
            'cope' : join(self.directories.output_dir,
                'run_level_analysis', '_run_id_*_subject_id_{subject_id}', 'results',
                'cope{contrast_id}.nii.gz'),
            'varcope' : join(self.directories.output_dir,
                'run_level_analysis', '_run_id_*_subject_id_{subject_id}', 'results',
                'varcope{contrast_id}.nii.gz'),
            'masks' : join('derivatives', 'fmriprep', 'sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-*_bold_space-MNI152NLin2009cAsym_brainmask.nii.gz')
        }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory= self.directories.results_dir
        subject_level.connect(information_source, 'subject_id', select_files, 'subject_id')
        subject_level.connect(information_source, 'contrast_id', select_files, 'contrast_id')

        # Merge Node - Merge copes files for each subject
        merge_copes = Node(Merge(), name = 'merge_copes')
        merge_copes.inputs.dimension = 't'
        subject_level.connect(select_files, 'cope', merge_copes, 'in_files')

        # Merge Node - Merge varcopes files for each subject
        merge_varcopes = Node(Merge(), name = 'merge_varcopes')
        merge_varcopes.inputs.dimension = 't'
        subject_level.connect(select_files, 'varcope', merge_varcopes, 'in_files')

        # Merge Node - Merge masks files for each subject
        merge_masks = Node(Merge(), name = 'merge_masks')
        merge_masks.inputs.dimension = 't'
        subject_level.connect(select_files, 'masks', merge_masks, 'in_files')

        # MathsCommand Node - Create a subject mask by
        #   computing the intersection of all run masks.
        mask_intersection = Node(MathsCommand(), name = 'mask_intersection')
        mask_intersection.inputs.args = '-Tmin -thr 0.9'
        subject_level.connect(merge_masks, 'merged_file', mask_intersection, 'in_file')

        # L2Model Node - Generate subject specific second level model
        generate_model = Node(L2Model(), name = 'generate_model')
        generate_model.inputs.num_copes = len(self.run_list)

        # FLAMEO Node - Estimate model
        estimate_model = Node(FLAMEO(), name = 'estimate_model')
        estimate_model.inputs.run_mode = 'flame1'
        subject_level.connect(mask_intersection, 'out_file', estimate_model,  'mask_file')
        subject_level.connect(merge_copes, 'merged_file', estimate_model, 'cope_file')
        subject_level.connect(merge_varcopes, 'merged_file', estimate_model, 'var_cope_file')
        subject_level.connect(generate_model, 'design_mat', estimate_model, 'design_file')
        subject_level.connect(generate_model, 'design_con', estimate_model, 't_con_file')
        subject_level.connect(generate_model, 'design_grp', estimate_model, 'cov_split_file')

        # DataSink Node - store the wanted results in the wanted directory
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        subject_level.connect(estimate_model, 'zstats', data_sink, 'subject_level_analysis.@stats')
        subject_level.connect(
            estimate_model, 'tstats', data_sink, 'subject_level_analysis.@tstats')
        subject_level.connect(estimate_model, 'copes', data_sink, 'subject_level_analysis.@copes')
        subject_level.connect(
            estimate_model, 'var_copes', data_sink, 'subject_level_analysis.@varcopes')

        return subject_level

    def get_subject_level_outputs(self):
        """ Return the names of the files the subject level analysis is supposed to generate. """

        parameters = {
            'contrast_id' : self.contrast_list,
            'subject_id' : self.subject_list,
            'file' : ['cope1.nii.gz', 'tstat1.nii.gz', 'varcope1.nii.gz', 'zstat1.nii.gz']
        }
        parameter_sets = product(*parameters.values())
        template = join(
            self.directories.output_dir,
            'subject_level_analysis', '_contrast_id_{contrast_id}_subject_id_{subject_id}','{file}'
            )
        return_list = [template.format(**dict(zip(parameters.keys(), parameter_values)))\
            for parameter_values in parameter_sets]

        return return_list

    def get_one_sample_t_test_regressors(subject_list: list) -> dict:
        """
        Create dictionary of regressors for one sample t-test group analysis.

        Parameters:
            - subject_list: ids of subject in the group for which to do the analysis

        Returns:
            - dict containing named lists of regressors.
        """

        return dict(group_mean = [1 for _ in subject_list])

    def get_two_sample_t_test_regressors(
        equal_range_ids: list,
        equal_indifference_ids: list,
        subject_list: list,
        ) -> dict:
        """
        Create dictionary of regressors for two sample t-test group analysis.

        Parameters:
            - equal_range_ids: ids of subjects in equal range group
            - equal_indifference_ids: ids of subjects in equal indifference group
            - subject_list: ids of subject for which to do the analysis

        Returns:
            - regressors, dict: containing named lists of regressors.
            - groups, list: group identifiers to distinguish groups in FSL analysis.
        """

        # Create 2 lists containing n_sub values which are
        #  * 1 if the participant is on the group
        #  * 0 otherwise
        equal_range_regressors = [1 if i in equal_range_ids else 0 for i in subject_list]
        equal_indifference_regressors = [
            1 if i in equal_indifference_ids else 0 for i in subject_list
            ]

        # Create regressors output : a dict with the two list
        regressors = dict(
            equalRange = equal_range_regressors,
            equalIndifference = equal_indifference_regressors
        )

        # Create groups outputs : a list with 1 for equalRange subjects and 2 for equalIndifference
        groups = [1 if i == 1 else 2 for i in equal_range_regressors]

        return regressors, groups

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
            - group_level: nipype.WorkFlow
        """
        # Compute the number of participants used to do the analysis
        nb_subjects = len(self.subject_list)

        # Declare the workflow
        group_level = Workflow(
            base_dir = self.directories.working_dir,
            name = f'group_level_analysis_{method}_nsub_{nb_subjects}')

        # Infosource Node - iterate over the contrasts generated by the subject level analysis
        information_source = Node(IdentityInterface(
            fields = ['contrast_id']),
            name = 'information_source')
        information_source.iterables = [('contrast_id', self.contrast_list)]

        # SelectFiles Node - select necessary files
        templates = {
            'cope' : join(self.directories.output_dir,
                'subject_level_analysis', '_contrast_id_{contrast_id}_subject_id_*',
                'cope1.nii.gz'),
            'varcope' : join(self.directories.output_dir,
                'subject_level_analysis', '_contrast_id_{contrast_id}_subject_id_*',
                'varcope1.nii.gz'),
            'masks' : join('derivatives', 'fmriprep', 'sub-*', 'func',
                'sub-*_task-MGT_run-*_bold_space-MNI152NLin2009cAsym_brainmask.nii.gz')
            }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.results_dir
        group_level.connect(information_source, 'contrast_id', select_files, 'contrast_id')

        # Function Node elements_in_string
        #   Get contrast of parameter estimates (cope) for these subjects
        # Note : using a MapNode with elements_in_string requires using clean_list to remove
        #   None values from the out_list
        get_copes = MapNode(Function(
            function = elements_in_string,
            input_names = ['input_str', 'elements'],
            output_names = ['out_list']
            ),
            name = 'get_copes', iterfield = 'input_str'
        )
        group_level.connect(select_files, 'cope', get_copes, 'input_str')

        # Function Node elements_in_string
        #   Get variance of the estimated copes (varcope) for these subjects
        # Note : using a MapNode with elements_in_string requires using clean_list to remove
        #   None values from the out_list
        get_varcopes = MapNode(Function(
            function = elements_in_string,
            input_names = ['input_str', 'elements'],
            output_names = ['out_list']
            ),
            name = 'get_varcopes', iterfield = 'input_str'
        )
        group_level.connect(select_files, 'varcope', get_varcopes, 'input_str')

        # Function Node elements_in_string
        #   Get masks for these subjects
        # Note : using a MapNode with elements_in_string requires using clean_list to remove
        #   None values from the out_list
        get_masks = MapNode(Function(
            function = elements_in_string,
            input_names = ['input_str', 'elements'],
            output_names = ['out_list']
            ),
            name = 'get_masks', iterfield = 'input_str'
        )
        group_level.connect(select_files, 'masks', get_masks, 'input_str')

        # Merge Node - Merge cope files
        merge_copes = Node(Merge(), name = 'merge_copes')
        merge_copes.inputs.dimension = 't'
        group_level.connect(get_copes, ('out_list', clean_list), merge_copes, 'in_files')

        # Merge Node - Merge cope files
        merge_varcopes = Node(Merge(), name = 'merge_varcopes')
        merge_varcopes.inputs.dimension = 't'
        group_level.connect(get_varcopes, ('out_list', clean_list), merge_varcopes, 'in_files')

        # Merge Node - Merge mask files
        merge_masks = Node(Merge(), name = 'merge_masks')
        merge_masks.inputs.dimension = 't'
        group_level.connect(get_masks, ('out_list', clean_list), merge_masks, 'in_files')

        # MathsCommand Node - Create a subject mask by
        #   computing the intersection of all run masks
        #   (all voxels included in at least 80% of masks across all runs).
        mask_intersection = Node(MathsCommand(), name = 'mask_intersection')
        mask_intersection.inputs.args = '-Tmin -thr 0.9'
        group_level.connect(merge_masks, 'merged_file', mask_intersection, 'in_file')

        # MultipleRegressDesign Node - Specify model
        specify_model = Node(MultipleRegressDesign(), name = 'specify_model')

        # FLAMEO Node - Estimate model
        estimate_model = Node(FLAMEO(), name = 'estimate_model')
        estimate_model.inputs.run_mode = 'flame1'
        group_level.connect(mask_intersection, 'out_file', estimate_model, 'mask_file')
        group_level.connect(merge_copes, 'merged_file', estimate_model, 'cope_file')
        group_level.connect(merge_varcopes, 'merged_file', estimate_model, 'var_cope_file')
        group_level.connect(specify_model, 'design_mat', estimate_model, 'design_file')
        group_level.connect(specify_model, 'design_con', estimate_model, 't_con_file')
        group_level.connect(specify_model, 'design_grp', estimate_model, 'cov_split_file')

        # Randomise Node - Perform clustering on statistical output
        randomise = MapNode(Randomise(),
            name = 'randomise',
            iterfield = ['in_file', 'cope_file'],
            synchronize = True)
        randomise.inputs.tfce = True
        randomise.inputs.num_perm = 10000
        randomise.inputs.c_thresh = 0.05
        group_level.connect(mask_intersection, 'out_file', randomise, 'mask')
        group_level.connect(merge_copes, 'merged_file', randomise, 'in_file')
        group_level.connect(specify_model, 'design_con', randomise, 'tcon')
        group_level.connect(specify_model, 'design_mat', randomise, 'design_mat')

        # Datasink Node - Save important files
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        group_level.connect(estimate_model, 'zstats', data_sink,
            f'group_level_analysis_{method}_nsub_{nb_subjects}.@zstats')
        group_level.connect(estimate_model, 'tstats', data_sink,
            f'group_level_analysis_{method}_nsub_{nb_subjects}.@tstats')
        group_level.connect(randomise,'t_corrected_p_files', data_sink,
            f'group_level_analysis_{method}_nsub_{nb_subjects}.@t_corrected_p_files')
        group_level.connect(randomise,'t_p_files', data_sink,
            f'group_level_analysis_{method}_nsub_{nb_subjects}.@t_p_files')

        if method in ('equalIndifference', 'equalRange'):
            # Setup a one sample t-test
            specify_model.inputs.contrasts = [
                ['group_mean', 'T', ['group_mean'], [1]],
                ['group_mean_neg', 'T', ['group_mean'], [-1]]
                ]

            # Function Node get_group_subjects - Get subjects in the group and in the subject_list
            get_group_subjects = Node(Function(
                function = list_intersection,
                input_names = ['list_1', 'list_2'],
                output_names = ['out_list']
                ),
                name = 'get_group_subjects'
            )
            get_group_subjects.inputs.list_1 = get_group(method)
            get_group_subjects.inputs.list_2 = self.subject_list
            group_level.connect(get_group_subjects, 'out_list', get_copes, 'elements')
            group_level.connect(get_group_subjects, 'out_list', get_varcopes, 'elements')
            group_level.connect(get_group_subjects, 'out_list', get_masks, 'elements')

            # Function Node get_one_sample_t_test_regressors
            #   Get regressors in the equalRange and equalIndifference method case
            regressors_one_sample = Node(
                Function(
                    function = self.get_one_sample_t_test_regressors,
                    input_names = ['subject_list'],
                    output_names = ['regressors']
                ),
                name = 'regressors_one_sample',
            )
            group_level.connect(get_group_subjects, 'out_list', regressors_one_sample, 'subject_list')
            group_level.connect(regressors_one_sample, 'regressors', specify_model, 'regressors')

        elif method == 'groupComp':

            # Select copes and varcopes corresponding to the selected subjects
            #   Indeed the SelectFiles node asks for all (*) subjects available
            get_copes.inputs.elements = self.subject_list
            get_varcopes.inputs.elements = self.subject_list
            get_masks.inputs.elements = self.subject_list

            # Setup a two sample t-test
            specify_model.inputs.contrasts = [
                ['equalRange_sup', 'T', ['equalRange', 'equalIndifference'], [1, -1]]
            ]

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

            # Function Node get_two_sample_t_test_regressors
            #   Get regressors in the groupComp method case
            regressors_two_sample = Node(
                Function(
                    function = self.get_two_sample_t_test_regressors,
                    input_names = [
                        'equal_range_ids',
                        'equal_indifference_ids',
                        'subject_list',
                    ],
                    output_names = ['regressors', 'groups']
                ),
                name = 'regressors_two_sample',
            )
            regressors_two_sample.inputs.subject_list = self.subject_list

            # Add missing connections
            group_level.connect(
                get_equal_range_subjects, 'out_list', regressors_two_sample, 'equal_range_ids')
            group_level.connect(
                get_equal_indifference_subjects, 'out_list',
                regressors_two_sample, 'equal_indifference_ids')
            group_level.connect(regressors_two_sample, 'regressors', specify_model, 'regressors')
            group_level.connect(regressors_two_sample, 'groups', specify_model, 'groups')

        return group_level

    def get_group_level_outputs(self):
        """ Return all names for the files the group level analysis is supposed to generate. """

        # Handle equalRange and equalIndifference
        parameters = {
            'contrast_id': self.contrast_list,
            'method': ['equalRange', 'equalIndifference'],
            'file': [
                'randomise_tfce_corrp_tstat1.nii.gz',
                'randomise_tfce_corrp_tstat2.nii.gz',
                'tstat1.nii.gz',
                'tstat2.nii.gz',
                'zstat1.nii.gz',
                'zstat2.nii.gz'
                ]
        }
        parameter_sets = product(*parameters.values())
        template = join(
            self.directories.output_dir,
            'group_level_analysis_{method}_nsub_'+f'{len(self.subject_list)}',
            '_contrast_id_{contrast_id}',
            '{file}'
            )
        return_list = [template.format(**dict(zip(parameters.keys(), parameter_values)))\
            for parameter_values in parameter_sets]

        # Handle groupComp
        parameters = {
            'contrast_id': self.contrast_list,
            'file': [
                'randomise_tfce_corrp_tstat1.nii.gz',
                'tstat1.nii.gz',
                'zstat1.nii.gz'
                ]
        }
        parameter_sets = product(*parameters.values())
        template = join(
            self.directories.output_dir,
            f'group_level_analysis_groupComp_nsub_{len(self.subject_list)}',
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
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_1', '_cluster0', 'zstat1_threshold.nii.gz'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_1', 'zstat1.nii.gz'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_1', '_cluster0', 'zstat1_threshold.nii.gz'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_1', 'zstat1.nii.gz'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_1', '_cluster0', 'zstat1_threshold.nii.gz'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_1', 'zstat1.nii.gz'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_1', '_cluster0', 'zstat1_threshold.nii.gz'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_1', 'zstat1.nii.gz'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_2', '_cluster0', 'zstat1_threshold.nii.gz'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_2', 'zstat1.nii.gz'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_2', '_cluster0', 'zstat1_threshold.nii.gz'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_2', 'zstat1.nii.gz'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_2', '_cluster0', 'zstat1_threshold.nii.gz'),
            join(f'group_level_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_2', 'zstat1.nii.gz'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_2', '_cluster0', 'zstat1_threshold.nii.gz'),
            join(f'group_level_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_2', 'zstat1.nii.gz'),
            join(f'group_level_analysis_groupComp_nsub_{nb_sub}',
                '_contrast_id_2', '_cluster0', 'zstat1_threshold.nii.gz'),
            join(f'group_level_analysis_groupComp_nsub_{nb_sub}',
                '_contrast_id_2', 'zstat1.nii.gz')
        ]
        return [join(self.directories.output_dir, f) for f in files]
