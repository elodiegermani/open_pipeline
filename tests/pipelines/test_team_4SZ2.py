#!/usr/bin/python
# coding: utf-8

""" Tests of the 'narps_open.pipelines.team_4SZ2' module.

Launch this test with PyTest

Usage:
======
    pytest -q test_team_4SZ2.py
    pytest -q test_team_4SZ2.py -k <selected_test>
"""
from os.path import join, exists, abspath
from filecmp import cmp

from pytest import helpers, mark
from nipype import Workflow, Node, Function
from nipype.interfaces.base import Bunch

from narps_open.utils.configuration import Configuration
from narps_open.pipelines.team_4SZ2 import PipelineTeam4SZ2

class TestPipelinesTeam4SZ2:
    """ A class that contains all the unit tests for the PipelineTeam4SZ2 class."""

    @staticmethod
    @mark.unit_test
    def test_create():
        """ Test the creation of a PipelineTeam4SZ2 object """

        pipeline = PipelineTeam4SZ2()

        # 1 - check the parameters
        assert pipeline.fwhm == 5.0
        assert pipeline.team_id == '4SZ2'

        # 2 - check workflows
        assert pipeline.get_preprocessing() is None
        assert isinstance(pipeline.get_run_level_analysis(), Workflow)
        assert pipeline.get_subject_level_analysis() is None
        group_level = pipeline.get_group_level_analysis()
        assert len(group_level) == 3
        for sub_workflow in group_level:
            assert isinstance(sub_workflow, Workflow)

    @staticmethod
    @mark.unit_test
    def test_outputs():
        """ Test the expected outputs of a PipelineTeam4SZ2 object """

        pipeline = PipelineTeam4SZ2()

        # 1 - 1 subject outputs
        pipeline.subject_list = ['001']
        helpers.test_pipeline_outputs(pipeline, [0, 2*4*1*4, 0, 6*2*2 + 3*2, 18])

        # 2 - 4 subjects outputs
        pipeline.subject_list = ['001', '002', '003', '004']
        helpers.test_pipeline_outputs(pipeline, [0, 2*4*4*4, 0, 6*2*2 + 3*2, 18])

    @staticmethod
    @mark.unit_test
    def test_subject_information():
        """ Test the get_subject_information method """

        # Get test files
        test_file = join(Configuration()['directories']['test_data'], 'pipelines', 'events.tsv')

        # Prepare several scenarii
        info_missed = PipelineTeam4SZ2.get_subject_information(test_file)

        # Compare bunches to expected
        bunch = info_missed[0]
        assert isinstance(bunch, Bunch)
        assert bunch.conditions == ['gain', 'loss']
        helpers.compare_float_2d_arrays(bunch.onsets, [
            [4.071, 11.834, 19.535, 27.535, 36.435],
            [4.071, 11.834, 19.535, 27.535, 36.435]
            ])
        helpers.compare_float_2d_arrays(bunch.durations, [
            [4.0, 4.0, 4.0, 4.0, 4.0],
            [4.0, 4.0, 4.0, 4.0, 4.0]
            ])
        helpers.compare_float_2d_arrays(bunch.amplitudes, [
            [14.0, 34.0, 38.0, 10.0, 16.0],
            [6.0, 14.0, 19.0, 15.0, 17.0]
            ])

    @staticmethod
    @mark.unit_test
    def test_one_sample_t_test_regressors():
        """ Test the get_one_sample_t_test_regressors method """

        result = PipelineTeam4SZ2.get_one_sample_t_test_regressors(['001', '002', '003', '004'])
        assert result == {'group_mean' : [1]*4}

    @staticmethod
    @mark.unit_test
    def test_two_sample_t_test_regressors():
        """ Test the get_two_sample_t_test_regressors method """

        result_1, result_2 = PipelineTeam4SZ2.get_two_sample_t_test_regressors(
            ['001', '003'], # equal_range_ids
            ['002', '004'], # equal_indifference_ids
            ['001', '002', '003', '004'], # subject_list
            ['01', '02'] # run_list
            )
        assert result_1 == {
            'equalRange' : [1, 1, 0, 0, 1, 1, 0, 0],
            'equalIndifference' : [0, 0, 1, 1, 0, 0, 1, 1]
            }
        assert result_2 == [1, 1, 2, 2, 1, 1, 2, 2]

    @staticmethod
    @mark.pipeline_test
    def test_execution():
        """ Test the execution of a PipelineTeam4SZ2 and compare results """
        helpers.test_pipeline_evaluation('4SZ2')