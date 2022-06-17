

from nipype.interfaces.spm import node_function # Complete with necessary functions
from nipype.interfaces.fsl import node_function # Complete with necessary functions
from nipype.algorithms.modelgen import SpecifySPMModel, SpecifyModel # Functions used during L1 analysis
from nipype.interfaces.utility import IdentityInterface, Function
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.algorithms.misc import Gunzip
from nipype import Workflow, Node, MapNode, JoinNode
from nipype.interfaces.base import Bunch

from os.path import join as opj
import os
import json

def get_preprocessing(exp_dir, result_dir, working_dir, output_dir, subject_list, run_list, fwhm):
    """
    Returns the preprocessing workflow.

    Parameters: 
        - exp_dir: str, directory where raw data are stored
        - result_dir: str, directory where results will be stored
        - working_dir: str, name of the sub-directory for intermediate results
        - output_dir: str, name of the sub-directory for final results
        - subject_list: list of str, list of subject for which you want to do the preprocessing
        - run_list: list of str, list of runs for which you want to do the preprocessing 
        - fwhm: float, fwhm for smoothing step
        
    Returns: 
        - preprocessing: Nipype WorkFlow 
    """

    # THE FOLLOWING PART STAYS THE SAME FOR ALL PREPROCESSING PIPELINES 
    infosource_preproc = Node(IdentityInterface(fields = ['subject_id', 'run_id']), 
        name = 'infosource_preproc')

    infosource_preproc.iterables = [('subject_id', subject_list), ('run_id', run_list)] # Iterates over subject and runs 

    # Templates to select files node
    anat_file = opj('sub-{subject_id}', 'anat', 
                    'sub-{subject_id}_T1w.nii.gz')

    func_file = opj('sub-{subject_id}', 'func', 
                    'sub-{subject_id}_task-MGT_run-{run_id}_bold.nii.gz')

    magnitude_file = opj('sub-{subject_id}', 'fmap', 'sub-{subject_id}_magnitude1.nii.gz')

    phasediff_file = opj('sub-{subject_id}', 'fmap', 'sub-{subject_id}_phasediff.nii.gz')

    template = {'anat' : anat_file, 'func' : func_file, 'magnitude' : magnitude_file, 'phasediff' : phasediff_file}

    # SelectFiles node - to select necessary files
    selectfiles_preproc = Node(SelectFiles(template, base_directory=exp_dir), name = 'selectfiles_preproc')

    # DataSink Node - store the wanted results in the wanted repository
    datasink_preproc = Node(DataSink(base_directory=result_dir, container=output_dir), name='datasink_preproc')

    # THE FOLLOWING PART HAS TO BE MODIFIED WITH NODES OF THE PIPELINE
    node_variable = Node(node_function, name = 'node_name') # Replace with the name of the node_variable, 
    # the node_function to use in the NiPype interface,
    # and the name of the node (recommanded to be the same as node_variable)

    # ADD OTHER NODES WITH THE DIFFERENT STEPS OF THE PIPELINE

    preprocessing =  Workflow(base_dir = opj(result_dir, working_dir), name = "preprocessing") # Workflow creation

    preprocessing.connect([(infosource_preproc, selectfiles_preproc, [('subject_id', 'subject_id'),
                                                                     ('run_id', 'run_id')]), 
                           (selectfiles_preproc, node_variable [('func', 'node_input_name')]), # Complete with name of node to link with and the name of the input 
                           # Input and output names can be found on NiPype documentation
                           (node_variable, datasink_preproc, [('node_output_name', 'preprocess.@sym_link')])]) 
    
    return preprocessing    

