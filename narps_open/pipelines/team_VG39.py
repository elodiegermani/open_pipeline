#!/usr/bin/python
# coding: utf-8

""" Write the work of NARPS' team 2T6S using Nipype """

from os.path import join
from itertools import product

from nipype import Workflow, Node, MapNode
from nipype.interfaces.utility import IdentityInterface, Function
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.interfaces.spm import (
    Smooth,
    Level1Design, OneSampleTTestDesign, TwoSampleTTestDesign,
    EstimateModel, EstimateContrast, Threshold
    )
from nipype.algorithms.modelgen import SpecifySPMModel
from nipype.algorithms.misc import Gunzip

from narps_open.pipelines import Pipeline

class PipelineTeam2T6S(Pipeline):
    """ A class that defines the pipeline of team 2T6S. """

    def __init__(self):
        super().__init__()
        self.fwhm = 5.0
        self.team_id = 'VG39'
        self.contrast_list = ['0001', '0002', '0003', '0004']

    def get_preprocessing(self):
        """ No preprocessing has been done by team 2T6S """
        return None

    def get_run_level_analysis(self):
        """ No run level analysis has been done by team 2T6S """
        return None

    # @staticmethod # Starting python 3.10, staticmethod should be used here
    # Otherwise it produces a TypeError: 'staticmethod' object is not callable
    def get_subject_infos(event_files, runs):
        """ Create Bunchs for specifySPMModel.

        Parameters :
        - event_files: list of str, list of events files (one per run) for the subject
        - runs: list of str, list of runs to use

        Returns :
        - subject_info : list of Bunch for 1st level analysis.
        """
        from nipype.interfaces.base import Bunch

        condition_names = ['trial']
        onset = {}
        duration = {}
        weights_gain = {}
        weights_loss = {}
        rt = {}

        for run_id in range(len(runs)):
            # Create dictionary items with empty lists
            onset.update({c + '_run' + str(run_id + 1) : [] for c in condition_names})
            duration.update({c + '_run' + str(run_id + 1) : [] for c in condition_names})
            weights_gain.update({'gain_run' + str(run_id + 1) : []})
            weights_loss.update({'loss_run' + str(run_id + 1) : []})

            with open(event_files[run_id], 'rt') as event_file:
                next(event_file)  # skip the header

                for line in event_file:
                    info = line.strip().split()

                    for condition in condition_names:
                        val = condition + '_run' + str(run_id + 1) # trial_run1
                        val_gain = 'gain_run' + str(run_id + 1) # gain_run1
                        val_loss = 'loss_run' + str(run_id + 1) # loss_run1
                        onset[val].append(float(info[0])) # onsets for trial_run1
                        # "The first predictor in the model was the onset of the gamble event, with a duration of 0"
                        duration[val].append(float(0))
                        weights_gain[val_gain].append(float(info[2])) # weights gain for trial_run1
                        weights_loss[val_loss].append(-1.0 * float(info[3])) # weights loss for trial_run1

                    # "The second predictor in the model was the reaction time (RT) of the subject to the gamble stimulus."
                    rt.append(float(info[4]))

            # demeaning
            # "Specifically, the mean of all gains across the entire task was subtracted from every gain value to find the parametric modulator for each event"
            weights_gain = weights_gain-np.mean(weights_gain)
            # "An equivalent demeaning procedure was repeated for the loss parametric modulator"
            weights_loss = weights_loss-np.mean(weights_loss)

            


        # Bunching is done per run, i.e. trial_run1, trial_run2, etc.
        # But names must not have '_run1' etc because we concatenate runs
        subject_info = []
        for run_id in range(len(runs)):

            conditions = [c + '_run' + str(run_id + 1) for c in condition_names]
            gain = 'gain_run' + str(run_id + 1)
            loss = 'loss_run' + str(run_id + 1)

            subject_info.insert(
                run_id,
                Bunch(
                    conditions = condition_names,
                    onsets = [onset[c] for c in conditions],
                    durations = [duration[c] for c in conditions],
                    amplitudes = None,
                    tmod = None,
                    pmod = [Bunch(
                        name = ['gain', 'loss'],
                        poly = [1, 1],
                        param = [weights_gain[gain], weights_loss[loss]])
                    ],
                    regressor_names = None,
                    regressors = None)
                )

        return subject_info

    # @staticmethod # Starting python 3.10, staticmethod should be used here
    # Otherwise it produces a TypeError: 'staticmethod' object is not callable
    def get_contrasts():
        """
        Create a list of tuples that represent contrasts.
        Each contrast is in the form :
        (Name, Stat, [list of condition names],[weights on those conditions])
        """
        # List of condition names
        conditions = ['trial', 'trialxgain^1', 'trialxloss^1']

        # Create contrasts
        trial = ('trial', 'T', conditions, [1, 0, 0])
        effect_gain = ('effect_of_gain', 'T', conditions, [0, 1, 0])
        positive_effect_loss = ('positive_effect_of_loss', 'T', conditions, [0, 0, 1])
        negative_effect_loss = ('negative_effect_of_loss', 'T', conditions, [0, 0, -1])

        # Return contrast list
        return [trial, effect_gain, positive_effect_loss, negative_effect_loss]

    # @staticmethod # Starting python 3.10, staticmethod should be used here
    # Otherwise it produces a TypeError: 'staticmethod' object is not callable
    def get_parameters_file(filepaths, subject_id, working_dir):
        """
        Create new tsv files with only desired parameters per subject per run.

        Parameters :
        - filepaths : paths to subject parameters file (i.e. one per run)
        - subject_id : subject for whom the 1st level analysis is made

        Return :
        - parameters_file : paths to new files containing only desired parameters.
        """
        from os import mkdir
        from os.path import join, isdir

        import pandas as pd
        import numpy as np

        # Handle the case where filepaths is a single path (str)
        if not isinstance(filepaths, list):
            filepaths = [filepaths]

        # Create the parameters files
        parameters_file = []
        for file_id, file in enumerate(filepaths):
            data_frame = pd.read_csv(file, sep = '\t', header=0)

            # Extract parameters we want to use for the model
            temp_list = np.array([
                data_frame['X'], data_frame['Y'], data_frame['Z'],
                data_frame['RotX'], data_frame['RotY'], data_frame['RotZ']])
            retained_parameters = pd.DataFrame(np.transpose(temp_list))

            # Write parameters to a parameters file
            # TODO : warning !!! filepaths must be ordered (1,2,3,4) for the following code to work
            new_path =join(working_dir, 'parameters_file',
                f'parameters_file_sub-{subject_id}_run-{str(file_id + 1).zfill(2)}.tsv')

            if not isdir(join(working_dir, 'parameters_file')):
                mkdir(join(working_dir, 'parameters_file'))

            with open(new_path, 'w') as writer:
                writer.write(retained_parameters.to_csv(
                    sep = '\t', index = False, header = False, na_rep = '0.0'))

            parameters_file.append(new_path)

        return parameters_file

    # @staticmethod # Starting python 3.10, staticmethod should be used here
    # Otherwise it produces a TypeError: 'staticmethod' object is not callable
    def remove_gunzip_files(_, subject_id, working_dir):
        """
        This method is used in a Function node to fully remove
        the files generated by the gunzip node, once they aren't needed anymore.

        Parameters:
        - _: Node input only used for triggering the Node
        - subject_id: str, TODO
        - working_id: str, TODO
        """
        from shutil import rmtree
        from os.path import join

        try:
            rmtree(join(working_dir, 'l1_analysis', f'_subject_id_{subject_id}', 'gunzip_func'))
        except OSError as error:
            print(error)
        else:
            print('The directory is deleted successfully')

    # @staticmethod # Starting python 3.10, staticmethod should be used here
    # Otherwise it produces a TypeError: 'staticmethod' object is not callable
    def remove_smoothed_files(_, subject_id, working_dir):
        """
        This method is used in a Function node to fully remove
        the files generated by the smoothing node, once they aren't needed anymore.

        Parameters:
        - _: Node input only used for triggering the Node
        - subject_id: str, TODO
        - working_id: str, TODO
        """
        from shutil import rmtree
        from os.path import join

        try:
            rmtree(join(working_dir, 'l1_analysis', f'_subject_id_{subject_id}', 'smooth'))
        except OSError as error:
            print(error)
        else:
            print('The directory is deleted successfully')

    def get_subject_level_analysis(self):
        """
        Create the subject level analysis workflow.

        Returns:
            - l1_analysis : nipype.WorkFlow
        """
        # Infosource Node - To iterate on subjects
        infosource = Node(IdentityInterface(
            fields = ['subject_id', 'dataset_dir', 'results_dir', 'working_dir', 'run_list'],
            dataset_dir = self.directories.dataset_dir,
            results_dir = self.directories.results_dir,
            working_dir = self.directories.working_dir,
            run_list = self.run_list),
            name = 'infosource')
        infosource.iterables = [('subject_id', self.subject_list)]

        # Templates to select files node
        template = {
            # Parameter file
            'param' : join('derivatives', 'fmriprep', 'sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-*_bold_confounds.tsv'),
            # Functional MRI
            'func' : join('derivatives', 'fmriprep', 'sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-*_bold_space-MNI152NLin2009cAsym_preproc.nii.gz'),
            # Event file
            'event' : join('sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-*_events.tsv')
        }

        # SelectFiles - to select necessary files
        selectfiles = Node(SelectFiles(template, base_directory = self.directories.dataset_dir),
            name = 'selectfiles')

        # DataSink - store the wanted results in the wanted repository
        datasink = Node(DataSink(base_directory = self.directories.output_dir),
            name = 'datasink')

        # Gunzip - gunzip files because SPM do not use .nii.gz files
        gunzip_func = MapNode(Gunzip(),
            name = 'gunzip_func',
            iterfield = ['in_file'])

        # Smooth - smoothing node
        smooth = Node(Smooth(fwhm = self.fwhm),
            name = 'smooth')

        # Funcion node get_subject_infos - get subject specific condition information
        subject_infos = Node(Function(
            function = self.get_subject_infos,
            input_names = ['event_files', 'runs'],
            output_names = ['subject_info']),
            name = 'subject_infos')

        # SpecifyModel - generates SPM-specific Model
        specify_model = Node(SpecifySPMModel(
            concatenate_runs = True, input_units = 'secs', output_units = 'secs',
            time_repetition = self.tr, high_pass_filter_cutoff = 128),
            name = 'specify_model')

        # Level1Design - generates an SPM design matrix
        # "Only the canonical HRF was used to build the predictors."
        l1_design = Node(Level1Design(
            bases = {'hrf': {'derivs': [0, 0]}}, timing_units = 'secs',
            interscan_interval = self.tr),
            name = 'l1_design')

        # EstimateModel - estimate the parameters of the model
        l1_estimate = Node(EstimateModel(
            estimation_method = {'Classical': 1}),
            name = 'l1_estimate')

        # Function node get_contrasts - get the contrasts
        contrasts = Node(Function(
            function = self.get_contrasts,
            input_names = [],
            output_names = ['contrasts']),
            name = 'contrasts')

        # Function node get_parameters_file - get parameters files
        parameters = Node(Function(
            function = self.get_parameters_file,
            input_names = ['filepaths', 'subject_id', 'working_dir'],
            output_names = ['parameters_file']),
            name = 'parameters')
        parameters.inputs.working_dir = self.directories.working_dir

        # EstimateContrast - estimates contrasts
        contrast_estimate = Node(EstimateContrast(),
            name = 'contrast_estimate')

        # Function node remove_gunzip_files - remove output of the gunzip node
        remove_gunzip_files = Node(Function(
            function = self.remove_gunzip_files,
            input_names = ['_', 'subject_id', 'working_dir'],
            output_names = []),
            name = 'remove_gunzip_files')
        remove_gunzip_files.inputs.working_dir = self.directories.working_dir

        # Function node remove_smoothed_files - remove output of the smooth node
        remove_smoothed_files = Node(Function(
            function = self.remove_smoothed_files,
            input_names = ['_', 'subject_id', 'working_dir'],
            output_names = []),
            name = 'remove_smoothed_files')
        remove_smoothed_files.inputs.working_dir = self.directories.working_dir

        # Create l1 analysis workflow and connect its nodes
        l1_analysis = Workflow(base_dir = self.directories.working_dir, name = 'l1_analysis')
        l1_analysis.connect([
            (infosource, selectfiles, [('subject_id', 'subject_id')]),
            (infosource, subject_infos, [('run_list', 'runs')]),
            (infosource, remove_gunzip_files, [('subject_id', 'subject_id')]),
            (infosource, remove_smoothed_files, [('subject_id', 'subject_id')]),
            (subject_infos, specify_model, [('subject_info', 'subject_info')]),
            (contrasts, contrast_estimate, [('contrasts', 'contrasts')]),
            (selectfiles, parameters, [('param', 'filepaths')]),
            (selectfiles, subject_infos, [('event', 'event_files')]),
            (infosource, parameters, [
                ('subject_id', 'subject_id'),
                ('working_dir', 'working_dir')]),
            (selectfiles, gunzip_func, [('func', 'in_file')]),
            (gunzip_func, smooth, [('out_file', 'in_files')]),
            (smooth, specify_model, [('smoothed_files', 'functional_runs')]),
            (smooth, remove_gunzip_files, [('smoothed_files', '_')]),
            (parameters, specify_model, [('parameters_file', 'realignment_parameters')]),
            (specify_model, l1_design, [('session_info', 'session_info')]),
            (l1_design, l1_estimate, [('spm_mat_file', 'spm_mat_file')]),
            (l1_estimate, contrast_estimate, [
                ('spm_mat_file', 'spm_mat_file'),
                ('beta_images', 'beta_images'),
                ('residual_image', 'residual_image')]),
            (contrast_estimate, datasink, [
                ('con_images', 'l1_analysis.@con_images'),
                ('spmT_images', 'l1_analysis.@spmT_images'),
                ('spm_mat_file', 'l1_analysis.@spm_mat_file')]),
            (contrast_estimate, remove_smoothed_files, [('spmT_images', '_')])
            ])

        return l1_analysis

    def get_subject_level_outputs(self):
        """ Return the names of the files the subject level analysis is supposed to generate. """

        # Contrat maps
        templates = [join(
            self.directories.output_dir,
            'l1_analysis', '_subject_id_{subject_id}', f'con_{contrast_id}.nii')\
            for contrast_id in self.contrast_list]

        # SPM.mat file
        templates += [join(
            self.directories.output_dir,
            'l1_analysis', '_subject_id_{subject_id}', 'SPM.mat')]

        # spmT maps
        templates += [join(
            self.directories.output_dir,
            'l1_analysis', '_subject_id_{subject_id}', f'spmT_{contrast_id}.nii')\
            for contrast_id in self.contrast_list]

        # Format with subject_ids
        return_list = []
        for template in templates:
            return_list += [template.format(subject_id = s) for s in self.subject_list]

        return return_list

    # @staticmethod # Starting python 3.10, staticmethod should be used here
    # Otherwise it produces a TypeError: 'staticmethod' object is not callable
    def get_subset_contrasts(file_list, subject_list, participants_file):
        """
        Parameters :
        - file_list : original file list selected by selectfiles node
        - subject_list : list of subject IDs that are in the wanted group for the analysis
        - participants_file: str, file containing participants caracteristics

        Returns :
        - equal_indifference_id : a list of subject ids in the equalIndifference group
        - equal_range_id : a list of subject ids in the equalRange group
        - equal_indifference_files : a subset of file_list corresponding to subjects in the equalIndifference group
        - equal_range_files : a subset of file_list corresponding to subjects in the equalRange group
        """
        equal_indifference_id = []
        equal_range_id = []
        equal_indifference_files = []
        equal_range_files = []

        with open(participants_file, 'rt') as file:
            next(file)  # skip the header
            for line in file:
                info = line.strip().split()
                if info[0][-3:] in subject_list and info[1] == 'equalIndifference':
                    equal_indifference_id.append(info[0][-3:])
                elif info[0][-3:] in subject_list and info[1] == 'equalRange':
                    equal_range_id.append(info[0][-3:])

        for file in file_list:
            sub_id = file.split('/')
            if sub_id[-2][-3:] in equal_indifference_id:
                equal_indifference_files.append(file)
            elif sub_id[-2][-3:] in equal_range_id:
                equal_range_files.append(file)

        return equal_indifference_id, equal_range_id, equal_indifference_files, equal_range_files

    # @staticmethod # Starting python 3.10, staticmethod should be used here
    # Otherwise it produces a TypeError: 'staticmethod' object is not callable
    def reorganize_results(team_id, nb_sub, output_dir, results_dir):
        """ Reorganize the results to analyze them. """
        from os import mkdir
        from os.path import join, isdir
        from shutil import copyfile

        hypotheses = [
            join(output_dir, f'l2_analysis_equalIndifference_nsub_{nb_sub}', '_contrast_id_02'),
            join(output_dir, f'l2_analysis_equalRange_nsub_{nb_sub}', '_contrast_id_02'),
            join(output_dir, f'l2_analysis_equalIndifference_nsub_{nb_sub}', '_contrast_id_02'),
            join(output_dir, f'l2_analysis_equalRange_nsub_{nb_sub}', '_contrast_id_02'),
            join(output_dir, f'l2_analysis_equalIndifference_nsub_{nb_sub}', '_contrast_id_04'),
            join(output_dir, f'l2_analysis_equalRange_nsub_{nb_sub}', '_contrast_id_04'),
            join(output_dir, f'l2_analysis_equalIndifference_nsub_{nb_sub}', '_contrast_id_04'),
            join(output_dir, f'l2_analysis_equalRange_nsub_{nb_sub}', '_contrast_id_04'),
            join(output_dir, f'l2_analysis_groupComp_nsub_{nb_sub}', '_contrast_id_03')
        ]

        # Build lists of files for unthresholded and thresholded maps
        repro_unthresh = []
        repro_thresh = []
        for file_id, filename in enumerate(hypotheses):
            if file_id in [4,5]:
                repro_unthresh.append(join(filename, 'spmT_0002.nii'))
                repro_thresh.append(join(filename, '_threshold1', 'spmT_0002_thr.nii'))
            else:
                repro_unthresh.append(join(filename, 'spmT_0001.nii'))
                repro_thresh.append(join(filename, '_threshold0', 'spmT_0001_thr.nii'))

        if not isdir(join(results_dir, 'NARPS-reproduction')):
            mkdir(join(results_dir, 'NARPS-reproduction'))

        for file_id, filename in enumerate(repro_unthresh):
            f_in = filename
            f_out = join(results_dir,
                'NARPS-reproduction',
                f'team-{team_id}_nsub-{nb_sub}_hypo-{file_id + 1}_unthresholded.nii')
            copyfile(f_in, f_out)

        for file_id, filename in enumerate(repro_thresh):
            f_in = filename
            f_out = join(results_dir,
                'NARPS-reproduction',
                f'team-{team_id}_nsub-{nb_sub}_hypo-{file_id + 1}_thresholded.nii')
            copyfile(f_in, f_out)

        print(f'Results files of team {team_id} reorganized.')

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
            - l2_analysis: nipype.WorkFlow
        """
        # Compute the number of participants used to do the analysis
        nb_subjects = len(self.subject_list)

        # Infosource - iterate over the list of contrasts
        infosource_groupanalysis = Node(
            IdentityInterface(
                fields = ['contrast_id', 'subjects'],
                subjects = self.subject_list),
                name = 'infosource_groupanalysis')
        infosource_groupanalysis.iterables = [('contrast_id', self.contrast_list)]

        # SelectFiles
        templates = {
            # Contrast for all participants
            'contrast' : join(self.directories.output_dir,
                'l1_analysis', '_subject_id_*', 'con_{contrast_id}.nii'),
            # Participants file
            'participants' : join(self.directories.dataset_dir, 'participants.tsv')
            }

        selectfiles_groupanalysis = Node(SelectFiles(
            templates, base_directory=self.directories.results_dir, force_list= True),
            name = 'selectfiles_groupanalysis')

        # Datasink - save important files
        datasink_groupanalysis = Node(DataSink(
            base_directory = str(self.directories.output_dir)
            ),
            name = 'datasink_groupanalysis')

        # Function node reorganize_results - organize results once computed
        reorganize_res = Node(Function(
            function = self.reorganize_results,
            input_names = ['team_id', 'nb_subjects', 'results_dir', 'output_dir']),
            name = 'reorganize_res')
        reorganize_res.inputs.team_id = self.team_id
        reorganize_res.inputs.nb_subjects = nb_subjects
        reorganize_res.inputs.results_dir = self.directories.results_dir
        reorganize_res.inputs.output_dir = self.directories.output_dir

        # Function node get_subset_contrasts - select subset of contrasts
        sub_contrasts = Node(Function(
            function = self.get_subset_contrasts,
            input_names = ['file_list', 'method', 'subject_list', 'participants_file'],
            output_names = [
                'equalIndifference_id',
                'equalRange_id',
                'equalIndifference_files',
                'equalRange_files']),
            name = 'sub_contrasts')
        sub_contrasts.inputs.method = method

        # Estimate model
        estimate_model = Node(EstimateModel(
            estimation_method = {'Classical':1}),
            name = 'estimate_model')

        # Estimate contrasts
        estimate_contrast = Node(EstimateContrast(
            group_contrast = True),
            name = 'estimate_contrast')

        # Create thresholded maps
        threshold = MapNode(Threshold(
            use_topo_fdr = False, use_fwe_correction = False, extent_threshold = 10,
            height_threshold = 0.001, height_threshold_type = 'p-value',
            force_activation = True),
            name = 'threshold', iterfield = ['stat_image', 'contrast_index'])

        l2_analysis = Workflow(
            base_dir = self.directories.working_dir,
            name = f'l2_analysis_{method}_nsub_{nb_subjects}')
        l2_analysis.connect([
            (infosource_groupanalysis, selectfiles_groupanalysis, [
                ('contrast_id', 'contrast_id')]),
            (infosource_groupanalysis, sub_contrasts, [
                ('subjects', 'subject_list')]),
            (selectfiles_groupanalysis, sub_contrasts, [
                ('contrast', 'file_list'),
                ('participants', 'participants_file')]),
            (estimate_model, estimate_contrast, [('spm_mat_file', 'spm_mat_file'),
                ('residual_image', 'residual_image'),
                ('beta_images', 'beta_images')]),
            (estimate_contrast, threshold, [('spm_mat_file', 'spm_mat_file'),
                ('spmT_images', 'stat_image')]),
            (estimate_model, datasink_groupanalysis, [
                ('mask_image', f'l2_analysis_{method}_nsub_{nb_subjects}.@mask')]),
            (estimate_contrast, datasink_groupanalysis, [
                ('spm_mat_file', f'l2_analysis_{method}_nsub_{nb_subjects}.@spm_mat'),
                ('spmT_images', f'l2_analysis_{method}_nsub_{nb_subjects}.@T'),
                ('con_images', f'l2_analysis_{method}_nsub_{nb_subjects}.@con')]),
            (threshold, datasink_groupanalysis, [
                ('thresholded_map', f'l2_analysis_{method}_nsub_{nb_subjects}.@thresh')])])

        if method in ('equalRange', 'equalIndifference'):
            contrasts = [('Group', 'T', ['mean'], [1]), ('Group', 'T', ['mean'], [-1])]

            threshold.inputs.contrast_index = [1, 2]
            threshold.synchronize = True

            ## Specify design matrix
            one_sample_t_test_design = Node(OneSampleTTestDesign(),
                name = 'one_sample_t_test_design')

            l2_analysis.connect([
                (sub_contrasts, one_sample_t_test_design, [(f'{method}_files', 'in_files')]),
                (one_sample_t_test_design, estimate_model, [('spm_mat_file', 'spm_mat_file')])])

        elif method == 'groupComp':
            contrasts = [
                ('Eq range vs Eq indiff in loss', 'T', ['Group_{1}', 'Group_{2}'], [-1, 1])]

            threshold.inputs.contrast_index = [1]
            threshold.synchronize = True

            # Node for the design matrix
            two_sample_t_test_design = Node(TwoSampleTTestDesign(),
                name = 'two_sample_t_test_design')

            l2_analysis.connect([
                (sub_contrasts, two_sample_t_test_design, [
                    ('equalRange_files', 'group1_files'),
                    ('equalIndifference_files', 'group2_files')]),
                (two_sample_t_test_design, estimate_model, [
                    ('spm_mat_file', 'spm_mat_file')])
                ])

        estimate_contrast.inputs.contrasts = contrasts

        return l2_analysis

    def get_group_level_outputs(self):
        """ Return all names for the files the group level analysis is supposed to generate. """

        # Handle equalRange and equalIndifference
        parameters = {
            'contrast_id': ['0001', '0002', '0003', '0004'],
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
            'l2_analysis_{method}_nsub_{nb_subjects}',
            '_contrast_id_{contrast_id}',
            '{file}'
            )

        return_list = [template.format(**dict(zip(parameters.keys(), parameter_values)))\
            for parameter_values in parameter_sets]

        # Handle groupComp
        parameters = {
            'contrast_id': ['0001', '0002', '0003', '0004'],
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
            'l2_analysis_{method}_nsub_{nb_subjects}',
            '_contrast_id_{contrast_id}',
            '{file}'
            )

        return_list += [template.format(**dict(zip(parameters.keys(), parameter_values)))\
            for parameter_values in parameter_sets]

        return return_list
