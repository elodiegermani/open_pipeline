#!/usr/bin/python
# coding: utf-8

""" This module allows to get Neurovault collections corresponding
    to results from teams involed in NARPS
"""

from os import makedirs
from os.path import join
from json import loads
from urllib.request import urlretrieve, urlopen

from narps_open.utils.configuration import Configuration
from narps_open.data.description import TeamDescription
from narps_open.utils import show_download_progress

class ResultsCollection():
    """ Represents a Neurovault collections corresponding
        to results from teams involed in NARPS.
    """

    def __init__(self, team_id: str):
        # Initialize attributes
        self.team_id = team_id
        self.uid = self.get_uid()
        self.directory = join(
            Configuration()['directories']['narps_results'],
            'orig',
            self.uid + '_' + self.team_id
            )
        self.files = self.get_file_urls()

    def get_uid(self):
        """ Return the uid of the collection by browsing the team desription """
        return TeamDescription(team_id = self.team_id).general['NV_collection_link'].split('/')[-2]

    def get_file_urls(self):
        """ Return a dict containing the download url for each file of the collection.
        * dict key is the file base name (with no extension)
        * dict value is the download url for the file on Neurovault
        """

        # Get the images data from Neurovault's API
        collection_url = 'https://neurovault.org/api/collections/' + self.uid + '/images/'

        with urlopen(collection_url) as response:
            json = loads(response.read())

            file_urls = {}
            for result in json['results']:
                # Get data for a file in the collection
                file_urls[result['name']] = result['file']

        return file_urls

    def download(self):
        """ Download the collection, file by file. """

        # Create download directory if not existing
        makedirs(self.directory, exist_ok = True)

        # Download dataset
        print('Collecting results for team', self.team_id)
        for file_name, file_url in self.files.items():
            urlretrieve(
                file_url,
                join(self.directory, file_name+'.nii.gz'),
                show_download_progress
                )