# THIS FUNCTION IS USED IN THE FIRST LEVEL ANALYSIS PIPELINES OF SPM 
# THIS IS AN EXAMPLE THAT IS ADAPTED TO A SPECIFIC PIPELINE 
# MODIFY ACCORDING TO THE PIPELINE YOU WANT TO REPRODUCE
def get_subject_infos_spm(event_files, runs):
    '''

    The model contained 6 regressors per run:
    - One predictor with onset at the start of the trial and duration of 4s.
    - Two parametric modulators (one for gains, one for losses) were added to the trial onset predictor. 
    The two parametric modulators were orthogonalized w.r.t. the main predictor, but were not orthogonalized w.r.t. one another.
    - Two predictors modelling the decision output, one for accepting the gamble and one for rejecting it 
    (merging strong and weak decisions). 
    The onset was defined as the beginning of the trial + RT and the duration was set to 0 (stick function).
    - One constant term for each run was included (SPM12 default design).
    
    Create Bunchs for specifySPMModel.

    Parameters :
    - event_files: list of str, list of events files (one per run) for the subject
    - runs: list of str, list of runs to use
    
    Returns :
    - subject_info : list of Bunch for 1st level analysis.
    '''
    from nipype.interfaces.base import Bunch
    
    cond_names = ['trial', 'accepting', 'rejecting']
    onset = {}
    duration = {}
    weights_gain = {}
    weights_loss = {}
    onset_button = {}
    duration_button = {}
    
    for r in range(len(runs)):  # Loop over number of runs.
        onset.update({s + '_run' + str(r+1) : [] for s in cond_names}) # creates dictionary items with empty lists
        duration.update({s + '_run' + str(r+1) : [] for s in cond_names}) 
        weights_gain.update({'gain_run' + str(r+1) : []})
        weights_loss.update({'loss_run' + str(r+1) : []})
    
    for r, run in enumerate(runs):
        
        f_events = event_files[r]
        
        with open(f_events, 'rt') as f:
            next(f)  # skip the header
            
            for line in f:
                info = line.strip().split()
                
                for cond in cond_names:
                    val = cond + '_run' + str(r+1) # trial_run1 or accepting_run1
                    val_gain = 'gain_run' + str(r+1) # gain_run1
                    val_loss = 'loss_run' + str(r+1) # loss_run1
                    if cond == 'trial':
                        onset[val].append(float(info[0])) # onsets for trial_run1 
                        duration[val].append(float(4))
                        weights_gain[val_gain].append(float(info[2])) # weights gain for trial_run1
                        weights_loss[val_loss].append(float(info[3])) # weights loss for trial_run1
                    elif cond == 'accepting' and 'accept' in info[5]:
                        onset[val].append(float(info[0]) + float(info[4]))
                        duration[val].append(float(0))
                    elif cond == 'rejecting' and 'reject' in info[5]:
                        onset[val].append(float(info[0]) + float(info[4]))
                        duration[val].append(float(0))
                    

    # Bunching is done per run, i.e. trial_run1, trial_run2, etc.
    # But names must not have '_run1' etc because we concatenate runs 
    subject_info = []
    for r in range(len(runs)):

        cond = [s + '_run' + str(r+1) for s in cond_names]
        gain = 'gain_run' + str(r+1)
        loss = 'loss_run' + str(r+1)

        subject_info.insert(r,
                           Bunch(conditions=cond_names,
                                 onsets=[onset[c] for c in cond],
                                 durations=[duration[c] for c in cond],
                                 amplitudes=None,
                                 tmod=None,
                                 pmod=[Bunch(name=['gain', 'loss'],
                                             poly=[1, 1],
                                             param=[weights_gain[gain],
                                                    weights_loss[loss]]), None],
                                 regressor_names=None,
                                 regressors=None))

    return subject_info

