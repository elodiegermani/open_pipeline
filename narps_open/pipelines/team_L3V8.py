#!/usr/bin/python
# coding: utf-8

""" Write the work of NARPS team L3V8 using Nipype """

from os.path import join
from itertools import product

from nipype import Workflow, Node, MapNode
from nipype.interfaces.utility import IdentityInterface, Function, Rename, Merge
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.algorithms.misc import Gunzip
from nipype.interfaces.spm import (Realign, Coregister, NewSegment,
    Normalize12, Smooth, OneSampleTTestDesign, EstimateModel, 
    EstimateContrast, Level1Design, TwoSampleTTestDesign, Threshold)
from nipype.interfaces.spm.base import Info as SPMInfo
from nipype.interfaces.fsl import ExtractROI
from nipype.algorithms.modelgen import SpecifySPMModel

from narps_open.pipelines import Pipeline
from narps_open.data.task import TaskInformation
from narps_open.data.participants import get_group
from narps_open.core.common import (
    remove_parent_directory, list_intersection, elements_in_string, clean_list
    )
from narps_open.utils.configuration import Configuration

class PipelineTeamL3V8(Pipeline):
    """ NARPS team L3V8 pipeline class definition and description of pipeline steps 
    Participants:101"""
    
    def __init__(self):
        super().__init__()
        self.fwhm = 6.0
        self.team_id = 'L3V8'
        self.contrast_list = ['0001', '0002', '0003', '0004', '0005', '0006'] # why is this selected?

        # Define contrasts
        gain_conditions = [f'gamble_run{i}xgain_run{i}^1' for i in range(1,len(self.run_list) + 1)] # to name runs 
        loss_conditions = [f'gamble_run{i}xloss_run{i}^1' for i in range(1,len(self.run_list) + 1)]
        self.subject_level_contrasts = [
            ('pos_gain', 'T', gain_conditions, [1, 1, 1, 1]), # average postivite activation -gain value
            ('pos_loss', 'T', loss_conditions, [1, 1, 1, 1]), # average positive effect -loss value 
            ('neg_gain', 'T', gain_conditions, [-1, -1, -1, -1]),  # average negative activation - gain value
            ('neg_loss', 'T', loss_conditions, [-1, -1, -1, -1]), # average negative activation - loss value 
            ]
        # figure out group contrast settings # TODO - make sure why?
        #('contrast1', 'T', gain_conditions, [-1, 1, -1, 1, -1, 1, -1, 1]) # group differences between EqI and EqR
            
    def get_preprocessing(self):
        """
        Create the second part of the preprocessing workflow.

        Returns:
            - preprocessing : nipype.WorkFlow
        """
        # Infosource Node - To iterate on subjects
        info_source = Node(IdentityInterface(
            fields = ['subject_id', 'run_id']),
            name = 'info_source')
        info_source.iterables = [
            ('subject_id', self.subject_list), ('run_id', self.run_list)
            ]

        # SelectFiles Node - Select necessary files
        templates = {
            'anat' : join('sub-{subject_id}', 'anat', 'sub-{subject_id}_T1w.nii.gz'),
            'func' : join('sub-{subject_id}', 'func',
                'sub-{subject_id}_task-MGT_run-{run_id}_bold.nii.gz'),
        }

        preprocessing = Workflow(
            base_dir = self.directories.working_dir,
            name = 'preprocessing'
        )

        # select files
        select_files = Node(SelectFiles(templates), name = 'select_files')
        select_files.inputs.base_directory = self.directories.dataset_dir
        
        # DataSink Node - store the wanted results in the wanted repository save output
        data_sink = Node(DataSink(), name = 'data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir

        # selectfiles node connection
        preprocessing.connect(info_source, 'subject_id', select_files, 'subject_id')
        preprocessing.connect(info_source, 'run_id', select_files, 'run_id')

        # Order of operations:
        # Realignment, co-registration, segmentation, normalization, smooth (6 mm).
        
        # Gunzip nodes - gunzip files because SPM do not use .nii.gz files
        gunzip_anat = Node(Gunzip(), name = 'gunzip_anat')
        gunzip_func = Node(Gunzip(), name = 'gunzip_func')            

        # gunzip node connection
        preprocessing.connect(select_files, 'anat', gunzip_anat, 'in_file')
        preprocessing.connect(select_files, 'func', gunzip_func, 'in_file')
        
        # motion correction - default realignment node in SPM

        motion_correction = Node(interface=Realign(), name='realign')
        motion_correction.inputs.register_to_mean = False # they registered to 1st slice
        motion_correction.inputs.interp = 4
        motion_correction.inputs.quality = 0.9
        motion_correction.inputs.write_interp = 4 
        motion_correction.inputs.jobtype = 'estwrite'
        

        # connection node for motion correction
        preprocessing.connect(gunzip_func, 'out_file', motion_correction, 'in_files')
        preprocessing.connect( motion_correction, 'realigned_files', data_sink, 'preprocessing.@realigned_files')
        preprocessing.connect( motion_correction, 'realignment_parameters', data_sink, 'preprocessing.@realignment_parameters')
        preprocessing.connect( motion_correction, 'mean_image', data_sink, 'preprocessing.@mean_image')
        
        # coregistration node

        coregisteration = Node(Coregister(), name="coregister")
        coregisteration.inputs.jobtype = 'estimate'
        coregisteration.inputs.cost_function = 'nmi'

        
        # connect coreg
        preprocessing.connect( motion_correction, 'mean_image', coregisteration, 'target') # target=mean
        preprocessing.connect( gunzip_anat, 'out_file', coregisteration, 'source') # T1w=source anat
        preprocessing.connect( coregisteration, 'coregistered_source', data_sink, 'preprocessing.@coregistered_source') # T1w=source anat
        
        # Get SPM Tissue Probability Maps file
        spm_tissues_file = join(SPMInfo.getinfo()['path'], 'tpm', 'TPM.nii')

        # Segmentation Node - SPM Segment function via custom scripts (defaults left in place)
        segmentation = Node(NewSegment(), name = 'segmentation')
        segmentation.inputs.write_deformation_fields = [True, True]
        segmentation.inputs.channel_info = (0.0001, 60, (True, True))
        segmentation.inputs.affine_regularization = 'mni'
        segmentation.inputs.tissues = [
            [(spm_tissues_file, 1), 1, (True,False), (True, False)],
            [(spm_tissues_file, 2), 1, (True,False), (True, False)],
            [(spm_tissues_file, 3), 2, (True,False), (False, False)],
            [(spm_tissues_file, 4), 3, (True,False), (False, False)],
            [(spm_tissues_file, 5), 4, (True,False), (False, False)],
            [(spm_tissues_file, 6), 2, (False,False), (False, False)]
        ]
        # segmentation connection
        preprocessing.connect(coregisteration, 'coregistered_source', segmentation, 'channel_files') 
        preprocessing.connect(segmentation, 'bias_corrected_images', data_sink, 'preprocessing.@bias_corrected_images')
        preprocessing.connect(segmentation, 'native_class_images', data_sink, 'preprocessing.@native_class_images')
        preprocessing.connect(segmentation, 'forward_deformation_field', data_sink, 'preprocessing.@forward_deformation_field')
        
       
        # normalization node

        normalization = Node(Normalize12(), name="normalize") 
        normalization.inputs.jobtype = 'write'
        normalization.inputs.write_interp = 4
        normalization.inputs.warping_regularization = [0, 0.001, 0.5, 0.05, 0.2]

        # normalization connection 
        preprocessing.connect(segmentation, 'forward_deformation_field', normalization, 'deformation_file')
        preprocessing.connect(motion_correction, 'realigned_files', normalization, 'apply_to_files')
         
        preprocessing.connect(normalization, 'normalized_files', data_sink, 'preprocessing.@normalized_files') 
        
    
        # smoothing node

        smooth = Node(Smooth(), name="smooth")
        smooth.inputs.fwhm = [6, 6, 6]
        smooth.inputs.implicit_masking = False

        preprocessing.connect(normalization, 'normalized_files', smooth, 'in_files') 
        preprocessing.connect(smooth, 'smoothed_files', data_sink, 'preprocessing.@smoothed_files') 
        

        # all nodes connected and returns preprocessing
        
        return preprocessing
    
    
    def get_run_level_analysis(self):

        return
    def get_subject_level_analysis(self):
        return
    def get_group_level_analysis(self):
        return
    def get_hypotheses_outputs(self):
        return 