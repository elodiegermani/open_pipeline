#!/usr/bin/python
# coding: utf-8

""" Write the work of NARPS' team 80GC using Nipype """

from os.path import join
from itertools import product

from nipype import Workflow, Node, MapNode
from nipype.interfaces.utility import IdentityInterface, Function
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.interfaces.afni import Deconvolve, MaskTool

from narps_open.pipelines import Pipeline
from narps_open.data.participants import get_group
from narps_open.core.common import (
    list_intersection, elements_in_string, clean_list
    )
from narps_open.core.interfaces.afni import Ttestpp, SelectSubBrick

class PipelineTeam80GC(Pipeline):
    """ A class that defines the pipeline of team 80GC. """

    def __init__(self):
        super().__init__()
        self.team_id = '80GC'
        self.contrast_list = ['gain', 'loss']
        self.contrast_indices = [5, 6]
        self.subject_level_contrasts = ['SYM: +gain', 'SYM: +loss']

    def get_preprocessing(self):
        """ No preprocessing has been done by team 80GC """
        return None

    def get_run_level_analysis(self):
        """ No run level analysis has been done by team 80GC """
        return None

    def get_events_files(event_files, nb_events, subject_id):
        """
        Create a stimuli file to be read by AFNI's 3DDeconvolve

        Parameters :
        - event_files: list of str, event files, on for each run of one subject
        - nb_events : int, number of events (i.e.: number of data lines in each event file)
            WARNING - We assume that all events files have the same number of lines
        - subject_id : related subject id

        Returns :
        - gain_df_file: str, file containing gain regressor values
        - loss_df_file: str, file containing gain regressor values
        """
        from os.path import abspath

        from pandas import DataFrame, read_csv

        # Init empty dataframes
        gain_df = DataFrame(index=range(0,len(event_files)), columns=range(0,nb_events))
        loss_df = DataFrame(index=range(0,len(event_files)), columns=range(0,nb_events))

        # Extract info from raw event files
        for file_id, event_file in enumerate(event_files):
            events_df = read_csv(event_file, sep = '\t')
            events_df = events_df[['onset', 'gain', 'loss']].T

            gain_df.loc[file_id] = [
                f"{events_df[i].loc['onset']}*{events_df[i].loc['gain']}"\
                for i in range(0, nb_events)
                ]
            loss_df.loc[file_id] = [
                f"{events_df[i].loc['onset']}*{events_df[i].loc['loss']}"\
                for i in range(0, nb_events)
                ]

        # Create AFNI stimuli files
        gain_file = abspath(f'events_sub-{subject_id}_timesxgain.txt')
        loss_file = abspath(f'events_sub-{subject_id}_timesxloss.txt')
        gain_df.to_csv(gain_file, sep='\t', index=False, header=False)
        loss_df.to_csv(loss_file, sep='\t', index=False, header=False)

        return gain_file, loss_file

    def get_events_arguments(gain_event_file, loss_event_file):
        """
        Create a stimuli arguments list to be passed to AFNI's 3DDeconvolve

        Parameters :
        - gain_event_file: str, file containing gain regressor values
        - loss_event_file: str, file containing loss regressor values

        Returns :
        - arguments: str, formatted arguments for AFNI's 3DDeconvolve args input
        """
        arguments = '-stim_label 1 gain '
        #arguments += f'-stim_times_AM2 1 {gain_event_file} \'BLOCK(4,1)\' '
        #arguments += f'-stim_times_AM2 1 {gain_event_file} \'GAM(8.6,.547,4)\' '
        arguments += f'-stim_times_AM2 1 {gain_event_file} \'GAM(8.6,.547)\' '
        arguments += '-stim_label 2 loss '
        #arguments += f'-stim_times_AM2 2 {loss_event_file} \'BLOCK(4,1)\' '
        #arguments += f'-stim_times_AM2 2 {loss_event_file} \'GAM(8.6,.547,4)\' '
        arguments += f'-stim_times_AM2 2 {loss_event_file} \'GAM(8.6,.547)\' '

        return arguments

    def get_confounds_file(confounds_files, nb_time_points, subject_id):
        """
        Create a new tsv file with only desired confounds for a subject

        Parameters :
        - confounds_files : list of str, paths to the subject confounds files
        - nb_time_points : int, number of time points
            (i.e.: number of data lines in each confounds file)
            WARNING - We assume that all confounds files have the same number of lines
        - subject_id : related subject id

        Return :
        - confounds_file : path to new file containing only desired confounds
        """
        from os.path import abspath

        from pandas import DataFrame, read_csv
        from numpy import array, transpose

        # Init empty dataframe
        parameters_df = DataFrame(
            index=range(0,nb_time_points*len(confounds_files)), columns=range(0,6))

        # Open original confounds file
        for file_id, file in enumerate(confounds_files):
            data_frame = read_csv(file, sep = '\t', header=0)

            # Extract confounds we want to use for the model
            parameters_df[file_id*nb_time_points:(file_id+1)*nb_time_points] = DataFrame(
                transpose(array([
                    data_frame['X'].sub(data_frame['X'].mean()),
                    data_frame['Y'].sub(data_frame['Y'].mean()),
                    data_frame['Z'].sub(data_frame['Z'].mean()),
                    data_frame['RotX'].sub(data_frame['RotX'].mean()),
                    data_frame['RotY'].sub(data_frame['RotY'].mean()),
                    data_frame['RotZ'].sub(data_frame['RotZ'].mean())
                ])))

        # Write confounds to a file
        confounds_file = abspath(f'confounds_file_sub-{subject_id}.tsv')
        with open(confounds_file, 'w', encoding = 'utf-8') as writer:
            writer.write(parameters_df.to_csv(
                sep = '\t', index = False, header = False, na_rep = '0.0'))

        return confounds_file

    def get_confounds_arguments(confounds_file):
        """
        Create a confounds arguments list to be passed to AFNI's 3DDeconvolve

        Parameters :
        - confounds_file: str, file containing confounds

        Returns :
        - arguments: str, formatted arguments for AFNI's 3DDeconvolve args input
        """

        arguments = '-stim_base 3 -stim_label 3 x_motion_regressor '
        arguments += f'-stim_file 3 {confounds_file}\'[0]\' '
        arguments += '-stim_base 4 -stim_label 4 y_motion_regressor '
        arguments += f'-stim_file 4 {confounds_file}\'[1]\' '
        arguments += '-stim_base 5 -stim_label 5 z_motion_regressor '
        arguments += f'-stim_file 5 {confounds_file}\'[2]\' '
        arguments += '-stim_base 6 -stim_label 6 rotx_motion_regressor '
        arguments += f'-stim_file 6 {confounds_file}\'[3]\' '
        arguments += '-stim_base 7 -stim_label 7 roty_motion_regressor '
        arguments += f'-stim_file 7 {confounds_file}\'[4]\' '
        arguments += '-stim_base 8 -stim_label 8 rotz_motion_regressor '
        arguments += f'-stim_file 8 {confounds_file}\'[5]\' '

        return arguments

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
            'confounds' : join('derivatives', 'fmriprep', 'sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-*_bold_confounds.tsv'),
            'func' : join('derivatives', 'fmriprep', 'sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-*_bold_space-MNI152NLin2009cAsym_preproc.nii.gz'),
            'event' : join('sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-*_events.tsv')
        }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.dataset_dir
        subject_level.connect(information_source, 'subject_id', select_files, 'subject_id')

        # FUNCTION get_events_file - generate files with event data
        events_information = Node(Function(
            function = self.get_events_files,
            input_names = ['event_files', 'nb_events', 'subject_id'],
            output_names = ['gain_file', 'loss_file']),
            name = 'events_information')
        events_information.inputs.nb_events = 64
        subject_level.connect(select_files, 'event', events_information, 'event_files')
        subject_level.connect(information_source, 'subject_id', events_information, 'subject_id')

        # FUNCTION get_events_arguments - generate arguments for 3ddeconvolve with event data
        events_arguments = Node(Function(
            function = self.get_events_arguments,
            input_names = ['gain_event_file', 'loss_event_file'],
            output_names = ['arguments']),
            name = 'events_arguments')
        subject_level.connect(events_information, 'gain_file', events_arguments, 'gain_event_file')
        subject_level.connect(events_information, 'loss_file', events_arguments, 'loss_event_file')

        # FUNCTION get_confounds_file - generate files with event data
        confounds_information = Node(Function(
            function = self.get_confounds_file,
            input_names = ['confounds_files', 'nb_time_points', 'subject_id'],
            output_names = ['confounds_file']),
            name = 'confounds_information')
        confounds_information.inputs.nb_time_points = 453
        subject_level.connect(select_files, 'confounds', confounds_information, 'confounds_files')
        subject_level.connect(
            information_source, 'subject_id', confounds_information, 'subject_id')

        # FUNCTION get_events_arguments - generate arguments for 3ddeconvolve with confounds data
        confounds_arguments = Node(Function(
            function = self.get_confounds_arguments,
            input_names = ['confounds_file'],
            output_names = ['arguments']),
            name = 'confounds_arguments')
        subject_level.connect(
            confounds_information, 'confounds_file', confounds_arguments, 'confounds_file')

        # FUNCTION concatenate strings - merge outputs from get_events_file and get_confounds_file
        concat_function = lambda a_str, b_str, c_str: a_str + b_str + c_str
        merge_arguments = Node(Function(
            function = concat_function,
            input_names = ['a_str', 'b_str', 'c_str'],
            output_names = ['out_str']),
            name = 'merge_arguments')
        other_args = '-xjpeg design_matrix.jpg -num_stimts 8 '
        merge_arguments.inputs.a_str = other_args
        subject_level.connect(events_arguments, 'arguments', merge_arguments, 'b_str')
        subject_level.connect(confounds_arguments, 'arguments', merge_arguments, 'c_str')

        # DECONVOLVE - Run the regression analysis
        deconvolve = Node(Deconvolve(), name = 'deconvolve')
        deconvolve.inputs.polort = 4  # -float
        deconvolve.inputs.fout = False
        deconvolve.inputs.tout = False
        deconvolve.inputs.goforit = 8
        deconvolve.inputs.num_threads = 1 # Parameter -jobs
        deconvolve.inputs.x1D = 'design_matrix.xmat.1D'
        deconvolve.inputs.out_file = 'out_deconvolve.nii'
        deconvolve.inputs.gltsym = self.subject_level_contrasts
        deconvolve.inputs.glt_label = [(1, self.contrast_list[0]), (2, self.contrast_list[1])]
        subject_level.connect(select_files, 'func', deconvolve, 'in_files')
        subject_level.connect(merge_arguments, 'out_str', deconvolve, 'args')

        # DATA SINK - store the wanted results in the wanted repository
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        subject_level.connect(deconvolve, 'out_file', data_sink, 'subject_level_analysis.@out_file')
        subject_level.connect(deconvolve, 'x1D', data_sink, 'subject_level_analysis.@x1D')

        return subject_level

    def get_subject_level_outputs(self):
        """ Return the names of the files the subject level analysis is supposed to generate. """

        # Deconvolve output file containing contrasts etc.
        # Here is the complete list of what the file contains:
        #   0 - Full_Fstat
        #   1 - gain#0_Coef
        #   2 - gain#1_Coef
        #   3 - loss#0_Coef
        #   4 - loss#1_Coef
        #   5 - gain_GLT#0_Coef
        #   6 - loss_GLT#0_Coef
        templates = [join(
            self.directories.output_dir,
            'subject_level_analysis', '_subject_id_{subject_id}', 'out_deconvolve.nii')]

        # Design matrix
        templates += [join(
            self.directories.output_dir,
            'subject_level_analysis', '_subject_id_{subject_id}', 'design_matrix.xmat.1D')]

        # Format with subject_ids
        return_list = []
        for template in templates:
            return_list += [template.format(subject_id = s) for s in self.subject_list]

        return return_list

    def select_subbrick(in_file: str, index: int):
        """
        Create a tuple (file, index) for AFNI interfaces allowing to select a sub-brick
            for input file.

        Parameters :
        - in_file: str, files to select the sub-brick from
        - index: int, index of the desired sub-brick in in_file

        Returns :
        - out: tuple, (in_file, index)
        """
        return (in_file, index)

    def get_group_level_analysis(self):
        """
        Return a workflow for the group level analysis.

        Returns:
            - group_level: nipype.WorkFlow
        """

        # Init the workflow
        nb_subjects = len(self.subject_list)
        group_level = Workflow(
            base_dir = self.directories.working_dir,
            name = f'group_level_analysis_nsub_{nb_subjects}')

        # IDENTITY INTERFACE - Iterate over the list of contrasts from the subject level
        info_source = Node(
            IdentityInterface(fields=['contrast_id', 'contrast_index', 'subject_list']),
            name = 'info_source'
            )
        info_source.iterables = [
            ('contrast_id', self.contrast_list),
            ('contrast_index', self.contrast_indices)
            ]
        info_source.inputs.subject_list = self.subject_list
        info_source.synchronize = True

        # SELECT FILES - Select necessary files
        templates = {
            'deconvolve_bucket' : join(self.directories.output_dir, 'subject_level_analysis',
                '_subject_id_*', 'out_deconvolve.nii'),
            'masks' : join('derivatives', 'fmriprep', 'sub-*', 'func',
                'sub-*_task-MGT_run-*_bold_space-MNI152NLin2009cAsym_brainmask.nii.gz')
        }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.dataset_dir
        select_files.inputs.force_list = True

        # SELECT SUBJECTS

        # Create a function to complete the subject ids out from the get_equal*_subjects node
        complete_subject_ids = lambda l : [f'_subject_id_{a}' for a in l]
        complete_sub_ids = lambda l : [f'sub-{a}' for a in l]

        # Function Node list_intersection - Get subjects from the subject_list
        #   that are in the `equalRange` group
        equal_range_subjects = Node(Function(
            function = list_intersection,
            input_names = ['list_1', 'list_2'],
            output_names = ['out_list']
            ),
            name = 'equal_range_subjects'
        )
        equal_range_subjects.inputs.list_1 = get_group('equalRange')
        equal_range_subjects.inputs.list_2 = self.subject_list

        # Function Node list_intersection - Get subjects from the subject_list
        #   that are in the `equalIndifference` group
        equal_indifference_subjects = Node(Function(
            function = list_intersection,
            input_names = ['list_1', 'list_2'],
            output_names = ['out_list']
            ),
            name = 'equal_indifference_subjects'
        )
        equal_indifference_subjects.inputs.list_1 = get_group('equalIndifference')
        equal_indifference_subjects.inputs.list_2 = self.subject_list

        # Function Node elements_in_string - Get contrast files for equalRange subjects
        # Note : using a MapNode with elements_in_string requires using clean_list to remove
        #   None values from the out_list
        equal_range_contrasts = MapNode(Function(
            function = elements_in_string,
            input_names = ['input_str', 'elements'],
            output_names = ['out_list']
            ),
            name = 'equal_range_contrasts', iterfield = 'input_str'
        )
        group_level.connect(select_files, 'deconvolve_bucket', equal_range_contrasts, 'input_str')
        group_level.connect(
            equal_range_subjects, ('out_list', complete_subject_ids),
            equal_range_contrasts, 'elements')

        # Function Node elements_in_string - Get contrast files for equalIndifference subjects
        # Note : using a MapNode with elements_in_string requires using clean_list to remove
        #   None values from the out_list
        equal_indifference_contrasts = MapNode(Function(
            function = elements_in_string,
            input_names = ['input_str', 'elements'],
            output_names = ['out_list']
            ),
            name = 'equal_indifference_contrasts', iterfield = 'input_str'
        )
        group_level.connect(
            select_files, 'deconvolve_bucket', equal_indifference_contrasts, 'input_str')
        group_level.connect(
            equal_indifference_subjects, ('out_list', complete_subject_ids),
            equal_indifference_contrasts, 'elements')

        # Function Node select_subbrick - Create setA list of input files for 3dttest++
        set_a_arguments = MapNode(Function(
            function = self.select_subbrick,
            input_names = ['in_file', 'index'],
            output_names = ['out']
            ),
            name = 'set_a_arguments',
            iterfield = 'in_file'
        )
        group_level.connect(info_source, 'contrast_index', set_a_arguments, 'index')
        group_level.connect(
            equal_range_contrasts, ('out_list', clean_list),
            set_a_arguments, 'in_file')

        # Function Node select_subbrick - Create setB list of input files for 3dttest++
        set_b_arguments = MapNode(Function(
            function = self.select_subbrick,
            input_names = ['in_file', 'index'],
            output_names = ['out']
            ),
            name = 'set_b_arguments',
            iterfield = 'in_file'
        )
        group_level.connect(info_source, 'contrast_index', set_b_arguments, 'index')
        group_level.connect(
            equal_indifference_contrasts, ('out_list', clean_list),
            set_b_arguments, 'in_file')

        # Function Node elements_in_string - Get masks files for all subjects
        # Note : using a MapNode with elements_in_string requires using clean_list to remove
        #   None values from the out_list
        masks = MapNode(Function(
            function = elements_in_string,
            input_names = ['input_str', 'elements'],
            output_names = ['out_list']
            ),
            name = 'masks', iterfield = 'input_str'
        )
        group_level.connect(select_files, 'masks', masks, 'input_str')
        group_level.connect(info_source, ('subject_list', complete_sub_ids), masks, 'elements')

        # MASK TOOL - Create mask intersection
        mask_intersection = Node(MaskTool(), name = 'mask_intersection')
        mask_intersection.inputs.inter = True
        mask_intersection.inputs.outputtype = 'NIFTI'
        group_level.connect(
            masks, ('out_list', clean_list), mask_intersection, 'in_file')

        # 3DTTEST++ - Perform a one sample t-test
        t_test = Node(Ttestpp(), name = 't_test')
        t_test.inputs.set_a_label = 'equalRange'
        t_test.inputs.set_b_label = 'equalIndifference'
        t_test.inputs.toz = True
        t_test.inputs.clustsim = False
        t_test.inputs.nomeans = True
        t_test.inputs.out_file = 'ttestpp_out.nii'
        group_level.connect(mask_intersection, 'out_file', t_test, 'mask')
        group_level.connect(set_a_arguments, 'out', t_test, 'set_a')
        group_level.connect(set_b_arguments, 'out', t_test, 'set_b')

        # Output dataset from t_test consists in 3 sub-bricks :
        # #0  equalRange-equalIndiffe_Zscr
        # #1  equalRange_Zscr
        # #2  equalIndiffe_Zscr

        # SELECT SUB BRICK - Split output of 3dttest++
        select_output = MapNode(SelectSubBrick(), name = 'select_output', iterfield = 'index')
        select_output.inputs.out_file = 'group_level_tstat.nii'
        select_output.inputs.outputtype = 'NIFTI'
        select_output.inputs.index = [0, 1, 2]
        group_level.connect(t_test, 'out_file', select_output, 'in_file')

        # DATA SINK - save important files
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        group_level.connect(
            select_output, 'out_file',
            data_sink, f'group_level_analysis_nsub_{nb_subjects}.@out')

        return group_level

    def get_group_level_outputs(self):
        """ Return all names for the files the group level analysis is supposed to generate. """

        parameters = {
            'contrast_dir': [
                f'_contrast_id_{c}_contrast_index_{i}' for c, i \
                in zip(self.contrast_list, self.contrast_indices)],
            'nb_subjects' : [str(len(self.subject_list))],
            'method' : ['0', '1', '2']
        }
        parameter_sets = product(*parameters.values())
        template = join(
            self.directories.output_dir,
            'group_level_analysis_nsub_{nb_subjects}',
            '{contrast_dir}', '_select_output{method}', 'group_level_tstat.nii'
            )

        return_list = [template.format(**dict(zip(parameters.keys(), parameter_values)))\
            for parameter_values in parameter_sets]

        return return_list

    def get_hypotheses_outputs(self):
        """ Return all hypotheses output file names.
            Note that hypotheses 5 to 8 correspond to the maps given by the team in their results ;
            but they are not fully consistent with the hypotheses definitions as expected by NARPS.
        """
        nb_sub = len(self.subject_list)
        files = [
            # Hypothesis 1
            '',
            join(f'group_level_analysis_nsub_{nb_sub}', '_contrast_id_gain_contrast_index_5',
                '_select_output2', 'group_level_tstat.nii'),
            # Hypothesis 2
            '',
            join(f'group_level_analysis_nsub_{nb_sub}', '_contrast_id_gain_contrast_index_5',
                '_select_output1', 'group_level_tstat.nii'),
            # Hypothesis 3
            '',
            join(f'group_level_analysis_nsub_{nb_sub}', '_contrast_id_gain_contrast_index_5',
                '_select_output2', 'group_level_tstat.nii'),
            # Hypothesis 4
            '',
            join(f'group_level_analysis_nsub_{nb_sub}', '_contrast_id_gain_contrast_index_5',
                '_select_output1', 'group_level_tstat.nii'),
            # Hypothesis 5
            '',
            join(f'group_level_analysis_nsub_{nb_sub}', '_contrast_id_loss_contrast_index_6',
                '_select_output2', 'group_level_tstat.nii'),
            # Hypothesis 6
            '',
            join(f'group_level_analysis_nsub_{nb_sub}', '_contrast_id_loss_contrast_index_6',
                '_select_output1', 'group_level_tstat.nii'),
            # Hypothesis 7
            '',
            join(f'group_level_analysis_nsub_{nb_sub}', '_contrast_id_loss_contrast_index_6',
                '_select_output2', 'group_level_tstat.nii'),
            # Hypothesis 8
            '',
            join(f'group_level_analysis_nsub_{nb_sub}', '_contrast_id_loss_contrast_index_6',
                '_select_output1', 'group_level_tstat.nii'),
            # Hypothesis 9
            '',
            join(f'group_level_analysis_nsub_{nb_sub}', '_contrast_id_loss_contrast_index_6',
                '_select_output0', 'group_level_tstat.nii'),
        ]
        return [join(self.directories.output_dir, f) for f in files]