# THIS FUNCTION IS USED IN THE FIRST LEVEL ANALYSIS PIPELINES OF FSL
# THIS IS AN EXAMPLE THAT IS ADAPTED TO A SPECIFIC PIPELINE 
# MODIFY ACCORDING TO THE PIPELINE YOU WANT TO REPRODUCE
def get_session_infos_fsl(event_file):
    '''
    Create Bunchs for specifyModel.
    
    Parameters :
    - event_file : str, file corresponding to the run and the subject to analyze
    
    Returns :
    - subject_info : list of Bunch for 1st level analysis.
    '''
    from os.path import join as opj
    from nipype.interfaces.base import Bunch
    import numpy as np
    
    cond_names = ['trial', 'gain', 'loss']
    
    onset = {}
    duration = {}
    amplitude = {}
    
    for c in cond_names:  # For each condition.
        onset.update({c : []}) # creates dictionary items with empty lists
        duration.update({c : []}) 
        amplitude.update({c : []})

    with open(event_file, 'rt') as f:
        next(f)  # skip the header

        for line in f:
            info = line.strip().split()
            # Creates list with onsets, duration and loss/gain for amplitude (FSL)
            for c in cond_names:
                if c == 'gain':
                    onset[c].append(float(info[0]))
                    duration[c].append(float(info[4]))
                    amplitude[c].append(float(info[2]))
                elif c == 'loss':
                    onset[c].append(float(info[0]))
                    duration[c].append(float(info[4]))
                    amplitude[c].append(float(info[3]))
                elif c == 'trial':
                    onset[c].append(float(info[0]))
                    duration[c].append(float(info[4]))
                    amplitude[c].append(float(1)) 


    
    subject_info = []

    subject_info.append(Bunch(conditions=cond_names,
                             onsets=[onset[k] for k in cond_names],
                             durations=[duration[k] for k in cond_names],
                             amplitudes=[amplitude[k] for k in cond_names],
                             regressor_names=None,
                             regressors=None))

    return subject_info

# THIS FUNCTION CREATES THE CONTRASTS THAT WILL BE ANALYZED IN THE FIRST LEVEL ANALYSIS
# IT IS ADAPTED FOR A SPECIFIC PIPELINE AND SHOULD BE MODIFIED DEPENDING ON THE PIPELINE YOU ARE TRYING TO REPRODUCE
def get_contrasts(subject_id):
    '''
    Create the list of tuples that represents contrasts. 
    Each contrast is in the form : 
    (Name,Stat,[list of condition names],[weights on those conditions])

    Parameters:
    	- subject_id: str, ID of the subject 

    Returns:
    	- contrasts: list of tuples, list of contrasts to analyze
    '''
    # list of condition names     
    conditions = ['trial', 'trialxgain^1', 'trialxloss^1']
    
    # create contrasts
    trial = ('trial', 'T', conditions, [1, 0, 0])
    
    effect_gain = ('effect_of_gain', 'T', conditions, [0, 1, 0])
    
    effect_loss = ('effect_of_loss', 'T', conditions, [0, 0, 1])
    
    # contrast list
    contrasts = [effect_gain, effect_loss]

    return contrasts


