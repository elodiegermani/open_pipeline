#!/usr/bin/python
# coding: utf-8

""" A command line tool for the narps_open.utils.export module """

import os
from os.path import join, exists, basename
import shutil
from argparse import ArgumentParser

from narps_open.utils.configuration import Configuration
from narps_open.pipelines import get_implemented_pipelines
from narps_open.runner import PipelineRunner


# Derived Class Cleaner or only add method
class PipelineExporter(PipelineRunner):
    def get_export_filename(i):
        """Get NARPS compliant filename based on the position in the fixed list files

        """
        hypothesis = str(i // 2 + 1) # 2 files per hypothesis starting at 1
        suffix = "" if i%2 == 0 else "un" #even thresholded odd unthresholded
        export_filename = f"hypo_{hypothesis}_{suffix}thresh.nii.gz"
        return export_filename

def get_export_filename(i):
    """Get NARPS compliant filename based on the position in the fixed list files

    """
    hypothesis = str(i // 2 + 1)  # 2 files per hypothesis starting at 1
    suffix = "" if i % 2 == 0 else "un"  # even thresholded odd unthresholded
    export_filename = f"hypo_{hypothesis}_{suffix}thresh.nii.gz"
    return export_filename


def main():
    """ Entry-point for the command line tool narps_open_export """

    # Parse arguments
    parser = ArgumentParser(description = 'Export group level NARPS reproduced results into BIDS format')
    parser.add_argument('-t', '--team', type = str, required = True,
        help = 'the team ID', choices = get_implemented_pipelines())
    parser.add_argument('-n', '--nsubjects', type = int, required = True,
        help='the number of subjects to be selected')
    arguments = parser.parse_args()

    # Initialize pipeline
    runner = PipelineRunner(arguments.team)
    runner.pipeline.directories.dataset_dir = Configuration()['directories']['dataset']
    runner.pipeline.directories.results_dir = Configuration()['directories']['reproduced_results']
    runner.pipeline.directories.set_output_dir_with_team_id(arguments.team)
    runner.pipeline.directories.set_working_dir_with_team_id(arguments.team)
    # should I use export files with team_id
    runner.nb_subjects = arguments.nsubjects


    # Retrieve the paths to the reproduced files
    reproduced_files = runner.pipeline.get_hypotheses_outputs()
    # Not statisfactory !
    # TODO: a group of minimun XXXXX subjects can be exported
    # TODO have a hash based on the exact subjects list
    # TODO: full dataset should be the default case

    export_dir = join(runner.pipeline.directories.results_dir, "group-level", runner.pipeline.team_id, f"nbsub-{str(len(runner.nb_subjects))}")
    if not exists(export_dir):
        os.makedirs(export_dir)
    for i, file in enumerate(reproduced_files):
        export_file = join(export_dir, get_export_filename(i))
        # TODO use datalad instead (installation will be messier)
        shutil.copy2(file, export_file)









if __name__ == '__main__':
    main()
