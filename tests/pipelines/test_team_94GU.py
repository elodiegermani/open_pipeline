from os.path import join

from nipype import Workflow
from nipype.interfaces.spm import RealignUnwarp, NewSegment, Coregister, Normalize12, Smooth, FieldMap
from pytest import helpers, mark

from narps_open.pipelines.team_94GU import PipelineTeam94GU
from narps_open.pipelines.team_98BT import PipelineTeam98BT
from narps_open.utils.configuration import Configuration


class TestPipelinesTeam94GU:

    @staticmethod
    @mark.unit_test
    def test_create():
        """ Test the creation of a PipelineTeam2T6S object """

        pipeline = PipelineTeam94GU()

        # 1 - check the parameters
        assert pipeline.fwhm == 6.0
        assert pipeline.team_id == '94GU'

        # 2 - check workflows
        assert isinstance(pipeline.get_preprocessing(), Workflow)
        assert pipeline.get_run_level_analysis() is None
        assert pipeline.get_subject_level_analysis() is None
        assert pipeline.get_group_level_analysis() is None

    @staticmethod
    @mark.unit_test
    def test_extract_fieldmap_infos():

        filedmap_file_1 = join(
            Configuration()['directories']['test_data'], 'pipelines', 'phasediff_1.json')
        filedmap_file_2 = join(
            Configuration()['directories']['test_data'], 'pipelines', 'phasediff_2.json')

        test_result = PipelineTeam94GU.extract_fieldmap_infos(
            filedmap_file_1, ['magnitude_1', 'magnitude_2'])
        assert test_result[0] == (0.00492, 0.00738)
        assert test_result[1] == 'magnitude_1'
        test_result = PipelineTeam98BT.get_fieldmap_info(
            filedmap_file_2, ['magnitude_1', 'magnitude_2'])
        assert test_result[0] == (0.00492, 0.00738)
        assert test_result[1] == 'magnitude_2'

    @staticmethod
    @mark.unit_test
    def test_get_fieldmap():
        pipeline = PipelineTeam94GU()
        node = pipeline.get_fieldmap()
        assert isinstance(node.interface, FieldMap)

    @staticmethod
    @mark.unit_test
    def test_get_motion_correction():
        pipeline = PipelineTeam94GU()
        node = pipeline.get_motion_correction()
        assert isinstance(node.interface, RealignUnwarp)
        assert node.name == 'motion_correction'
        assert not node.inputs.register_to_mean

    @staticmethod
    @mark.unit_test
    def test_get_segmentation():
        pipeline = PipelineTeam94GU()
        node = pipeline.get_segmentation()
        assert isinstance(node.interface, NewSegment)
        assert node.name == 'segmentation'
        assert not node.inputs.register_to_mean

    @staticmethod
    @mark.unit_test
    def test_get_coregistration():
        pipeline = PipelineTeam94GU()
        node = pipeline.get_coregistration()
        assert isinstance(node.interface, Coregister)
        assert node.name == 'coregistration'
        assert node.inputs.cost_function == 'mi'

    @staticmethod
    @mark.unit_test
    def test_get_normalisation():
        pipeline = PipelineTeam94GU()
        node = pipeline.get_normalise()
        assert isinstance(node.interface, Normalize12)
        assert node.name == 'normalise'
        assert node.inputs.bias_regularization == 0.0001
        assert node.inputs.bias_fwhm == 60
        assert node.inputs.warping_regularization == [0, 0.001, 0.5, 0.05, 0.2]
        assert node.inputs.write_voxel_sizes == [2, 2, 2]

    @staticmethod
    @mark.unit_test
    def test_get_smoothing():
        pipeline = PipelineTeam94GU()
        node = pipeline.get_smoothing()
        assert isinstance(node.interface, Smooth)
        assert node.name == 'smoothing'
        assert node.inputs.fwhm == pipeline.fwhm

    @staticmethod
    @mark.pipeline_test
    def test_execution():
        """ Test the execution of a PipelineTeam94GU and compare results """
        helpers.test_pipeline_evaluation('94GU')