def get_l1_analysis(subject_list, TR, run_list, exp_dir, result_dir, working_dir, output_dir):
    """
    Returns the first level analysis workflow.

    Parameters: 
        - exp_dir: str, directory where raw data are stored
        - result_dir: str, directory where results will be stored
        - working_dir: str, name of the sub-directory for intermediate results
        - output_dir: str, name of the sub-directory for final results
        - subject_list: list of str, list of subject for which you want to do the analysis
        - run_list: list of str, list of runs for which you want to do the analysis 
        - TR: float, time repetition used during acquisition

    Returns: 
        - l1_analysis : Nipype WorkFlow 
    """
    # THE FOLLOWING PART STAYS THE SAME FOR ALL PREPROCESSING PIPELINES 
    # Infosource Node - To iterate on subjects
    infosource = Node(IdentityInterface(fields = ['subject_id', 'exp_dir', 'result_dir', 
                                                  'working_dir', 'run_list'], 
                                        exp_dir = exp_dir, result_dir = result_dir, working_dir = working_dir,
                                        run_list = run_list),
                      name = 'infosource')

    infosource.iterables = [('subject_id', subject_list)] # ITERATES OVER SUBJECT LIST

    # Templates to select files node
    func_file = opj(result_dir, output_dir, 'preprocess', '_run_id_*_subject_id_{subject_id}', 
                   'swusub-{subject_id}_task-MGT_run-*_bold.nii')

    event_files = opj(exp_dir, 'sub-{subject_id}', 'func', 
                      'sub-{subject_id}_task-MGT_run-*_events.tsv')

    template = {'func' : func_file, 'event' : event_files}

    # SelectFiles node - to select necessary files
    selectfiles = Node(SelectFiles(template, base_directory=exp_dir), name = 'selectfiles')
    
    # DataSink Node - store the wanted results in the wanted repository
    datasink = Node(DataSink(base_directory=result_dir, container=output_dir), name='datasink')

    # THIS IS THE NODE EXECUTING THE get_subject_infos_spm FUNCTION
    # IF YOU'RE DOING AN FSL PIPELINE --> JUST CHANGE THE NAME OF THE FUNCTION TO get_subject_infos_fsl
    # Get Subject Info - get subject specific condition information
    subject_infos = Node(Function(input_names=['event_files', 'runs'],
                                   output_names=['subject_info'],
                                   function=get_subject_infos_spm),
                          name='subject_infos')
    
    subject_infos.inputs.runs = run_list
    # THIS IS THE NODE EXECUTING THE get_contrasts FUNCTION
    # Node contrasts to get contrasts 
    contrasts = Node(Function(function=get_contrasts,
                              input_names=['subject_id'],
                              output_names=['contrasts']),
                     name='contrasts')

    # THE FOLLOWING PART HAS TO BE MODIFIED WITH NODES OF THE PIPELINE
    node_variable = Node(node_function, name = 'node_name') # Replace with the name of the node_variable, 
    # the node_function to use in the NiPype interface,
    # and the name of the node (recommanded to be the same as node_variable)

    # ADD OTHER NODES WITH THE DIFFERENT STEPS OF THE PIPELINE

    # Create l1 analysis workflow and connect its nodes
    l1_analysis = Workflow(base_dir = opj(result_dir, working_dir), name = "l1_analysis")

    l1_analysis.connect([(infosource, selectfiles, [('subject_id', 'subject_id')]),
                        (infosource, contrasts, [('subject_id', 'subject_id')]),
                        (selectfiles, subject_infos, [('event', 'event_files')]),
                        (selectfiles, node_variable [('func', 'node_input_name')]), # Complete with name of node to link with and the name of the input 
                        # Input and output names can be found on NiPype documentation
                        (node_variable, datasink, [('node_output_name', 'preprocess.@sym_link')])
                        ])
    
    return l1_analysis

def get_subset_contrasts(file_list, method, subject_list, participants_file):
    ''' 
    Parameters :
    - file_list : original file list selected by selectfiles node 
    - subject_list : list of subject IDs that are in the wanted group for the analysis
    - participants_file: str, file containing participants caracteristics
    - method: str, one of "equalRange", "equalIndifference" or "groupComp"
    
    This function return the file list containing only the files belonging to subject in the wanted group.
    '''
    equalIndifference_id = []
    equalRange_id = []
    equalIndifference_files = []
    equalRange_files = []

    with open(participants_file, 'rt') as f:
            next(f)  # skip the header
            
            for line in f:
                info = line.strip().split()
                
                if info[0][-3:] in subject_list and info[1] == "equalIndifference":
                    equalIndifference_id.append(info[0][-3:])
                elif info[0][-3:] in subject_list and info[1] == "equalRange":
                    equalRange_id.append(info[0][-3:])
    
    for file in file_list:
        sub_id = file.split('/')
        if sub_id[-2][-3:] in equalIndifference_id:
            equalIndifference_files.append(file)
        elif sub_id[-2][-3:] in equalRange_id:
            equalRange_files.append(file)
            
    return equalIndifference_id, equalRange_id, equalIndifference_files, equalRange_files


