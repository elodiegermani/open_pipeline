#!/usr/bin/python
# coding: utf-8

""" Tests of the 'narps_open.pipelines.team_B5I6' module.

Launch this test with PyTest

Usage:
======
    pytest -q test_team_B5I6.py
    pytest -q test_team_B5I6.py -k <selected_test>
"""
from os.path import join, exists, abspath
from filecmp import cmp

from pytest import helpers, mark
from nipype import Workflow, Node, Function
from nipype.interfaces.base import Bunch

from narps_open.utils.configuration import Configuration
from narps_open.pipelines.team_B5I6 import PipelineTeamB5I6

class TestPipelinesTeamB5I6:
    """ A class that contains all the unit tests for the PipelineTeamB5I6 class."""

    @staticmethod
    @mark.unit_test
    def test_create():
        """ Test the creation of a PipelineTeamB5I6 object """

        pipeline = PipelineTeamB5I6()

        # 1 - check the parameters
        assert pipeline.fwhm == 5.0
        assert pipeline.team_id == 'B5I6'

        # 2 - check workflows
        assert pipeline.get_preprocessing() is None
        assert isinstance(pipeline.get_run_level_analysis(), Workflow)
        assert isinstance(pipeline.get_subject_level_analysis(), Workflow)
        group_level = pipeline.get_group_level_analysis()
        assert len(group_level) == 3
        for sub_workflow in group_level:
            assert isinstance(sub_workflow, Workflow)

    @staticmethod
    @mark.unit_test
    def test_outputs():
        """ Test the expected outputs of a PipelineTeamB5I6 object """

        pipeline = PipelineTeamB5I6()

        # 1 - 1 subject outputs
        pipeline.subject_list = ['001']
        helpers.test_pipeline_outputs(pipeline, [0, 4*6*4*1, 4*6*1, 6*6*2 + 3*6, 18])

        # 2 - 4 subjects outputs
        pipeline.subject_list = ['001', '002', '003', '004']
        helpers.test_pipeline_outputs(pipeline, [0, 4*6*4*4, 4*6*4, 6*6*2 + 3*6, 18])

    @staticmethod
    @mark.unit_test
    def test_subject_information():
        """ Test the get_subject_information method """

        # Get test files
        test_file = abspath(join(
            Configuration()['directories']['test_data'], 'pipelines', 'events.tsv'))
        test_file_2 = abspath(join(
            Configuration()['directories']['test_data'], 'pipelines', 'events_resp.tsv'))

        # Prepare several scenarii
        info_missed = PipelineTeamB5I6.get_subject_information(test_file)
        info_no_missed = PipelineTeamB5I6.get_subject_information(test_file_2)

        # Compare bunches to expected
        bunch = info_missed[0]
        assert isinstance(bunch, Bunch)
        assert bunch.conditions == ['trial', 'gain', 'loss', 'missed']
        helpers.compare_float_2d_arrays(bunch.onsets, [
            [4.071, 11.834, 27.535, 36.435],
            [4.071, 11.834, 27.535, 36.435],
            [4.071, 11.834, 27.535, 36.435],
            [19.535]
            ])
        helpers.compare_float_2d_arrays(bunch.durations, [
            [4.0, 4.0, 4.0, 4.0],
            [4.0, 4.0, 4.0, 4.0],
            [4.0, 4.0, 4.0, 4.0],
            [4.0]
            ])
        helpers.compare_float_2d_arrays(bunch.amplitudes, [
            [1.0, 1.0, 1.0, 1.0],
            [-4.5, 15.5, -8.5, -2.5],
            [-7.0,  1.0,  2.0,  4.0],
            [1.0]
            ])

        bunch = info_no_missed[0]
        assert isinstance(bunch, Bunch)
        assert bunch.conditions == ['trial', 'gain', 'loss']
        helpers.compare_float_2d_arrays(bunch.onsets, [
            [4.071, 11.834, 27.535, 36.435],
            [4.071, 11.834, 27.535, 36.435],
            [4.071, 11.834, 27.535, 36.435]
            ])
        helpers.compare_float_2d_arrays(bunch.durations, [
            [4.0, 4.0, 4.0, 4.0],
            [4.0, 4.0, 4.0, 4.0],
            [4.0, 4.0, 4.0, 4.0]
            ])
        helpers.compare_float_2d_arrays(bunch.amplitudes, [
            [1.0, 1.0, 1.0, 1.0],
            [-4.5, 15.5, -8.5, -2.5],
            [-7.0,  1.0,  2.0,  4.0]
            ])

    @staticmethod
    @mark.unit_test
    def test_confounds_file_no_outliers(temporary_data_dir):
        """ Test the get_confounds_file method in the case with no outliers """

        # Get input and reference output file
        confounds_file = abspath(join(
            Configuration()['directories']['test_data'], 'pipelines', 'confounds.tsv'))
        reference_file = abspath(join(
            Configuration()['directories']['test_data'],
            'pipelines', 'team_B5I6', 'out_confounds_no_outliers.tsv'))

        # Create new confounds file
        confounds_node = Node(Function(
            input_names = ['filepath', 'subject_id', 'run_id'],
            output_names = ['confounds_file'],
            function = PipelineTeamB5I6.get_confounds_file),
            name = 'confounds_node')
        confounds_node.base_dir = temporary_data_dir
        confounds_node.inputs.filepath = confounds_file
        confounds_node.inputs.subject_id = 'sid'
        confounds_node.inputs.run_id = 'rid'
        confounds_node.run()

        # Check confounds file was created
        created_confounds_file = abspath(join(
            temporary_data_dir, confounds_node.name, 'confounds_file_sub-sid_run-rid.tsv'))
        assert exists(created_confounds_file)

        # Check contents
        assert cmp(reference_file, created_confounds_file)

    @staticmethod
    @mark.unit_test
    def test_confounds_file_outliers(temporary_data_dir):
        """ Test the get_confounds_file method in the case with outliers """

        # Get input and reference output file
        confounds_file = abspath(join(
            Configuration()['directories']['test_data'],
            'pipelines', 'team_B5I6', 'confounds_with_outliers.tsv'))
        reference_file = abspath(join(
            Configuration()['directories']['test_data'],
            'pipelines', 'team_B5I6', 'out_confounds_outliers.tsv'))

        # Create new confounds file
        confounds_node = Node(Function(
            input_names = ['filepath', 'subject_id', 'run_id'],
            output_names = ['confounds_file'],
            function = PipelineTeamB5I6.get_confounds_file),
            name = 'confounds_node')
        confounds_node.base_dir = temporary_data_dir
        confounds_node.inputs.filepath = confounds_file
        confounds_node.inputs.subject_id = 'sid'
        confounds_node.inputs.run_id = 'rid'
        confounds_node.run()

        # Check confounds file was created
        created_confounds_file = abspath(join(
            temporary_data_dir, confounds_node.name, 'confounds_file_sub-sid_run-rid.tsv'))
        assert exists(created_confounds_file)

        # Check contents
        assert cmp(reference_file, created_confounds_file)

    @staticmethod
    @mark.pipeline_test
    def test_execution():
        """ Test the execution of a PipelineTeamB5I6 and compare results """
        helpers.test_pipeline_evaluation('B5I6')
