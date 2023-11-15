#!/usr/bin/python
# coding: utf-8

""" Tests of the 'narps_open.pipelines.team_08MQ' module.

Launch this test with PyTest

Usage:
======
    pytest -q test_team_08MQ.py
    pytest -q test_team_08MQ.py -k <selected_test>
"""

from pytest import helpers, mark
from nipype import Workflow

from narps_open.pipelines.team_08MQ import PipelineTeam08MQ

class TestPipelinesTeam08MQ:
    """ A class that contains all the unit tests for the PipelineTeam08MQ class."""

    @staticmethod
    @mark.unit_test
    def test_create():
        """ Test the creation of a PipelineTeam08MQ object """

        pipeline = PipelineTeam08MQ()

        # 1 - check the parameters
        assert pipeline.fwhm == 6.0
        assert pipeline.team_id == '08MQ'

        # 2 - check workflows
        assert isinstance(pipeline.get_preprocessing(), Workflow)
        assert isinstance(pipeline.get_run_level_analysis(), Workflow)
        assert isinstance(pipeline.get_subject_level_analysis(), Workflow)

        group_level = pipeline.get_group_level_analysis()
        assert len(group_level) == 3
        for sub_workflow in group_level:
            assert isinstance(sub_workflow, Workflow)

    @staticmethod
    @mark.unit_test
    def test_outputs():
        """ Test the expected outputs of a PipelineTeam08MQ object """
        pipeline = PipelineTeam08MQ()
        # 1 - 1 subject outputs
        pipeline.subject_list = ['001']
        assert len(pipeline.get_preprocessing_outputs()) == 3*4
        assert len(pipeline.get_run_level_outputs()) == 8+4*3*4
        assert len(pipeline.get_subject_level_outputs()) == 4*3
        assert len(pipeline.get_group_level_outputs()) == 0
        assert len(pipeline.get_hypotheses_outputs()) == 18

        # 2 - 4 subjects outputs
        pipeline.subject_list = ['001', '002', '003', '004']
        assert len(pipeline.get_preprocessing_outputs()) == 3*4*4
        assert len(pipeline.get_run_level_outputs()) == (8+4*3*4)*4
        assert len(pipeline.get_subject_level_outputs()) == 4*3*4
        assert len(pipeline.get_group_level_outputs()) == 0
        assert len(pipeline.get_hypotheses_outputs()) == 18

    @staticmethod
    @mark.unit_test
    def test_subject_information():
        """ Test the get_subject_information method """

    @staticmethod
    @mark.unit_test
    def test_run_level_contrasts():
        """ Test the get_run_level_contrasts method """
        contrasts = PipelineTeam08MQ().get_run_level_contrasts()

        assert contrasts[0] == ('positive_effect_gain', 'T', ['gain', 'loss'], [1, 0]),
        assert contrasts[0] == ('positive_effect_loss', 'T', ['gain', 'loss'], [0, 1]),
        assert contrasts[0] == ('negative_effect_loss', 'T', ['gain', 'loss'], [0, -1]),

    @staticmethod
    @mark.unit_test
    def test_subgroups_contrasts():
        """ Test the get_subgroups_contrasts method """

        #contrasts = PipelineTeam08MQ().get_subgroups_contrasts()
        #copes, varcopes, subject_list: list, participants_file: str

    @staticmethod
    @mark.unit_test
    def test_one_sample_t_test_regressors():
        """ Test the get_one_sample_t_test_regressors method """

        regressors = PipelineTeam08MQ().get_one_sample_t_test_regressors(['001', '002'])
        assert regressors == [1, 1]

    @staticmethod
    @mark.unit_test
    def test_two_sample_t_test_regressors():
        """ Test the get_two_sample_t_test_regressors method """

        regressors, groups = PipelineTeam08MQ().get_two_sample_t_test_regressors(
            ['001', '003'], # equalRange group
            ['002', '004'], # equalIndifference group
            ['001', '002', '003', '004'] # all subjects
            )
        assert regressors == dict(
                equalRange = [1, 0, 1, 0],
                equalIndifference = [0, 1, 0, 1]
            )
        assert groups == [1, 2, 1, 2]

    @staticmethod
    @mark.pipeline_test
    def test_execution():
        """ Test the execution of a PipelineTeam08MQ and compare results """
        helpers.test_pipeline_evaluation('08MQ')