def get_l2_analysis(subject_list, n_sub, contrast_list, method, exp_dir, result_dir, working_dir, output_dir):   
    """
    Returns the 2nd level of analysis workflow.

    Parameters: 
        - exp_dir: str, directory where raw data are stored
        - result_dir: str, directory where results will be stored
        - working_dir: str, name of the sub-directory for intermediate results
        - output_dir: str, name of the sub-directory for final results
        - subject_list: list of str, list of subject for which you want to do the preprocessing
        - contrast_list: list of str, list of contrasts to analyze
        - n_sub: float, number of subjects used to do the analysis
        - method: one of "equalRange", "equalIndifference" or "groupComp"

    Returns: 
        - l2_analysis: Nipype WorkFlow 
    """         
    # Infosource - a function free node to iterate over the list of subject names
    infosource_groupanalysis = Node(IdentityInterface(fields=['contrast_id', 'subjects'],
                                                      subjects = subject_list),
                      name="infosource_groupanalysis")

    infosource_groupanalysis.iterables = [('contrast_id', contrast_list)]

    # SelectFiles
    contrast_file = opj(result_dir, output_dir, 'l1_analysis', '_subject_id_*', "con_00{contrast_id}.nii")

    participants_file = opj(exp_dir, 'participants.tsv')

    templates = {'contrast' : contrast_file, 'participants' : participants_file}
    
    selectfiles_groupanalysis = Node(SelectFiles(templates, base_directory=result_dir, force_list= True),
                       name="selectfiles_groupanalysis")
    
    # Datasink node : to save important files 
    datasink_groupanalysis = Node(DataSink(base_directory = result_dir, container = output_dir), 
                                  name = 'datasink_groupanalysis')
    
    # Node to select subset of contrasts
    sub_contrasts = Node(Function(input_names = ['file_list', 'method', 'subject_list', 'participants_file'],
                                 output_names = ['equalIndifference_id', 'equalRange_id', 'equalIndifference_files', 'equalRange_files'],
                                 function = get_subset_contrasts),
                        name = 'sub_contrasts')

    sub_contrasts.inputs.method = method

    ## Estimate model 
    estimate_model = Node(EstimateModel(estimation_method={'Classical':1}), name = "estimate_model")

    ## Estimate contrasts
    estimate_contrast = Node(EstimateContrast(group_contrast=True),
                             name = "estimate_contrast")

    ## Create thresholded maps 
    threshold = MapNode(Threshold(use_fwe_correction = False, height_threshold = 0.001), name = "threshold", iterfield = ["stat_image", "contrast_index"])

    l2_analysis = Workflow(base_dir = opj(result_dir, working_dir), name = f"l2_analysis_{method}_nsub_{n_sub}")

    l2_analysis.connect([(infosource_groupanalysis, selectfiles_groupanalysis, [('contrast_id', 'contrast_id')]),
        (infosource_groupanalysis, sub_contrasts, [('subjects', 'subject_list')]),
        (selectfiles_groupanalysis, sub_contrasts, [('contrast', 'file_list'), ('participants', 'participants_file')]),
        (estimate_model, estimate_contrast, [('spm_mat_file', 'spm_mat_file'),
            ('residual_image', 'residual_image'),
            ('beta_images', 'beta_images')]),
        (estimate_contrast, threshold, [('spm_mat_file', 'spm_mat_file'),
            ('spmT_images', 'stat_image')]),
        (estimate_model, datasink_groupanalysis, [('mask_image', f"l2_analysis_{method}_nsub_{n_sub}.@mask")]),
        (estimate_contrast, datasink_groupanalysis, [('spm_mat_file', f"l2_analysis_{method}_nsub_{n_sub}.@spm_mat"),
            ('spmT_images', f"l2_analysis_{method}_nsub_{n_sub}.@T"),
            ('con_images', f"l2_analysis_{method}_nsub_{n_sub}.@con")]),
        (threshold, datasink_groupanalysis, [('thresholded_map', f"l2_analysis_{method}_nsub_{n_sub}.@thresh")])])
    
    if method=='equalRange' or method=='equalIndifference':
        contrasts = [('Group', 'T', ['mean'], [1]), ('Group', 'T', ['mean'], [-1])] 
        ## Specify design matrix 
        one_sample_t_test_design = Node(OneSampleTTestDesign(), name = "one_sample_t_test_design")

        l2_analysis.connect([(sub_contrasts, one_sample_t_test_design, [(f"{method}_files", 'in_files')]),
            (one_sample_t_test_design, estimate_model, [('spm_mat_file', 'spm_mat_file')])])

        threshold.inputs.contrast_index = [1, 2]
        threshold.synchronize = True

    elif method == 'groupComp':
        contrasts = [('Eq range vs Eq indiff in loss', 'T', ['Group_{1}', 'Group_{2}'], [1, -1])]
        # Node for the design matrix
        two_sample_t_test_design = Node(TwoSampleTTestDesign(), name = 'two_sample_t_test_design')

        l2_analysis.connect([(sub_contrasts, two_sample_t_test_design, [('equalRange_files', "group1_files"), 
            ('equalIndifference_files', 'group2_files')]),
            (two_sample_t_test_design, estimate_model, [("spm_mat_file", "spm_mat_file")])])

        threshold.inputs.contrast_index = [1]
        threshold.synchronize = True

    estimate_contrast.inputs.contrasts = contrasts

    return l2_analysis


