#!/usr/bin/python
# coding: utf-8

"""
conftest.py file will be automatically launched before running
pytest on (a) test file(s) in the same directory.
"""

from os import remove
from os.path import join, isfile

from pytest import helpers

from narps_open.runner import PipelineRunner
from narps_open.utils import get_subject_id
from narps_open.utils.correlation import get_correlation_coefficient
from narps_open.utils.configuration import Configuration
from narps_open.data.results import ResultsCollection

# Init configuration, to ensure it is in testing mode
Configuration(config_type='testing')

@helpers.register
def test_pipeline_execution(
    team_id: str,
    nb_subjects: int = 4
    ):
    """ This pytest helper allows to launch a pipeline over a given number of subjects

    Arguments:
        - team_id: str, the ID of the team (allows to identify which pipeline to run)
        - nb_subjects: int, the number of subject to run the pipeline with

    Returns:
        - list(float) the correlation coefficients between the following
        (reference and computed) files:

    This function can be used as follows:
        results = pytest.helpers.test_pipeline('2T6S', 4)
        assert statistics.mean(results) > .003

    TODO : how to keep intermediate files of the low level for the next numbers of subjects ?
        - keep intermediate levels : boolean in PipelineRunner
    """

    # Initialize the pipeline
    runner = PipelineRunner(team_id)
    runner.nb_subjects = nb_subjects
    runner.pipeline.directories.dataset_dir = Configuration()['directories']['dataset']
    runner.pipeline.directories.results_dir = Configuration()['directories']['reproduced_results']
    runner.pipeline.directories.set_output_dir_with_team_id(team_id)
    runner.pipeline.directories.set_working_dir_with_team_id(team_id)
    runner.start(True, False)

    # Run as long as there are missing files after first level (with a max number of trials)
    # TODO : this is a workaround
    for _ in range(Configuration()['runner']['nb_trials']):

        # Get missing subjects
        missing_subjects = set()
        for file in runner.get_missing_first_level_outputs():
            missing_subjects.append(get_subject_id(file))

        # Restart pipeline
        runner.subjects = missing_subjects
        runner.start(True, False)

    # Check missing files for the last time
    missing_files = runner.get_missing_first_level_outputs()
    if missing_files:
        print('Missing files:', missing_files)
        raise Exception('There are missing files for first level analysis.')

    # Start pipeline for the group level only
    runner.nb_subjects = nb_subjects
    runner.start(False, True)

    # Retrieve the paths to the reproduced files
    reproduced_files = runner.pipeline.get_hypotheses_outputs()

    # Retrieve the paths to the results files
    collection = ResultsCollection(team_id)
    results_files = [join(collection.directory, f) for f in collection.files.values()]

    # Get unthresholded maps only
    indices = [1, 3, 5, 7, 9, 11, 13, 15, 17]
    reproduced_files = [reproduced_files[i] for i in indices]
    results_files = [results_files[i] for i in indices]

    # Compute the correlation coefficients
    return [
        get_correlation_coefficient(reproduced_file, results_file)
        for reproduced_file, results_file in zip(reproduced_files, results_files)
        ]

@helpers.register
def test_correlation_results(values: list, nb_subjects: int) -> bool:
    """ This pytest helper returns True if all values in `values` are greater than
        expected values. It returns False otherwise.

        Arguments:
        - values, list of 9 floats: a list of correlation values for the 9 hypotheses of NARPS
        - nb_subjects, int: the number of subject used to compute the correlation values
    """
    if nb_subjects < 21:
        expected = [0.30 for _ in range(9)]
    elif nb_subjects < 41:
        expected = [0.70 for _ in range(9)]
    elif nb_subjects < 61:
        expected = [0.80 for _ in range(9)]
    elif nb_subjects < 81:
        expected = [0.85 for _ in range(9)]
    else:
        expected = [0.93 for _ in range(9)]

    return False not in [v > e for v, e in zip(values, expected)]

@helpers.register
def test_pipeline_evaluation(team_id: str):
    """ Test the execution of a Pipeline and compare with results.
        Arguments:
        - team_id, str: the id of the team for which to test the pipeline

        Return: True if the correlation coefficients between reproduced data and results
            meet the expectations, False otherwise.
    """

    file_name = f'test_pipeline-{team_id}.txt'
    if isfile(file_name):
        remove(file_name)

    for subjects in [4]: #[20, 40, 60, 80, 108]:
        # Execute pipeline
        results = helpers.test_pipeline(team_id, subjects)

        # Compute correlation with results
        passed = helpers.test_correlation_results(results, subjects)

        # Write values in a file
        with open(file_name, 'a', encoding = 'utf-8') as file:
            file.write(f'{team_id} | {subjects} subjects | {results} | {passed}\n')

        assert passed
