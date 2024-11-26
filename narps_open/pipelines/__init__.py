#!/usr/bin/python
# coding: utf-8

""" Interfaces that declare operations and parameters common to all pipelines. """

from os.path import join
from abc import ABC, abstractmethod

# List all the available pipelines and the corresponding class for each
implemented_pipelines = {
    '08MQ': 'PipelineTeam08MQ',
    '0C7Q': None,
    '0ED6': None,
    '0H5E': None,
    '0I4U': None,
    '0JO0': None,
    '16IN': None,
    '1K0E': None,
    '1KB2': None,
    '1P0Y': None,
    '27SS': None,
    '2T6S': 'PipelineTeam2T6S',
    '2T7P': None,
    '3C6G': None,
    '3PQ2': None,
    '3TR7': 'PipelineTeam3TR7',
    '43FJ': None,
    '46CD': None,
    '4SZ2': 'PipelineTeam4SZ2',
    '4TQ6': 'PipelineTeam4TQ6',
    '50GV': None,
    '51PW': 'PipelineTeam51PW',
    '5G9K': None,
    '6FH5': None,
    '6VV2': None,
    '80GC': None,
    '94GU': None,
    '98BT': 'PipelineTeam98BT',
    '9Q6R': None,
    '9T8E': None,
    '9U7M': None,
    'AO86': None,
    'B23O': None,
    'B5I6': 'PipelineTeamB5I6',
    'B23O': 'PipelineTeamB23O',
    'B5I6': 'PipelineTeamB5I6',
    'C22U': None,
    'C88N': 'PipelineTeamC88N',
    'DC61': None,
    'E3B6': None,
    'E6R3': None,
    'I07H': None,
    'I52Y': None,
    'I9D6': None,
    'IZ20': None,
    'J7F9': 'PipelineTeamJ7F9',
    'K9P0': None,
    'L1A8': None,
    'L3V8': None,
    'L7J7': 'PipelineTeamL7J7',
    'L9G5': None,
    'O03M': None,
    'O21U': 'PipelineTeamO21U',
    'O6R6': 'PipelineTeamO6R6',
    'P5F3': None,
    'Q58J': None,
    'Q6O0': 'PipelineTeamQ6O0',
    'R42Q': None,
    'R5K7': None,
    'R7D1': None,
    'R9K3': 'PipelineTeamR9K3',
    'SM54': None,
    'T54A': 'PipelineTeamT54A',
    'U26C': 'PipelineTeamU26C',
    'UI76': None,
    'UK24': 'PipelineTeamUK24',
    'V55J': None,
    'VG39': None,
    'X19V': 'PipelineTeamX19V',
    'X1Y5': None,
    'X1Z4': None,
    'XU70': None
}

def get_implemented_pipelines() -> list:
    """ Return a list of team IDs whose pipeline is implemented in NARPS open pipelines """
    return [team for team, value in implemented_pipelines.items() if value is not None]

def get_not_implemented_pipelines() -> list:
    """ Return a list of team IDs whose pipeline is not implemented in NARPS open pipelines """
    return [team for team, value in implemented_pipelines.items() if value is None]

class PipelineDirectories():
    """ This object contains paths to the directories of interest for a Pipeline """

    def __init__(self):
        """ Attributes (properties) of class PipelineDirectories are:
            - dataset_dir: str, directory where the ds001734 dataset is stored
            - results_dir: str, base directory for results to be stored
            - working_dir: str, directory where to store intermediate results
            - output_dir: str, directory for final results
        """
        self._dataset_dir = ''
        self._results_dir = ''
        self._working_dir = ''
        self._output_dir = ''

    @property
    def dataset_dir(self) -> str:
        """ Getter for property dataset_dir """
        return self._dataset_dir

    @dataset_dir.setter
    def dataset_dir(self, dir_name: str) -> None:
        """ Setter for property dataset_dir """
        self._dataset_dir = dir_name

    @property
    def results_dir(self) -> str:
        """ Getter for property results_dir """
        return self._results_dir

    @results_dir.setter
    def results_dir(self, dir_name: str) -> None:
        """ Setter for property results_dir """
        self._results_dir = dir_name

    @property
    def working_dir(self) -> str:
        """ Getter for property working_dir """
        return self._working_dir

    @working_dir.setter
    def working_dir(self, dir_name: str) -> None:
        """ Setter for property working_dir """
        self._working_dir = dir_name

    def set_working_dir_with_team_id(self, team_id: str) -> None:
        """ An alternative setter for working_dir,
            to automatically set its path according to the team ID """
        if self.results_dir == '':
            raise AttributeError('PipelineDirectories :\
            set results_dir before using set_working_dir_with_team_id()')

        self._working_dir = join(
            self.results_dir,f'NARPS-{team_id}-reproduced','intermediate_results')

    @property
    def output_dir(self) -> str:
        """ Getter for property output_dir """
        return self._output_dir

    @output_dir.setter
    def output_dir(self, dir_name: str) -> None:
        """ Setter for property output_dir """
        self._output_dir = dir_name

    def set_output_dir_with_team_id(self, team_id: str) -> None:
        """ An alternative setter for output_dir,
            to automatically set its path according to the team ID """
        if self.results_dir == '':
            raise AttributeError('PipelineDirectories :\
            set results_dir before using set_output_dir_with_team_id()')

        self._output_dir = join(self.results_dir, f'NARPS-{team_id}-reproduced')

