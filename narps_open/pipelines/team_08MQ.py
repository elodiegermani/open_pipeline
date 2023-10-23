#!/usr/bin/python
# coding: utf-8

""" Write the work of NARPS team 08MQ using Nipype """

from os.path import join
from itertools import product

from nipype import Node, Workflow
from nipype.interfaces.utility import IdentityInterface, Function, Merge, Split
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.interfaces.fsl import (
    FSLCommand,

    FAST, BET, ErodeImage, PrepareFieldmap, MCFLIRT, SliceTimer,
    Threshold, Info, SUSAN, FLIRT, EpiReg, ApplyXFM, ConvertXFM,

    Level1Design, FEATModel, L2Model, FILMGLS

    # , Merge, FLAMEO,    Randomise, MultipleRegressDesign
    )
from nipype.algorithms.confounds import CompCor
from nipype.algorithms.modelgen import SpecifyModel
from nipype.interfaces.ants import Registration, ApplyTransforms
from narps_open.pipelines import Pipeline
from narps_open.data.task import TaskInformation

# Setup FSL
FSLCommand.set_default_output_type('NIFTI_GZ')

class PipelineTeam08MQ(Pipeline):
    """ A class that defines the pipeline of team 08MQ """

    def __init__(self):
        super().__init__()
        self.fwhm = 6.0
        self.team_id = '08MQ'
        self.contrast_list = ['1', '2', '3']

    def get_preprocessing(self):
        """ Return a Nipype workflow describing the prerpocessing part of the pipeline """

        # IdentityInterface node - allows to iterate over subjects and runs
        info_source = Node(IdentityInterface(
            fields = ['subject_id', 'run_id']),
            name = 'info_source')
        info_source.iterables = [
            ('run_id', self.run_list),
            ('subject_id', self.subject_list),
        ]

        # SelectFiles node - to select necessary files
        file_templates = {
            'anat': join('sub-{subject_id}', 'anat', 'sub-{subject_id}_T1w.nii.gz'),
            'func': join(
                'sub-{subject_id}', 'func', 'sub-{subject_id}_task-MGT_run-{run_id}_bold.nii.gz'
                ),
            'sbref': join(
                'sub-{subject_id}', 'func', 'sub-{subject_id}_task-MGT_run-{run_id}_sbref.nii.gz'
                ),
            'magnitude': join('sub-{subject_id}', 'fmap', 'sub-{subject_id}_magnitude1.nii.gz'),
            'phasediff': join('sub-{subject_id}', 'fmap', 'sub-{subject_id}_phasediff.nii.gz')
        }
        select_files = Node(SelectFiles(file_templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.dataset_dir

        # DataSink Node - store the wanted results in the wanted directory
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir

        # FAST Node - Bias field correction on anatomical images
        bias_field_correction = Node(FAST(), name = 'bias_field_correction')
        bias_field_correction.inputs.img_type = 1 # T1 image
        bias_field_correction.inputs.output_biascorrected = True

        # BET Node - Brain extraction for anatomical images
        brain_extraction_anat = Node(BET(), name = 'brain_extraction_anat')
        brain_extraction_anat.inputs.frac = 0.5
        #brain_extraction_anat.inputs.mask = True # TODO ?

        # FAST Node - Segmentation of anatomical images
        segmentation_anat = Node(FAST(), name = 'segmentation_anat')
        segmentation_anat.inputs.no_bias = True # Bias field was already removed
        segmentation_anat.inputs.segments = False # Only output partial volume estimation
        segmentation_anat.inputs.probability_maps = False # Only output partial volume estimation

        # Split Node - Split probability maps as they output from the segmentation node
        split_segmentation_maps = Node(Split(), name = 'split_segmentation_maps')
        split_segmentation_maps.inputs.splits = [1, 1, 1]
        split_segmentation_maps.inputs.squeeze = True # Unfold one-element splits removing the list

        # ANTs Node - Normalization of anatomical images to T1 MNI152 space
        #   https://github.com/ANTsX/ANTs/wiki/Anatomy-of-an-antsRegistration-call
        normalization_anat = Node(Registration(), name = 'normalization_anat')
        normalization_anat.inputs.fixed_image = Info.standard_image('MNI152_T1_2mm_brain.nii.gz')
        normalization_anat.inputs.collapse_output_transforms = True
        normalization_anat.inputs.convergence_threshold = [1e-06]
        normalization_anat.inputs.convergence_window_size = [10]
        normalization_anat.inputs.dimension = 3
        normalization_anat.inputs.initial_moving_transform_com = True
        normalization_anat.inputs.radius_or_number_of_bins = [32, 32, 4]
        normalization_anat.inputs.sampling_percentage = [0.25, 0.25, 1]
        normalization_anat.inputs.sampling_strategy = ['Regular', 'Regular', 'None']
        normalization_anat.inputs.transforms = ['Rigid', 'Affine', 'SyN']
        normalization_anat.inputs.metric = ['MI', 'MI', 'CC']
        normalization_anat.inputs.transform_parameters = [(0.1,), (0.1,), (0.1, 3.0, 0.0)]
        normalization_anat.inputs.metric_weight = [1.0]*3
        normalization_anat.inputs.shrink_factors = [[8, 4, 2, 1]]*3
        normalization_anat.inputs.smoothing_sigmas = [[3, 2, 1, 0]]*3
        normalization_anat.inputs.sigma_units = ['vox']*3
        normalization_anat.inputs.number_of_iterations = [
            [1000, 500, 250, 100],
            [1000, 500, 250, 100],
            [100, 70, 50, 20]
            ]
        normalization_anat.inputs.use_histogram_matching = True
        normalization_anat.inputs.winsorize_lower_quantile = 0.005
        normalization_anat.inputs.winsorize_upper_quantile = 0.995

        # Threshold Node - create white-matter mask
        threshold_white_matter = Node(Threshold(), name = 'threshold_white_matter')
        threshold_white_matter.inputs.thresh = 1

        # Threshold Node - create CSF mask
        threshold_csf = Node(Threshold(), name = 'threshold_csf')
        threshold_csf.inputs.thresh = 1

        # ErodeImage Node - Erode white-matter mask
        erode_white_matter = Node(ErodeImage(), name = 'erode_white_matter')
        erode_white_matter.inputs.kernel_shape = 'sphere'
        erode_white_matter.inputs.kernel_size = 2.0 #mm

        # ErodeImage Node - Erode CSF mask
        erode_csf = Node(ErodeImage(), name = 'erode_csf')
        erode_csf.inputs.kernel_shape = 'sphere'
        erode_csf.inputs.kernel_size = 1.5 #mm

        # BET Node - Brain extraction of magnitude images
        brain_extraction_magnitude = Node(BET(), name = 'brain_extraction_magnitude')
        brain_extraction_magnitude.inputs.frac = 0.5

        # PrepareFieldmap Node - Convert phase and magnitude to fieldmap images
        convert_to_fieldmap = Node(PrepareFieldmap(), name = 'convert_to_fieldmap')

        # FLIRT Node - Align high contrast functional images to anatomical
        #   (i.e.: single-band reference images a.k.a. sbref)
        coregistration_sbref = Node(FLIRT(), name = 'coregistration_sbref')
        coregistration_sbref.inputs.interp = 'trilinear'
        coregistration_sbref.inputs.cost = 'bbr' # boundary-based registration

        # ConvertXFM Node - Inverse coregistration transform, to get anat to func transform
        inverse_func_to_anat = Node(ConvertXFM(), name = 'inverse_func_to_anat')
        inverse_func_to_anat.inputs.invert_xfm = True

        # BET Node - Brain extraction for functional images
        brain_extraction_func = Node(BET(), name = 'brain_extraction_func')
        brain_extraction_func.inputs.frac = 0.3
        brain_extraction_func.inputs.mask = True
        brain_extraction_func.inputs.functional = True

        # MCFLIRT Node - Motion correction of functional images
        motion_correction = Node(MCFLIRT(), name = 'motion_correction')
        motion_correction.inputs.cost = 'normcorr'
        motion_correction.inputs.interpolation = 'spline' # should be 'trilinear'
        motion_correction.inputs.save_plots = True # Save transformation parameters

        # SliceTimer Node - Slice time correction
        slice_time_correction = Node(SliceTimer(), name = 'slice_time_correction')
        slice_time_correction.inputs.time_repetition = TaskInformation()['RepetitionTime']

        # SUSAN Node - smoothing of functional images
        smoothing = Node(SUSAN(), name = 'smoothing')
        smoothing.inputs.brightness_threshold = 2000.0 # TODO : which value ?
        smoothing.inputs.fwhm = self.fwhm

        # ApplyXFM Node - Alignment of white matter to functional space
        alignment_white_matter = Node(ApplyXFM(), name = 'alignment_white_matter')
        alignment_white_matter.inputs.apply_xfm = True

        # ApplyXFM Node - Alignment of CSF to functional space
        alignment_csf = Node(ApplyXFM(), name = 'alignment_csf')
        alignment_csf.inputs.apply_xfm = True

        # ApplyWarp Node - Alignment of functional data to anatomical space
        alignment_func_to_anat = Node(ApplyXFM(), name = 'alignment_func_to_anat')
        alignment_func_to_anat.inputs.apply_xfm = True

        # ApplyWarp Node - Alignment of functional data to MNI space
        alignment_func_to_mni = Node(ApplyTransforms(), name = 'alignment_func_to_mni')
        alignment_func_to_mni.inputs.reference_image = \
            Info.standard_image('MNI152_T1_2mm_brain.nii.gz')

        # Merge Node - Merge the two masks (WM and CSF) in one input for the next node
        merge_masks = Node(Merge(2), name = 'merge_masks')

        # CompCor Node - Compute anatomical confounds (regressors of no interest in the model)
        #   from the WM and CSF masks
        compute_confounds = Node(CompCor(), name = 'compute_confounds')
        compute_confounds.inputs.num_components = 4
        compute_confounds.inputs.merge_method = 'union'
        compute_confounds.inputs.repetition_time = TaskInformation()['RepetitionTime']

        preprocessing = Workflow(base_dir = self.directories.working_dir, name = 'preprocessing')
        preprocessing.connect([
            # Inputs
            (info_source, select_files, [('subject_id', 'subject_id'), ('run_id', 'run_id')]),

            # Anatomical images
            (select_files, bias_field_correction, [('anat', 'in_files')]),
            (bias_field_correction, brain_extraction_anat, [('restored_image', 'in_file')]),
            (brain_extraction_anat, segmentation_anat, [('out_file', 'in_files')]),
            (brain_extraction_anat, normalization_anat, [('out_file', 'moving_image')]),
            (segmentation_anat, split_segmentation_maps, [('partial_volume_files', 'inlist')]),
            (split_segmentation_maps, threshold_white_matter, [('out2', 'in_file')]),
            (split_segmentation_maps, threshold_csf, [('out1', 'in_file')]),
            (threshold_white_matter, erode_white_matter, [('out_file', 'in_file')]),
            (threshold_csf, erode_csf, [('out_file', 'in_file')]),
            (erode_white_matter, alignment_white_matter, [('out_file', 'in_file')]),
            (inverse_func_to_anat, alignment_white_matter, [('out_file', 'in_matrix_file')]),
            (select_files, alignment_white_matter, [('sbref', 'reference')]),
            (erode_csf, alignment_csf, [('out_file', 'in_file')]),
            (inverse_func_to_anat, alignment_csf, [('out_file', 'in_matrix_file')]),
            (select_files, alignment_csf, [('sbref', 'reference')]),
            (alignment_csf, merge_masks, [('out_file', 'in1')]),
            (alignment_white_matter, merge_masks, [('out_file', 'in2')]),

            # Field maps
            (select_files, brain_extraction_magnitude, [('magnitude', 'in_file')]),
            (brain_extraction_magnitude, convert_to_fieldmap, [('out_file', 'in_magnitude')]),
            (select_files, convert_to_fieldmap, [('phasediff', 'in_phase')]),

            # High contrast functional volume
            (select_files, coregistration_sbref, [('sbref', 'in_file')]),
            (select_files, coregistration_sbref, [('anat', 'reference')]),
            (convert_to_fieldmap, coregistration_sbref, [('out_fieldmap', 'fieldmap')]),
            (coregistration_sbref, inverse_func_to_anat, [('out_matrix_file', 'in_file')]),

            # Functional images
            (select_files, brain_extraction_func, [('func', 'in_file')]),
            (brain_extraction_func, motion_correction, [('out_file', 'in_file')]),
            (select_files, motion_correction, [('sbref', 'ref_file')]),
            (motion_correction, slice_time_correction, [('out_file', 'in_file')]),
            (slice_time_correction, smoothing, [('slice_time_corrected_file', 'in_file')]),
            (smoothing, alignment_func_to_anat, [('smoothed_file', 'in_file')]),
            (coregistration_sbref, alignment_func_to_anat, [('out_matrix_file', 'in_matrix_file')]),
            (brain_extraction_anat, alignment_func_to_anat, [('out_file', 'reference')]),
            (alignment_func_to_anat, alignment_func_to_mni, [('out_file', 'input_image')]),
            (normalization_anat, alignment_func_to_mni, [('forward_transforms', 'transforms')]),
            (merge_masks, compute_confounds, [('out', 'mask_files')]), # Masks are in the func space
            (slice_time_correction, compute_confounds, [('slice_time_corrected_file', 'realigned_file')]),

            # Outputs of preprocessing
            (motion_correction, data_sink, [('par_file', 'preprocessing.@par_file')]),
            (compute_confounds, data_sink, [('components_file', 'preprocessing.@components_file')]),
            (alignment_func_to_mni, data_sink, [('output_image', 'preprocessing.@output_image')])
        ])

        return preprocessing

    def get_preprocessing_outputs(self):
        """ Return a list of the files generated by the preprocessing """

        parameters = {
            'subject_id': self.subject_list,
            'run_id': self.run_list,
            'file': [
                'components_file.txt',
                'sub-{subject_id}_task-MGT_run-{run_id}_bold_brain_mcf.nii.gz.par',
                'sub-{subject_id}_task-MGT_run-{run_id}_bold_brain_mcf_st_smooth_flirt_trans.nii.gz'
            ]
        }
        parameter_sets = product(*parameters.values())
        template = join(
            self.directories.output_dir,
            'preprocessing',
            '_run_id_{run_id}_subject_id_{subject_id}',
            '{file}'
            )

        return [template.format(**dict(zip(parameters.keys(), parameter_values)))\
            for parameter_values in parameter_sets]

    def get_session_information(event_file):
        """
        Extract information from an event file, to setup the model. 4 regressors are extracted :
        - event: a regressor with 4 second ON duration
        - gain : a parametric modulation of events corresponding to gain magnitude. Mean centred.
        - loss : a parametric modulation of events corresponding to loss magnitude. Mean centred.
        - response : a regressor with 1 for accept and -1 for reject. Mean centred.

        Parameters :
        - event_file : str, event file corresponding to the run and the subject to analyze

        Returns :
        - subject_info : list of Bunch containing event information
        """
        from nipype.interfaces.base import Bunch

        condition_names = ['event', 'gain', 'loss', 'response']
        onsets = {}
        durations = {}
        amplitudes = {}

        # Create dictionary items with empty lists
        for condition in condition_names:
            onsets.update({condition : []})
            durations.update({condition : []})
            amplitudes.update({condition : []})

        # Parse information in the event_file
        with open(event_file, 'rt') as file:
            next(file)  # skip the header

            for line in file:
                info = line.strip().split()

                for condition in condition_names:
                    if condition == 'gain':
                        onsets[condition].append(float(info[0]))
                        durations[condition].append(float(info[4])) # TODO : change to info[1] (= 4) ?
                        amplitudes[condition].append(float(info[2]))
                    elif condition == 'loss':
                        onsets[condition].append(float(info[0]))
                        durations[condition].append(float(info[4])) # TODO : change to info[1] (= 4) ?
                        amplitudes[condition].append(float(info[3]))
                    elif condition == 'event':
                        onsets[condition].append(float(info[0]))
                        durations[condition].append(float(info[1]))
                        amplitudes[condition].append(1.0)
                    elif condition == 'response':
                        onsets[condition].append(float(info[0]))
                        durations[condition].append(float(info[1])) # TODO : change to info[4] (= RT) ?
                        if 'accept' in info[5]:
                            amplitudes[condition].append(1.0)
                        elif 'reject' in info[5]:
                            amplitudes[condition].append(-1.0)
                        else:
                            amplitudes[condition].append(0.0)

        return [
            Bunch(
                conditions = condition_names,
                onsets = [onsets[k] for k in condition_names],
                durations = [durations[k] for k in condition_names],
                amplitudes = [amplitudes[k] for k in condition_names],
                regressor_names = None,
                regressors = None)
            ]

    def get_run_level_contrasts():
        """
        Create a list of tuples that represent contrasts.
        Each contrast is in the form :
        (Name,Stat,[list of condition names],[weights on those conditions])

        Returns:
            - contrasts: list of tuples, list of contrasts to analyze
        """
        # List of condition names
        conditions = ['gain', 'loss']

        # Return contrast list
        return [
            # Positive parametric effect of gain
            ('positive_effect_gain', 'T', conditions, [1, 0]),
            # Positive parametric effect of loss
            ('positive_effect_loss', 'T', conditions, [0, 1]),
            # Negative parametric effect of loss.
            ('negative_effect_loss', 'T', conditions, [0, -1])
        ]

    def get_run_level_analysis(self):
        """ Return a Nipype workflow describing the run level analysis part of the pipeline

        Returns:
            - run_level_analysis : nipype.WorkFlow
        """

        # IdentityInterface node - allows to iterate over subjects and runs
        info_source = Node(IdentityInterface(
            fields = ['subject_id', 'run_id']),
            name = 'info_source')
        info_source.iterables = [
            ('run_id', self.run_list),
            ('subject_id', self.subject_list),
        ]

        # SelectFiles node - to select necessary files
        templates = {
            # Functional MRI
            'func' : join(self.directories.output_dir, 'preprocessing',
                '_run_id_{run_id}_subject_id_{subject_id}',
                'sub-{subject_id}_task-MGT_run-{run_id}_bold_brain_mcf_st_smooth_flirt_trans.nii.gz'
                ),
            # Event file
            'event' : join('sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-{run_id}_events.tsv'
                ),
            # Motion parameters
            'motion' : join(self.directories.output_dir, 'preprocessing',
                '_run_id_{run_id}_subject_id_{subject_id}',
                'sub-{subject_id}_task-MGT_run-{run_id}_bold_brain_mcf.nii.gz.par',
                )
        }
        select_files = Node(SelectFiles(templates), name = 'selectfiles')
        select_files.inputs.base_directory = self.directories.dataset_dir

        # DataSink Node - store the wanted results in the wanted directory
        data_sink = Node(DataSink(), name='datasink')
        data_sink.inputs.base_directory = self.directories.output_dir

        # Function Node get_session_information - Get subject information from event files
        session_information = Node(Function(
            input_names = ['event_file'],
            output_names = ['session_information']
            ), name = 'session_information')
        session_information.inputs.function = self.get_session_information

        # SpecifyModel - Generates a model
        specify_model = Node(SpecifyModel(), name = 'specify_model')
        specify_model.inputs.high_pass_filter_cutoff = 90
        specify_model.inputs.input_units = 'secs'
        specify_model.inputs.time_repetition = TaskInformation()['RepetitionTime']
        specify_model.inputs.parameter_source = 'FSL' # Source of motion parameters.

        # Function Node get_contrasts - Get the list of contrasts
        contrasts = Node(Function(
            input_names = [],
            output_names = ['contrasts']
            ), name = 'contrasts')
        contrasts.inputs.function = self.get_run_level_contrasts

        # Level1Design Node - Generate files for first level computation
        l1_design = Node(Level1Design(), 'l1_design')
        l1_design.inputs.bases = {
            'dgamma':{'derivs' : True} # Canonical double gamma HRF plus temporal derivative
            }
        l1_design.inputs.interscan_interval = TaskInformation()['RepetitionTime']
        l1_design.inputs.model_serial_correlations = True

        # FEATModel Node - Generate first level model
        model_generation = Node(FEATModel(), name = 'model_generation')

        # FILMGLS Node - Estimate first level model
        model_estimate = Node(FILMGLS(), name = 'model_estimate')

        # Create l1 analysis workflow and connect its nodes
        run_level_analysis = Workflow(
            base_dir = self.directories.working_dir,
            name = 'run_level_analysis'
            )
        run_level_analysis.connect([
            (info_source, select_files, [('subject_id', 'subject_id'), ('run_id', 'run_id')]),
            (select_files, session_information, [('event', 'event_file')]),
            (session_information, specify_model, [('subject_info', 'subject_info')]),
            (select_files, specify_model, [('motion', 'realignment_parameters')]),
            (select_files, specify_model, [('func', 'functional_runs')]),
            (contrasts, l1_design, [('contrasts', 'contrasts')]),
            (specify_model, l1_design, [('session_info', 'session_info')]),
            (l1_design, model_generation, [
                ('ev_files', 'ev_files'),
                ('fsf_files', 'fsf_file')]),
            (select_files, model_estimate, [('func', 'in_file')]),
            (model_generation, model_estimate, [
                ('con_file', 'tcon_file'),
                ('design_file', 'design_file')]),
            (model_estimate, data_sink, [('results_dir', 'run_level_analysis.@results')]),
            (model_generation, data_sink, [
                ('design_file', 'run_level_analysis.@design_file'),
                ('design_image', 'run_level_analysis.@design_img')]),
            ])

        return run_level_analysis

    def get_run_level_outputs(self):
        """ Return a list of the files generated by the run level analysis """

        parameters = {
            'run_id' : self.run_list,
            'subject_id' : self.subject_list,
            'file' : [
                'run0.mat',
                'run0.png'
            ]
        }
        parameter_sets = product(*parameters.values())
        template = join(
            self.directories.output_dir,
            'l1_analysis', '_run_id_{run_id}_subject_id_{subject_id}','{file}'
            )
        return_list = [template.format(**dict(zip(parameters.keys(), parameter_values)))\
            for parameter_values in parameter_sets]

        parameters = {
            'run_id' : self.run_list,
            'subject_id' : self.subject_list,
            'contrast_id' : self.contrast_list,
            'file' : [
                join('results', 'cope{contrast_id}.nii.gz'),
                join('results', 'tstat{contrast_id}.nii.gz'),
                join('results', 'varcope{contrast_id}.nii.gz'),
                join('results', 'zstat{contrast_id}.nii.gz'),
            ]
        }
        parameter_sets = product(*parameters.values())
        template = join(
            self.directories.output_dir,
            'l1_analysis', '_run_id_{run_id}_subject_id_{subject_id}','{file}'
            )

        return_list += [template.format(**dict(zip(parameters.keys(), parameter_values)))\
            for parameter_values in parameter_sets]

        return return_list
    """
    Group level
    Ordinary least squares. Pooled variance.

    Second level
    Positive one-sample ttest over first level contrast estimates.

    Group level
    Group effect for each first level contrast for each of the two groups.
    Contrast of positive parametric effect of loss, testing for equal range group responses being greater than equal indifference group.

    TFCE

    pval_computation : Permutation testing implemented in randomise (10,000 permutations).
    multiple_testing_correction : FWE permutation (10,000 permutations).
    comments_analysis : NA
    """

    def get_subject_level_analysis(self):
        """ Return a Nipype workflow describing the subject level analysis part of the pipeline """

        subject_level_analysis = Workflow(
            base_dir = self.directories.working_dir,
            name = 'subject_level_analysis'
        )
        return subject_level_analysis

    def get_subject_level_outputs(self):
        """ Return a list of the files generated by the subject level analysis """
        return ['fake_file']

    def get_subgroups_contrasts(
        copes, varcopes, subject_list: list, participants_file: str
    ):
        """
        This function return the file list containing only the files
        belonging to subject in the wanted group.

        Parameters :
        - copes: original file list selected by select_files node
        - varcopes: original file list selected by select_files node
        - subject_ids: list of subject IDs that are analyzed
        - participants_file: file containing participants characteristics

        Returns :
        - copes_equal_indifference : a subset of copes corresponding to subjects
        in the equalIndifference group
        - copes_equal_range : a subset of copes corresponding to subjects
        in the equalRange group
        - copes_global : a list of all copes
        - varcopes_equal_indifference : a subset of varcopes corresponding to subjects
        in the equalIndifference group
        - varcopes_equal_range : a subset of varcopes corresponding to subjects
        in the equalRange group
        - equal_indifference_id : a list of subject ids in the equalIndifference group
        - equal_range_id : a list of subject ids in the equalRange group
        - varcopes_global : a list of all varcopes
        """

        equal_range_id = []
        equal_indifference_id = []

        # Reading file containing participants IDs and groups
        with open(participants_file, 'rt') as file:
            next(file)  # skip the header

            for line in file:
                info = line.strip().split()

                # Checking for each participant if its ID was selected
                # and separate people depending on their group
                if info[0][-3:] in subject_list and info[1] == 'equalIndifference':
                    equal_indifference_id.append(info[0][-3:])
                elif info[0][-3:] in subject_list and info[1] == 'equalRange':
                    equal_range_id.append(info[0][-3:])

        copes_equal_indifference = []
        copes_equal_range = []
        copes_global = []
        varcopes_equal_indifference = []
        varcopes_equal_range = []
        varcopes_global = []

        # Checking for each selected file if the corresponding participant was selected
        # and add the file to the list corresponding to its group
        for cope, varcope in zip(copes, varcopes):
            sub_id = cope.split('/')
            if sub_id[-2][-3:] in equal_indifference_id:
                copes_equal_indifference.append(cope)
            elif sub_id[-2][-3:] in equal_range_id:
                copes_equal_range.append(cope)
            if sub_id[-2][-3:] in subject_list:
                copes_global.append(cope)

            sub_id = varcope.split('/')
            if sub_id[-2][-3:] in equal_indifference_id:
                varcopes_equal_indifference.append(varcope)
            elif sub_id[-2][-3:] in equal_range_id:
                varcopes_equal_range.append(varcope)
            if sub_id[-2][-3:] in subject_list:
                varcopes_global.append(varcope)

        return (copes_equal_indifference, copes_equal_range,
            varcopes_equal_indifference, varcopes_equal_range,
            equal_indifference_id, equal_range_id,
            copes_global, varcopes_global)

    def get_regressors(
        equal_range_id: list,
        equal_indifference_id: list,
        method: str,
        subject_list: list,
    ) -> dict:
        """
        Create dictionary of regressors for group analysis.

        Parameters:
            - equal_range_id: ids of subjects in equal range group
            - equal_indifference_id: ids of subjects in equal indifference group
            - method: one of "equalRange", "equalIndifference" or "groupComp"
            - subject_list: ids of subject for which to do the analysis

        Returns:
            - regressors: regressors used to distinguish groups in FSL group analysis
        """
        # For one sample t-test, creates a dictionary
        # with a list of the size of the number of participants
        if method == 'equalRange':
            regressors = dict(group_mean = [1 for i in range(len(equal_range_id))])
        elif method == 'equalIndifference':
            regressors = dict(group_mean = [1 for i in range(len(equal_indifference_id))])

        # For two sample t-test, creates 2 lists:
        #  - one for equal range group,
        #  - one for equal indifference group
        # Each list contains n_sub values with 0 and 1 depending on the group of the participant
        # For equalRange_reg list --> participants with a 1 are in the equal range group
        elif method == 'groupComp':
            equal_range_regressors = [
                1 for i in range(len(equal_range_id) + len(equal_indifference_id))
            ]
            equal_indifference_regressors = [
                0 for i in range(len(equal_range_id) + len(equal_indifference_id))
            ]

            for index, subject_id in enumerate(subject_list):
                if subject_id in equal_indifference_id:
                    equal_indifference_regressors[index] = 1
                    equal_range_regressors[index] = 0

            regressors = dict(
                equalRange = equal_range_regressors,
                equalIndifference = equal_indifference_regressors
            )

        return regressors

    def get_group_level_analysis(self):
        """
        Return all workflows for the group level analysis.

        Returns;
            - a list of nipype.WorkFlow
        """
        return None

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
        # [INFO] The following part stays the same for all preprocessing pipelines

        # Infosource node - iterate over the list of contrasts generated
        # by the subject level analysis
        info_source = Node(
            IdentityInterface(
                fields = ['contrast_id', 'subjects'],
                subjects = self.subject_list
            ),
            name = 'info_source',
        )
        info_source.iterables = [('contrast_id', self.contrast_list)]

        # Templates to select files node
        # [TODO] Change the name of the files depending on the filenames
        # of results of first level analysis
        templates = {
            'cope' : join(self.directories.output_dir,
                'subject_level_analysis',
                '_contrast_id_{contrast_id}_subject_id_*', 'cope1.nii.gz'),
            'varcope' : join(
                self.directories.output_dir,
                'subject_level_analysis',
                '_contrast_id_{contrast_id}_subject_id_*', 'varcope1.nii.gz'),
            'participants' : join(
                self.directories.dataset_dir,
                'participants.tsv')
        }
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.dataset_dir
        select_files.inputs.force_list = True

        # Datasink node - to save important files
        data_sink = Node(
            DataSink(base_directory = self.directories.output_dir),
            name = 'data_sink',
        )

        subgroups_contrasts = Node(Function(
            function = self.get_subgroups_contrasts,
            input_names=['copes', 'varcopes', 'subject_ids', 'participants_file'],
            output_names=[
                'copes_equalIndifference',
                'copes_equalRange',
                'varcopes_equalIndifference',
                'varcopes_equalRange',
                'equalIndifference_id',
                'equalRange_id',
                'copes_global',
                'varcopes_global'
                ]
            ),
            name = 'subgroups_contrasts',
        )

        regressors = Node(Function(
            function = self.get_regressors,
            input_names = [
                'equalRange_id',
                'equalIndifference_id',
                'method',
                'subject_list',
                ],
            output_names = ['regressors']
            ),
            name = 'regressors',
        )
        regressors.inputs.method = method
        regressors.inputs.subject_list = self.subject_list

        # Compute the number of participants used to do the analysis
        nb_subjects = len(self.subject_list)

        # Declare the workflow
        group_level_analysis = Workflow(
            base_dir = self.directories.working_dir,
            name = f'group_level_analysis_{method}_nsub_{nb_subjects}'
        )
        group_level_analysis.connect([
            (info_source, select_files, [('contrast_id', 'contrast_id')])
        ])

        # [INFO] Here we define the contrasts used for the group level analysis, depending on the
        # method used.
        if method in ('equalRange', 'equalIndifference'):
            contrasts = [('Group', 'T', ['mean'], [1]), ('Group', 'T', ['mean'], [-1])]

        elif method == 'groupComp':
            contrasts = [
                ('Eq range vs Eq indiff in loss', 'T', ['Group_{1}', 'Group_{2}'], [1, -1])
            ]

        # [INFO] Here we simply return the created workflow
        return group_level_analysis

    def get_group_level_outputs(self):
        """ Return a list of the files generated by the group level analysis """
        return ['fake_file']

    def get_hypotheses_outputs(self):
        """ Return the names of the files used by the team to answer the hypotheses of NARPS. """

        nb_sub = len(self.subject_list)
        files = [
            join(f'l3_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_pgain', 'randomise_tfce_corrp_tstat1.nii.gz'),
            join(f'l3_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_pgain', 'zstat1.nii.gz'),
            join(f'l3_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_pgain', 'randomise_tfce_corrp_tstat1.nii.gz'),
            join(f'l3_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_pgain', 'zstat1.nii.gz'),
            join(f'l3_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_pgain', 'randomise_tfce_corrp_tstat1.nii.gz'),
            join(f'l3_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_pgain', 'zstat1.nii.gz'),
            join(f'l3_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_pgain', 'randomise_tfce_corrp_tstat1.nii.gz'),
            join(f'l3_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_pgain', 'zstat1.nii.gz'),
            join(f'l3_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_ploss', 'randomise_tfce_corrp_tstat2.nii.gz'),
            join(f'l3_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_ploss', 'zstat2.nii.gz'),
            join(f'l3_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_ploss', 'randomise_tfce_corrp_tstat2.nii.gz'),
            join(f'l3_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_ploss', 'zstat2.nii.gz'),
            join(f'l3_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_ploss', 'randomise_tfce_corrp_tstat1.nii.gz'),
            join(f'l3_analysis_equalIndifference_nsub_{nb_sub}',
                '_contrast_id_ploss', 'zstat1.nii.gz'),
            join(f'l3_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_ploss', 'randomise_tfce_corrp_tstat1.nii.gz'),
            join(f'l3_analysis_equalRange_nsub_{nb_sub}',
                '_contrast_id_ploss', 'zstat1.nii.gz'),
            join(f'l3_analysis_groupComp_nsub_{nb_sub}',
                '_contrast_id_ploss', 'randomise_tfce_corrp_tstat1.nii.gz'),
            join(f'l3_analysis_groupComp_nsub_{nb_sub}',
                '_contrast_id_ploss', 'zstat1.nii.gz')
        ]
        return [join(self.directories.output_dir, f) for f in files]
