#!/usr/bin/python
# coding: utf-8

"""
NARPS team 6FH5 rewritten using Nipype-SPM

"""


from os.path import join

# [INFO] The import of base objects from Nipype, to create Workflows
from nipype import Node, Workflow # , JoinNode, MapNode

# [INFO] a list of interfaces used to manpulate data
from nipype.interfaces.utility import IdentityInterface, Function
from nipype.interfaces.io import SelectFiles, DataSink
from os.path import join
from itertools import product

from nipype import Workflow, Node, MapNode
from nipype.interfaces.utility import IdentityInterface, Function, Rename, Merge
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.algorithms.misc import Gunzip
from nipype.interfaces.spm import (RealignUnwarp, Coregister, NewSegment, Segment,
    Normalize12, Smooth, OneSampleTTestDesign, EstimateModel, FieldMap,
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




# [INFO] In order to inherit from Pipeline
from narps_open.pipelines import Pipeline

class PipelineTeam6FH5(Pipeline):
    """ A class that defines the pipeline of team 6FH5 """

    def __init__(self):
        super().__init__()
        self.fwhm = 6.0
        self.team_id = '6FH5'
        #self.contrast_list = ['0001', '0002', '0003', '0004', '0005', '0006'] # why is this selected?

        # Define contrasts they onl give group contrasts
        
     
    def get_preprocessing(self):
        """ Return a Nipype workflow describing the prerpocessing part of the pipeline """

        # [INFO] The following part stays the same for all preprocessing pipelines

        # IdentityInterface node - allows to iterate over subjects and runs
        info_source = Node(
            IdentityInterface(fields=['subject_id', 'run_id']),
            name='info_source'
        )
        info_source.iterables = [
            ('subject_id', self.subject_list),
            ('run_id', self.run_list),
        ]

        # Templates to select files node
        templates = {
            'anat': join(
                'sub-{subject_id}', 'anat', 'sub-{subject_id}_T1w.nii.gz'
                ),
            'func': join(
                'sub-{subject_id}', 'func', 'sub-{subject_id}_task-MGT_run-{run_id}_bold.nii.gz'
                ),
            'magnitude': join(
                'sub-{subject_id}', 'fmap', 'sub-{subject_id}_magnitude1.nii.gz'
                ),
            'phasediff': join(
                'sub-{subject_id}', 'fmap', 'sub-{subject_id}_phasediff.nii.gz'
                )
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

        
        # Gunzip nodes - gunzip files because SPM do not use .nii.gz files
        gunzip_anat = Node(Gunzip(), name = 'gunzip_anat')
        gunzip_func = Node(Gunzip(), name = 'gunzip_func')            
        gunzip_magnitude = Node(Gunzip(), name = 'gunzip_magnitude')
        gunzip_phase = Node(Gunzip(), name = 'gunzip_phase')
        # gunzip node connection
        preprocessing.connect(select_files, 'anat', gunzip_anat, 'in_file')
        preprocessing.connect(select_files, 'func', gunzip_func, 'in_file')
        preprocessing.connect(select_files, 'magnitude', gunzip_magnitude, 'in_file')
        preprocessing.connect(select_files, 'phase', gunzip_phase, 'in_file')

       
        # ORDER 
        # VBM-fieldmap, realign-unwrap, slicetiming, coregistration, segmentation-spm-dartel, normalization-dartel, smoothing 

        # FIELD MAP - Compute a voxel displacement map from magnitude and phase data
        # values are from https://github.com/Inria-Empenn/narps_open_pipelines/blob/ff9f46922a4aef5946f094bbff6cbdfc6ab93917/narps_open/pipelines/team_R5K7.py
        fieldmap = Node(FieldMap(), name = 'fieldmap')
        fieldmap.inputs.blip_direction = -1
        fieldmap.inputs.echo_times = (4.92, 7.38)
        fieldmap.inputs.total_readout_time = 29.15
        fieldmap.inputs.template = join(SPMInfo.getinfo()['path'], 'toolbox', 'FieldMap', 'T1.nii')
        
        # fieldmap node connection
        preprocessing.connect(gunzip_magnitude, 'out_file', fieldmap, 'magnitude_file')
        preprocessing.connect(gunzip_phase, 'out_file', fieldmap, 'phase_file')
        preprocessing.connect(gunzip_anat, 'out_file', fieldmap, 'anat_file')


        # REALIGN UNWARP
        # 

    

        realign_unwarp = MapNode(RealignUnwarp(), name = 'realign_unwarp', iterfield = 'in_files')
        realign_unwarp.inputs.quality = 0.95
        realign_unwarp.inputs.separation = 3
        realign_unwarp.inputs.register_to_mean = False
        realign_unwarp.inputs.interp = 7
        realign_unwarp.inputs.reslice_interp = 7
        # realign unwarp node connection 
        preprocessing.connect(fieldmap, 'vdm', realign_unwarp, 'phase_map')
        preprocessing.connect(gunzip_func, 'out_file', realign_unwarp, 'in_files')


        return preprocessing

    # [INFO] There was no run level analysis for the pipelines using SPM
    def get_run_level_analysis(self):
        """ Return a Nipype workflow describing the run level analysis part of the pipeline """
        return None
    def get_subject_level_analysis(self):
        return
    def get_group_level_analysis(self):
        return
    def get_hypotheses_outputs(self):
        return 