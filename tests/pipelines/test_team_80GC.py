#!/usr/bin/python
# coding: utf-8

""" Tests of the 'narps_open.pipelines.team_80GC' module.

Launch this test with PyTest

Usage:
======
    pytest -q test_team_80GC.py
    pytest -q test_team_80GC.py -k <selected_test>
"""
from os.path import join, exists
from filecmp import cmp

from pytest import helpers, mark
from nipype import Workflow, Node, Function
from nipype.interfaces.base import Bunch

from narps_open.utils.configuration import Configuration
from narps_open.pipelines.team_80GC import PipelineTeam80GC

class TestPipelinesTeam80GC:
    """ A class that contains all the unit tests for the PipelineTeam80GC class."""

    @staticmethod
    @mark.unit_test
    def test_create():
        """ Test the creation of a PipelineTeam80GC object """

        pipeline = PipelineTeam80GC()

        # 1 - check the parameters
        assert pipeline.team_id == '80GC'

        # 2 - check workflows
        assert pipeline.get_preprocessing() is None
        assert pipeline.get_run_level_analysis() is None
        assert isinstance(pipeline.get_subject_level_analysis(), Workflow)
        assert isinstance(pipeline.get_group_level_analysis(), Workflow)

    @staticmethod
    @mark.unit_test
    def test_outputs():
        """ Test the expected outputs of a PipelineTeam80GC object """
        pipeline = PipelineTeam80GC()
        # 1 - 1 subject outputs
        pipeline.subject_list = ['001']
        helpers.test_pipeline_outputs(pipeline, [0, 0, 2*1, 0, 18])

        # 2 - 4 subjects outputs
        pipeline.subject_list = ['001', '002', '003', '004']
        helpers.test_pipeline_outputs(pipeline, [0, 0, 2*4, 0, 18])

    @staticmethod
    @mark.unit_test
    def test_events_files(temporary_data_dir):
        """ Test the get_events_files method """

        # Get test files
        test_file = join(Configuration()['directories']['test_data'], 'pipelines', 'events.tsv')
        reference_file_gain = join(Configuration()['directories']['test_data'],
            'pipelines', 'team_80GC', 'events_sub-sid_timesxgain.txt')
        reference_file_loss = join(Configuration()['directories']['test_data'],
            'pipelines', 'team_80GC', 'events_sub-sid_timesxloss.txt')

        # Create a Nipype Node using get_events_files
        test_get_events_files = Node(Function(
            function = PipelineTeam80GC.get_events_files,
            input_names = ['event_files', 'nb_events', 'subject_id'],
            output_names = ['event_files']
            ), name = 'test_get_events_files')
        test_get_events_files.base_dir = temporary_data_dir
        test_get_events_files.inputs.event_files = [test_file, test_file]
        test_get_events_files.inputs.nb_events = 5
        test_get_events_files.inputs.subject_id = 'sid'
        test_get_events_files.run()

        # Check event files were created
        event_file_gain = join(
            temporary_data_dir,  test_get_events_files.name, 'events_sub-sid_timesxgain.txt')
        event_file_loss = join(
            temporary_data_dir,  test_get_events_files.name, 'events_sub-sid_timesxloss.txt')
        assert exists(event_file_gain)
        assert exists(event_file_loss)

        # Compare output files to expected
        assert cmp(reference_file_gain, event_file_gain)
        assert cmp(reference_file_loss, event_file_loss)

    @staticmethod
    @mark.unit_test
    def test_events_arguments():
        """ Test the get_events_arguments method """

    @staticmethod
    @mark.unit_test
    def test_confounds_file(temporary_data_dir):
        """ Test the get_confounds_file method """

        confounds_file = join(
            Configuration()['directories']['test_data'], 'pipelines', 'confounds.tsv')
        reference_file = join(
            Configuration()['directories']['test_data'], 'pipelines',
            'team_80GC', 'confounds_file_sub-sid.tsv')

        # Create a Nipype Node using get_confounds_file
        test_get_confounds_file = Node(Function(
            function = PipelineTeam80GC.get_confounds_file,
            input_names = ['confounds_files', 'nb_time_points', 'subject_id'],
            output_names = ['confounds_file']
            ), name = 'test_get_confounds_file')
        test_get_confounds_file.base_dir = temporary_data_dir
        test_get_confounds_file.inputs.confounds_files = [confounds_file, confounds_file]
        test_get_confounds_file.inputs.nb_time_points = 3
        test_get_confounds_file.inputs.subject_id = 'sid'
        test_get_confounds_file.run()

        # Check confounds file was created
        created_confounds_file = join(
            temporary_data_dir, test_get_confounds_file.name, 'confounds_file_sub-sid.tsv')
        assert exists(created_confounds_file)

        # Check contents
        assert cmp(reference_file, created_confounds_file)

    @staticmethod
    @mark.unit_test
    def test_confounds_arguments():
        """ Test the get_confounds_arguments method """

    @staticmethod
    @mark.pipeline_test
    def test_execution():
        """ Test the execution of a PipelineTeam80GC and compare results """
        helpers.test_pipeline_evaluation('80GC')