class Pipeline(ABC):
    """ An abstract class from which pipelines can inherit. """

    @abstractmethod
    def __init__(self):
        """ Attributes of class Pipeline are:
        # Directories
            - directories: PipelineDirectories, an object that contains all the paths of interest
            for the pipeline

        # Lists of data
            - subject_list: list of str, list of subject for which
            you want to do the subject level analysis
            - run_list: list of str, list of runs for which
            you want to do the subject level analysis
            - contrast_list: list of str, list of contrasts for which
            you want to do the group level analysis

        # Parameters
            - team_id: str, identifier of the team responsible for the pipeline
            - fwhm: float, Full width at half maximum (in mm) for the Gaussian smoothing kernel
            - tr: float, time repetition (in s) used during acquisition. This value is the same
            for all pipelines as they use the same dataset.
        """
        # Directories
        self._directories = PipelineDirectories()

        # Data
        self._subject_list = []
        self._run_list = ['01', '02', '03', '04']
        self._constrast_list = []

        # Parameters
        self._team_id = ''
        self._fwhm = 0.0
        self._tr = 1.0

    @property
    def directories(self):
        """ Getter for property directories """
        return self._directories

    @directories.setter
    def directories(self, value: PipelineDirectories):
        """ Setter for property directories """
        self._directories = value

    @property
    def subject_list(self):
        """ Getter for property subject_list """
        return self._subject_list

    @subject_list.setter
    def subject_list(self, value: list):
        """ Setter for property subject_list """
        self._subject_list = value

    @property
    def run_list(self):
        """ Getter for property run_list """
        return self._run_list

    @run_list.setter
    def run_list(self, value: list):
        """ Setter for property run_list """
        self._run_list = value

    @property
    def contrast_list(self):
        """ Getter for property contrast_list """
        return self._contrast_list

    @contrast_list.setter
    def contrast_list(self, value: list):
        """ Setter for property contrast_list """
        self._contrast_list = value

    @property
    def team_id(self):
        """ Getter for property team_id """
        return self._team_id

    @team_id.setter
    def team_id(self, value):
        """ Setter for property team_id """
        self._team_id = value

    @property
    def tr(self):
        """ Getter for property tr """
        return self._tr

    @property
    def fwhm(self):
        """ Getter for property fwhm """
        return self._fwhm

    @fwhm.setter
    def fwhm(self, value):
        """ Setter for property fwhm """
        self._fwhm = value

    @abstractmethod
    def get_preprocessing(self):
        """ Return a Nipype workflow describing the prerpocessing part of the pipeline """

    @abstractmethod
    def get_run_level_analysis(self):
        """ Return a Nipype workflow describing the run level analysis part of the pipeline """

    @abstractmethod
    def get_subject_level_analysis(self):
        """ Return a Nipype workflow describing the subject level analysis part of the pipeline """

    @abstractmethod
    def get_group_level_analysis(self):
        """ Return a Nipype workflow describing the group level analysis part of the pipeline """

    def get_preprocessing_outputs(self):
        """ Return the names of the files the preprocessing is supposed to generate. """
        return []

    def get_run_level_outputs(self):
        """ Return the names of the files the run level analysis is supposed to generate. """
        return []

    def get_subject_level_outputs(self):
        """ Return the names of the files the subject level analysis is supposed to generate. """
        return []

    def get_group_level_outputs(self):
        """ Return the names of the files the group level analysis is supposed to generate. """
        return []

    @abstractmethod
    def get_hypotheses_outputs(self):
        """ Return the names of the files used by the team to answer the hypotheses of NARPS.
            Files must be in the following order:
            hypo1_thresh.nii.gz
            hypo1_unthresh.nii.gz
            hypo2_thresh.nii.gz
            hypo2_unthresh.nii.gz
            hypo3_thresh.nii.gz
            hypo3_unthresh.nii.gz
            hypo4_thresh.nii.gz
            hypo4_unthresh.nii.gz
            hypo5_thresh.nii.gz
            hypo5_unthresh.nii.gz
            hypo6_thresh.nii.gz
            hypo6_unthresh.nii.gz
            hypo7_thresh.nii.gz
            hypo7_unthresh.nii.gz
            hypo8_thresh.nii.gz
            hypo8_unthresh.nii.gz
            hypo9_thresh.nii.gz
            hypo9_unthresh.nii.gz
        """
