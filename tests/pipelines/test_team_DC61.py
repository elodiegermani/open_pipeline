#!/usr/bin/python
# coding: utf-8

""" Tests of the 'narps_open.pipelines.team_DC61' module.

Launch this test with PyTest

Usage:
======
    pytest -q test_team_DC61.py
    pytest -q test_team_DC61.py -k <selected_test>
"""
from os.path import join, exists
from filecmp import cmp

from pytest import helpers, mark, fixture
from nipype import Workflow
from nipype.interfaces.base import Bunch

from narps_open.utils.configuration import Configuration
from narps_open.pipelines.team_DC61 import PipelineTeamDC61

@fixture
def mock_participants_data(mocker):
    """ A fixture to provide mocked data from the test_data directory """

    mocker.patch(
        'narps_open.data.participants.Configuration',
        return_value = {
            'directories': {
                'dataset': join(
                    Configuration()['directories']['test_data'],
                    'data', 'participants')
                }
            }
    )

class TestPipelinesTeamDC61:
    """ A class that contains all the unit tests for the PipelineTeamDC61 class."""

    @staticmethod
    @mark.unit_test
    def test_create():
        """ Test the creation of a PipelineTeamDC61 object """

        pipeline = PipelineTeamDC61()

        # 1 - check the parameters
        assert pipeline.fwhm == 5.0
        assert pipeline.team_id == 'DC61'

        # 2 - check workflows
        assert pipeline.get_preprocessing() is None
        assert pipeline.get_run_level_analysis() is None
        assert isinstance(pipeline.get_subject_level_analysis(), Workflow)
        group_level = pipeline.get_group_level_analysis()
        assert len(group_level) == 2
        for sub_workflow in group_level:
            assert isinstance(sub_workflow, Workflow)

    @staticmethod
    @mark.unit_test
    def test_outputs():
        """ Test the expected outputs of a PipelineTeamDC61 object """
        pipeline = PipelineTeamDC61()
        # 1 - 1 subject outputs
        pipeline.subject_list = ['001']
        helpers.test_pipeline_outputs(pipeline, [0, 0, 3, 7*2 + 4*2, 18])

        # 2 - 4 subjects outputs
        pipeline.subject_list = ['001', '002', '003', '004']
        helpers.test_pipeline_outputs(pipeline, [0, 0, 12, 7*2 + 4*2, 18])

    @staticmethod
    @mark.unit_test
    def test_subject_information():
        """ Test the get_subject_information method """

        # Get test files
        test_file = join(Configuration()['directories']['test_data'], 'pipelines', 'events.tsv')
        bunch = PipelineTeamDC61.get_subject_information(test_file, 1)

        # Compare bunches to expected
        assert isinstance(bunch, Bunch)
        assert bunch.conditions == ['gamble_run1']
        helpers.compare_float_2d_arrays(bunch.onsets, [[4.071, 11.834, 19.535, 27.535, 36.435]])
        helpers.compare_float_2d_arrays(bunch.durations, [[4.0, 4.0, 4.0, 4.0, 4.0]])
        assert bunch.amplitudes is None
        assert bunch.tmod is None
        assert bunch.pmod[0].name == ['gain_param', 'loss_param', 'rt_param']
        assert bunch.pmod[0].poly == [1, 1, 1]
        helpers.compare_float_2d_arrays(bunch.pmod[0].param, [
            [14.0, 34.0, 38.0, 10.0, 16.0],
            [6.0, 14.0, 19.0, 15.0, 17.0],
            [2.388, 2.289, 0.0, 2.08, 2.288]
            ])
        assert bunch.regressor_names is None
        assert bunch.regressors is None

    @staticmethod
    @mark.unit_test
    def test_confounds_file(temporary_data_dir):
        """ Test the get_confounds_file method """

        confounds_file = join(
            Configuration()['directories']['test_data'], 'pipelines', 'confounds.tsv')
        reference_file = join(
            Configuration()['directories']['test_data'], 'pipelines', 'team_DC61', 'confounds.tsv')

        # Get new confounds file
        PipelineTeamDC61.get_confounds_file(confounds_file, 'sid', 'rid', temporary_data_dir)

        # Check confounds file was created
        created_confounds_file = join(
            temporary_data_dir, 'confounds_files', 'confounds_file_sub-sid_run-rid.tsv')
        assert exists(created_confounds_file)

        # Check contents
        assert cmp(reference_file, created_confounds_file)

    @staticmethod
    @mark.unit_test
    def test_group_level_contrasts():
        """ Test the get_group_contrasts method """

        # Wrong parameter
        assert PipelineTeamDC61.get_group_level_contrasts('wrong') is None

        # effect_of_gain parameter
        assert PipelineTeamDC61.get_group_level_contrasts('effect_of_gain') == [
            ['gain_param_range', 'T', ['equalIndifference', 'equalRange'], [0, 1]],
            ['gain_param_indiff', 'T', ['equalIndifference', 'equalRange'], [1, 0]]
        ]

        # effect_of_loss parameter
        assert PipelineTeamDC61.get_group_level_contrasts('effect_of_loss') == [
            ['loss_param_range', 'T', ['equalIndifference', 'equalRange'], [0, 1]],
            ['loss_param_indiff', 'T', ['equalIndifference', 'equalRange'], [1, 0]],
            ['loss_param_range_f', 'F', [['loss_param_range', 'T', ['equalIndifference', 'equalRange'], [0, 1]]]],
            ['loss_param_indiff_f', 'F', [['loss_param_indiff', 'T', ['equalIndifference', 'equalRange'], [1, 0]]]]
        ]

    @staticmethod
    @mark.unit_test
    def test_group_covariates(mock_participants_data):
        """ Test the get_group_covariates method """
        subjects = ['001', '002', '003', '004']
        assert PipelineTeamDC61.get_group_covariates(subjects) == [
            dict(vector = [0, 1, 0, 1], name = 'equalRange'),
            dict(vector = [1, 0, 1, 0], name = 'equalIndifference')
        ]
        subjects = ['001', '003', '002', '004']
        assert PipelineTeamDC61.get_group_covariates(subjects) == [
            dict(vector = [0, 1, 0, 1], name = 'equalRange'),
            dict(vector = [1, 0, 1, 0], name = 'equalIndifference')
        ]

    @staticmethod
    @mark.pipeline_test
    def test_execution():
        """ Test the execution of a PipelineTeamDC61 and compare results """
        helpers.test_pipeline_evaluation('DC61')
