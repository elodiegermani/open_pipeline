#!/usr/bin/python
# coding: utf-8

""" Tests of the 'narps_open.pipelines.team_3C6G' module.

Launch this test with PyTest

Usage:
======
    pytest -q test_team_3C6G.py
    pytest -q test_team_3C6G.py -k <selected_test>
"""
from os.path import join

from pytest import helpers, mark
from nipype import Workflow
from nipype.interfaces.base import Bunch

from narps_open.utils.configuration import Configuration
from narps_open.pipelines.team_3C6G import PipelineTeam3C6G

class TestPipelinesTeam3C6G:
    """ A class that contains all the unit tests for the PipelineTeam3C6G class."""

    @staticmethod
    @mark.unit_test
    def test_create():
        """ Test the creation of a PipelineTeam3C6G object """

        pipeline = PipelineTeam3C6G()

        # 1 - check the parameters
        assert pipeline.fwhm == 6.0
        assert pipeline.team_id == '3C6G'

        # 2 - check workflows
        assert isinstance(pipeline.get_preprocessing(), Workflow)
        assert pipeline.get_run_level_analysis() is None
        assert isinstance(pipeline.get_subject_level_analysis(), Workflow)
        group_level = pipeline.get_group_level_analysis()

        assert len(group_level) == 3
        for sub_workflow in group_level:
            assert isinstance(sub_workflow, Workflow)

    @staticmethod
    @mark.unit_test
    def test_outputs():
        """ Test the expected outputs of a PipelineTeam3C6G object """
        pipeline = PipelineTeam3C6G()
        # 1 - 1 subject - 1 run outputs
        pipeline.subject_list = ['001']
        pipeline.run_list = ['01']
        assert len(pipeline.get_preprocessing_outputs()) == 2
        assert len(pipeline.get_run_level_outputs()) == 0
        assert len(pipeline.get_subject_level_outputs()) == 11
        assert len(pipeline.get_group_level_outputs()) == 105
        assert len(pipeline.get_hypotheses_outputs()) == 18

        # 2 - 1 subject - 4 runs outputs
        pipeline.subject_list = ['001']
        pipeline.run_list = ['01', '02', '03', '04']
        assert len(pipeline.get_preprocessing_outputs()) == 2 * 4
        assert len(pipeline.get_run_level_outputs()) == 0
        assert len(pipeline.get_subject_level_outputs()) == 11
        assert len(pipeline.get_group_level_outputs()) == 105
        assert len(pipeline.get_hypotheses_outputs()) == 18

        # 2 - 4 subjects outputs
        pipeline.subject_list = ['001', '002', '003', '004']
        pipeline.run_list = ['01', '02', '03', '04']
        assert len(pipeline.get_preprocessing_outputs()) == 2 * 4 * 4
        assert len(pipeline.get_run_level_outputs()) == 0
        assert len(pipeline.get_subject_level_outputs()) == 44
        assert len(pipeline.get_group_level_outputs()) == 105
        assert len(pipeline.get_hypotheses_outputs()) == 18

    @staticmethod
    @mark.unit_test
    def test_subject_information():
        """ Test the get_subject_information method """

        # Get test files
        test_file = join(Configuration()['directories']['test_data'], 'pipelines', 'events.tsv')

        bunch = PipelineTeam3C6G.get_subject_information(test_file)

        # Compare bunches to expected
        assert isinstance(bunch, Bunch)
        assert bunch.conditions == ['trial']
        helpers.compare_float_2d_arrays(bunch.onsets, [
            [4.071, 11.834, 19.535, 27.535, 36.435]])
        helpers.compare_float_2d_arrays(bunch.durations, [
            [4.0, 4.0, 4.0, 4.0, 4.0]])
        assert bunch.amplitudes is None
        assert bunch.tmod is None
        assert bunch.regressor_names is None
        assert bunch.regressors is None
        pmod = bunch.pmod[0]
        assert isinstance(pmod, Bunch)
        assert pmod.name == ['gain', 'loss']
        assert pmod.poly == [1, 1]
        helpers.compare_float_2d_arrays(pmod.param, [
            [14.0, 34.0, 38.0, 10.0, 16.0],
            [6.0, 14.0, 19.0, 15.0, 17.0]
            ])

    @staticmethod
    @mark.pipeline_test
    def test_execution():
        """ Test the execution of a PipelineTeam3C6G and compare results """
        helpers.test_pipeline_evaluation('3C6G')
