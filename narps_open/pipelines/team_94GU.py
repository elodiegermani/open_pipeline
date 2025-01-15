from os.path import join

from nipype import Workflow, Node, IdentityInterface, SelectFiles, Function, DataSink
from nipype.algorithms.misc import Gunzip
from nipype.interfaces.spm import RealignUnwarp, FieldMap, Smooth, Normalize12, Coregister, NewSegment
from nipype.interfaces.spm.base import Info as SPMInfo

from narps_open.data.task import TaskInformation
from narps_open.pipelines import Pipeline


class PipelineTeam94GU(Pipeline):
    """ A class that defines the pipeline of team 94GU. """

    def __init__(self):
        super().__init__()
        self.fwhm = 6.0
        self.team_id = '94GU'
        self.prep_templates = {
            'anat': join('sub-{subject_id}', 'anat', 'sub-{subject_id}_T1w.nii.gz'),
            'func': join('sub-{subject_id}', 'func',
                         'sub-{subject_id}_task-MGT_run-{run_id}_bold.nii.gz'),
            'magnitude': join('sub-{subject_id}', 'fmap', 'sub-{subject_id}_magnitude*.nii.gz'),
            'phasediff': join('sub-{subject_id}', 'fmap', 'sub-{subject_id}_phasediff.nii.gz'),
            'info_fmap': join('sub-{subject_id}', 'fmap', 'sub-{subject_id}_phasediff.json')
        }
        self.sub_level_templates = {
            'func': join(self.directories.output_dir,
                         'preprocessing', '_run_id_*_subject_id_{subject_id}', 'smoothing',
                         'swuasub-{subject_id}_task-MGT_run-*_bold.nii')
        }
        self.group_level_templates = {}

    def get_src_infos(self):
        """
        Node to get subjects / runs
        """
        information_source = Node(IdentityInterface(
            fields=['subject_id', 'run_id']),
            name='information_source')
        information_source.iterables = [
            ('subject_id', self.subject_list), ('run_id', self.run_list)
        ]
        return information_source

    def get_select_files(self, template):
        """
        Node to iterate over subject / run files
        """
        node = Node(SelectFiles(template), name='select_files')
        node.inputs.base_directory = self.directories.dataset_dir
        return node

    def get_data_sink(self):
        # DataSink Node - store the wanted results in the wanted repository
        data_sink = Node(DataSink(), name='data_sink')
        data_sink.inputs.base_directory = self.directories.output_dir
        return data_sink

    def get_preprocessing(self):
        """
            Preprocessing workflow

            1) Fieldmap distortion calculation;
            2) functional Realignment & unwarp & phase correction (subject motion estimation and correction);
            3) functional Indirect Segmentation & Normalization (
                coregister functional/structural;
                structural segmentation & normalization;
                apply same deformation field to functional
                )
            6) functional Smoothing (spatial convolution with Gaussian kernel);
            7) Artifact and structured noise identification;

        """
        preprocessing = Workflow(
            base_dir=self.directories.working_dir,
            name='preprocessing')

        src_infos = self.get_src_infos()
        select_files = self.get_select_files(self.prep_templates)

        # Unzipping nodes
        unzip_anat = Node(Gunzip(), name='unzip_anat')
        unzip_func = Node(Gunzip(), name='unzip_func')
        unzip_magnitude = Node(Gunzip(), name='unzip_magnitude')
        unzip_phasediff = Node(Gunzip(), name='unzip_phasediff')

        # Iterate over subjects / runs files
        preprocessing.connect(src_infos, 'subject_id', select_files, 'subject_id')
        preprocessing.connect(src_infos, 'run_id', select_files, 'run_id')

        # select_files -> gunzip_anat, gunzip_func
        preprocessing.connect(select_files, 'anat', unzip_anat, 'in_file')
        preprocessing.connect(select_files, 'func', unzip_func, 'in_file')

        fieldmap_infos = self.get_fieldmap_infos()

        # Extract magnitude infos from file
        preprocessing.connect(select_files, 'info_fmap', fieldmap_infos, 'info_file')
        preprocessing.connect(select_files, 'magnitude', fieldmap_infos, 'magnitude_files')
        # Unzip magnitude file

        # FIELDMAP DISTORTION CALCULATION
        # inputs : echo_times + magnitude_file + phase_diff + func
        fieldmap = self.get_fieldmap()
        preprocessing.connect(fieldmap_infos, 'echo_times', fieldmap, 'echo_times')
        # input unzipped magnitude
        preprocessing.connect(fieldmap_infos, 'magnitude_file', unzip_magnitude, 'in_file')
        preprocessing.connect(unzip_magnitude, 'out_file', fieldmap, 'magnitude_file')
        # input unzipped phasediff
        preprocessing.connect(select_files, 'phasediff', unzip_phasediff, 'in_file')
        preprocessing.connect(unzip_phasediff, 'out_file', fieldmap, 'phase_file')
        # input unzipped functional
        preprocessing.connect(unzip_func, 'out_file', fieldmap, 'epi_file')
        # output : fieldmap

        # MOTION CORRECTION
        # inputs : fieldmap + func
        motion_correction = self.get_motion_correction()
        preprocessing.connect(fieldmap, 'vdm', motion_correction, 'phase_map')
        preprocessing.connect(unzip_func, 'out_file', motion_correction, 'in_files')
        # output : motion corrected func

        # SEGMENTATION
        # input : anat
        segmentation = self.get_segmentation()
        preprocessing.connect(unzip_anat, 'out_file', segmentation, 'channel_files')
        # output : segmented anat, transformation file

        # COREGISTRATION
        # inputs : motion corrected func + motion corrected mean func + anat
        coregistration = self.get_coregistration()
        preprocessing.connect(motion_correction, 'mean_image', coregistration, 'source')
        preprocessing.connect(motion_correction, 'realigned_unwarped_files', coregistration, 'apply_to_files')
        preprocessing.connect(unzip_anat, 'out_file', coregistration, 'target')
        # outputs : coregistered motion corrected func

        # NORMALISE
        # inputs : coregistered motion corrected func + transformation file
        normalise = self.get_normalise()
        preprocessing.connect(coregistration, 'coregistered_source', normalise, 'apply_to_files')
        preprocessing.connect(segmentation, 'forward_deformation_field', normalise, 'deformation_file')
        # output : normalised coregistered motion corrected func

        # SMOOTHING
        # input : normalised coregistered motion corrected func
        smoothing = self.get_smoothing()
        preprocessing.connect(normalise, 'normalized_files', smoothing, 'in_files')
        # output : preprocessed (smoothed normalised coregistered motion corrected) func

        return preprocessing

    def get_fieldmap_infos(self):
        """
        Node to return fieldmap infos in a workflow
        """
        # Function Node get_fieldmap_info -
        return Node(Function(
            function=self.extract_fieldmap_infos,
            input_names=['info_file', 'magnitude_files'],
            output_names=['echo_times', 'magnitude_file']),
            name='fieldmap_info')

    def extract_fieldmap_infos(info_file, magnitude_files):
        """
        Function to get information necessary to compute the fieldmap.

        Parameters:
            - fieldmap_info_file: str, file with fieldmap information
            - magnitude_files: list of str, list of magnitude files

        Returns:
            - echo_times: tuple of floats, echo time obtained from fieldmap information file
            - magnitude_file: str, necessary file to compute fieldmap
        """
        from json import load

        with open(info_file, 'rt') as file:
            fieldmap_info = load(file)

        echo_time_1 = float(fieldmap_info['EchoTime1'])
        echo_time_2 = float(fieldmap_info['EchoTime2'])

        short_echo_time = min(echo_time_1, echo_time_2)
        long_echo_time = max(echo_time_1, echo_time_2)

        magnitude_file = None
        if short_echo_time == echo_time_1:
            magnitude_file = magnitude_files[0]
        elif short_echo_time == echo_time_2:
            magnitude_file = magnitude_files[1]

        return (short_echo_time, long_echo_time), magnitude_file

    def get_fieldmap(self):
        """
        FieldMap() node for fieldmap distortion calculation;
        """

        # FieldMap Node -
        fieldmap = Node(FieldMap(), name='fieldmap')
        fieldmap.inputs.blip_direction = -1
        fieldmap.inputs.total_readout_time = TaskInformation()['TotalReadoutTime']
        return fieldmap

    def get_motion_correction(self) -> Node:
        """
        RealignUnwarp() node for func motion correction, distortion correction

        Motion correction was performed in SPM12 (realign and unwarp and the fielmap toolbox).
        Default parameters were used:
        least squares approach and a 6 parameter (rigid body) spatial transformation.
        Fieldmap-based unwarping was performed at this step (SPM12).
        Reference scan = 1st scan.
        Image similarity metric = normalised mutual information.
        Interpolation type: B-spline.
        """
        node = Node(RealignUnwarp(), name='motion_correction')
        node.inputs.register_to_mean = False

        return node

    def get_segmentation(self) -> Node:
        """
        NewSegment() node for anat segmentation

        Method used = the unified segmentation algorithm implemented in SPM12
        """

        node = Node(interface=NewSegment(), name="segmentation")

        spm_tissues_file = join(SPMInfo.getinfo()['path'], 'tpm', 'TPM.nii')
        tissue1 = [(spm_tissues_file, 1), 1, (True, False), (True, False)]
        tissue2 = [(spm_tissues_file, 2), 1, (True, False), (True, False)]
        tissue3 = [(spm_tissues_file, 3), 2, (True, False), (True, False)]
        tissue4 = [(spm_tissues_file, 4), 3, (True, False), (True, False)]
        tissue5 = [(spm_tissues_file, 5), 4, (True, False), (True, False)]
        tissue6 = [(spm_tissues_file, 6), 2, (True, False), (True, False)]
        tissue_list = [tissue1, tissue2, tissue3, tissue4, tissue5, tissue6]
        node.inputs.tissues = tissue_list

        node.inputs.write_deformation_fields = [True, True]

        return node

    def get_coregistration(self) -> Node:
        """
        Coregister() node for anat/func coregistration

        Coregistration was performed in SPM12 (coregister: estimate and reslice). Type of
        transformation: rigid body model. Cost function = mutual information. Interpolation
        method = B-spline.
        """
        node = Node(interface=Coregister(), name="coregistration")
        node.inputs.cost_function = 'mi'
        return node

    def get_normalise(self) -> Node:
        """
        Normalize12() node for func normalisation

        Normalisation was performed in SPM12 (normalise). Volume-based registration applied on
        T1, the resulting transformation map applied then to T2*. MNI/ICBM space template -
        European brains: T1, 2 mm. Choice of warp = nonlinear. Type of transformation = DCT.
        Warping regularisation parameters = 0 0.001 0.5 0.05 0.2
        Bias regularisation = very light regularisation (0.0001). Bias FWHM 60mm cutoff
        SPM12's mean centering
        """
        node = Node(interface=Normalize12(), name="normalise")
        node.inputs.jobtype='write'
        node.inputs.bias_regularization = 0.0001
        node.inputs.bias_fwhm = 60
        node.inputs.warping_regularization = [0, 0.001, 0.5, 0.05, 0.2]
        # node.inputs.affine_regularization_type = 'mni'
        node.inputs.write_voxel_sizes = [2, 2, 2]
        return node

    def get_smoothing(self):
        """
        Smooth() node for func smoothing

        Smoothing was performed in SPM12 (smooth: 8 mm FWHM). Fixed kernel. Performed in
        normalised volumes.
        """
        node = Node(interface=Smooth(), name="smoothing")
        node.inputs.fwhm = self.fwhm
        return node

    def get_run_level_analysis(self):
        """
        No run level analysis with SPM
        """
        return None

    def get_subject_level_analysis(self):
        subject_level_analysis = Workflow(
            base_dir=self.directories.working_dir,
            name='subject_level_analysis')

        src_infos = self.get_src_infos()
        select_files = self.get_select_files(self.sub_level_templates)
        return subject_level_analysis

    def get_group_level_analysis(self):
        # TODO
        return None

    def get_hypotheses_outputs(self):
        # TODO
        return None
