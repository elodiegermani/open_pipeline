#!/usr/bin/python
# coding: utf-8

""" Tests of the 'narps_open.pipelines.team_0I4U' module.

Launch this test with PyTest

Usage:
======
    pytest -q test_team_0I4U.py
    pytest -q test_team_0I4U.py -k <selected_test>
"""
from os.path import join, exists
from filecmp import cmp

from pandas import read_csv

from pytest import helpers, mark
from nipype import Workflow
from nipype.interfaces.base import Bunch

from narps_open.utils.configuration import Configuration
from narps_open.pipelines.team_0I4U import PipelineTeam0I4U

class TestPipelinesTeam0I4U:
    """ A class that contains all the unit tests for the PipelineTeam0I4U class."""

    @staticmethod
    @mark.unit_test
    def test_create():
        """ Test the creation of a PipelineTeam0I4U object """

        pipeline = PipelineTeam0I4U()

        # 1 - check the parameters
        assert pipeline.fwhm == 5.0
        assert pipeline.team_id == '0I4U'

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
        """ Test the expected outputs of a PipelineTeam0I4U object """
        pipeline = PipelineTeam0I4U()
        # 1 - 1 subject outputs
        pipeline.subject_list = ['001']
        helpers.test_pipeline_outputs(pipeline, [4*2, 0, 1*1 + 2*2, 2*2*8 + 2*1*5, 18])

        # 2 - 4 subjects outputs
        pipeline.subject_list = ['001', '002', '003', '004']
        helpers.test_pipeline_outputs(pipeline, [4*4*2, 0, 4*(1*1 + 2*2), 2*2*8 + 2*1*5, 18])

    @staticmethod
    @mark.unit_test
    def test_subject_information():
        """ Test the get_subject_information method """

        # Get test files
        test_file = join(Configuration()['directories']['test_data'], 'pipelines', 'events.tsv')
        bunch = PipelineTeam0I4U.get_subject_information(test_file, 1)

        # Compare bunches to expected
        assert isinstance(bunch, Bunch)
        assert bunch.conditions == ['trial_run1', 'button_run1']
        helpers.compare_float_2d_arrays(bunch.onsets, [
            [4.071, 11.834, 19.535, 27.535, 36.435],
            [6.459, 14.123, 19.535, 29.615, 38.723]])
        helpers.compare_float_2d_arrays(bunch.durations, [
            [4.0, 4.0, 4.0, 4.0, 4.0],
            [0.0, 0.0, 0.0, 0.0, 0.0]])
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
            [6.0, 14.0, 19.0, 15.0, 17.0],
            ])

    @staticmethod
    @mark.unit_test
    def test_covariates_single_group(mocker):
        """ Test the get_covariates_single_group method """

        # Load test participant information
        test_file = join(Configuration()['directories']['test_data'], 'data',
            'participants', 'participants.tsv')
        participants_info = read_csv(test_file, sep='\t')

        # Run function
        subject_list = ['001', '002']
        covariates = PipelineTeam0I4U.get_covariates_single_group(subject_list, participants_info)
        assert covariates[0]['vector'] == [24.0, 25.0]
        assert covariates[0]['name'] == 'age'
        assert covariates[0]['centering'] == [1]
        assert covariates[1]['vector'] == [0.0, 0.0]
        assert covariates[1]['name'] == 'gender'
        assert covariates[1]['centering'] == [1]

        subject_list = ['003', '002']
        covariates = PipelineTeam0I4U.get_covariates_single_group(subject_list, participants_info)
        assert covariates[0]['vector'] == [25.0, 27.0]
        assert covariates[0]['name'] == 'age'
        assert covariates[0]['centering'] == [1]
        assert covariates[1]['vector'] == [0.0, 1.0]
        assert covariates[1]['name'] == 'gender'
        assert covariates[1]['centering'] == [1]

    @staticmethod
    @mark.unit_test
    def test_covariates_group_comp(mocker):
        """ Test the get_covariates_group_comp method """

        # Load test participant information
        test_file = join(Configuration()['directories']['test_data'], 'data',
            'participants', 'participants.tsv')
        participants_info = read_csv(test_file, sep='\t')

        # Run function
        subject_list_g1 = ['001', '002']
        subject_list_g2 = ['003', '004']
        covariates = PipelineTeam0I4U.get_covariates_group_comp(
            subject_list_g1, subject_list_g2, participants_info)
        assert covariates[0]['vector'] == [24.0, 25.0, 27.0, 25.0]
        assert covariates[0]['name'] == 'age'
        assert covariates[0]['centering'] == [1]
        assert covariates[1]['vector'] == [0.0, 0.0, 1.0, 0.0]
        assert covariates[1]['name'] == 'gender'
        assert covariates[1]['centering'] == [1]

        subject_list_g1 = ['004', '001']
        subject_list_g2 = ['003', '002']
        covariates = PipelineTeam0I4U.get_covariates_group_comp(
            subject_list_g1, subject_list_g2, participants_info)
        assert covariates[0]['vector'] == [24.0, 25.0, 25.0, 27.0]
        assert covariates[0]['name'] == 'age'
        assert covariates[0]['centering'] == [1]
        assert covariates[1]['vector'] == [0.0, 0.0, 0.0, 1.0]
        assert covariates[1]['name'] == 'gender'
        assert covariates[1]['centering'] == [1]

    @staticmethod
    @mark.pipeline_test
    def test_execution():
        """ Test the execution of a PipelineTeam0I4U and compare results """
        helpers.test_pipeline_evaluation('0I4U')