def reorganize_results(result_dir, output_dir, n_sub, team_ID):
    """
    Reorganize the results to analyze them. 

    Parameters: 
        - result_dir: str, directory where results will be stored
        - output_dir: str, name of the sub-directory for final results
        - n_sub: float, number of subject used for the analysis
        - team_ID: str, ID of the team to reorganize results

    """
    from os.path import join as opj
    import os
    import shutil
    import gzip

    h1 = opj(result_dir, output_dir, f"l2_analysis_equalIndifference_nsub_{n_sub}", '_contrast_id_01')
    h2 = opj(result_dir, output_dir, f"l2_analysis_equalRange_nsub_{n_sub}", '_contrast_id_01')
    h3 = opj(result_dir, output_dir, f"l2_analysis_equalIndifference_nsub_{n_sub}", '_contrast_id_01')
    h4 = opj(result_dir, output_dir, f"l2_analysis_equalRange_nsub_{n_sub}", '_contrast_id_01')
    h5 = opj(result_dir, output_dir, f"l2_analysis_equalIndifference_nsub_{n_sub}", '_contrast_id_02')
    h6 = opj(result_dir, output_dir, f"l2_analysis_equalRange_nsub_{n_sub}", '_contrast_id_02')
    h7 = opj(result_dir, output_dir, f"l2_analysis_equalIndifference_nsub_{n_sub}", '_contrast_id_02')
    h8 = opj(result_dir, output_dir, f"l2_analysis_equalRange_nsub_{n_sub}", '_contrast_id_02')
    h9 = opj(result_dir, output_dir, f"l2_analysis_groupComp_nsub_{n_sub}", '_contrast_id_02')

    h = [h1, h2, h3, h4, h5, h6, h7, h8, h9]

    repro_unthresh = [opj(filename, "spmT_0002.nii") if i in [4, 5] else opj(filename, 
                     "spmT_0001.nii") for i, filename in enumerate(h)]

    repro_thresh = [opj(filename, "_threshold1", 
         "spmT_0002_thr.nii") if i in [4, 5] else opj(filename, 
          "_threshold0", "spmT_0001_thr.nii")  for i, filename in enumerate(h)]
    
    if not os.path.isdir(opj(result_dir, "NARPS-reproduction")):
        os.mkdir(opj(result_dir, "NARPS-reproduction"))
    
    for i, filename in enumerate(repro_unthresh):
        f_in = filename
        f_out = opj(result_dir, "NARPS-reproduction", f"team_{team_ID}_nsub_{n_sub}_hypo{i+1}_unthresholded.nii")
        shutil.copyfile(f_in, f_out)

    for i, filename in enumerate(repro_thresh):
        f_in = filename
        f_out = opj(result_dir, "NARPS-reproduction", f"team_{team_ID}_nsub_{n_sub}_hypo{i+1}_thresholded.nii")
        shutil.copyfile(f_in, f_out)

    print(f"Results files of team {team_ID} reorganized.")


