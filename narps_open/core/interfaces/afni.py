#!/usr/bin/python
# coding: utf-8

""" AFNI interfaces for Nipype """

from os.path import abspath

from nipype.interfaces.base import traits, File, Str, InputMultiPath, isdefined
from nipype.interfaces.afni.base import (
    AFNICommand,
    AFNICommandInputSpec,
    AFNICommandOutputSpec
)

class TtestppInputSpec(AFNICommandInputSpec):
    """ The input specification of the 3dttest++ interface """

    set_a_label = Str(
        desc='label for setA',
        argstr='-labelA %s ',
        mandatory=True
        )
    set_a = InputMultiPath(
        traits.Tuple(
            File(desc='3D dataset', exists=True),
            traits.Int(desc='Index of the data in the dataset'),
        ),
        desc='specifies a set of input datasets for setA + their label.',
        argstr='-setA %s ', # Data tuples will be formatted in the _format_arg method
        requires=['set_a_label'],
        mandatory=True
    )
    set_b_label = Str(
        desc='label for setB',
        argstr='-labelB %s ',
        )
    set_b = InputMultiPath(
        traits.Tuple(
            File(desc='3D dataset', exists=True),
            traits.Int(desc='Index of the data in the dataset'),
        ),
        desc='specifies a set of input datasets for setB + their label.',
        argstr='-setB %s ', # Data tuples will be formatted in the _format_arg method
        requires=['set_b_label'],
    )
    set_a_weight = File(
        desc='Name of a file with the weights for the -setA datasets.',
        argstr='-setweightA %s ',
        requires=['set_a'],
        exists=True,
        )
    set_b_weight = File(
        desc='Name of a file with the weights for the -setB datasets.',
        argstr='-setweightB %s ',
        requires=['set_b'],
        exists=True,
        )
    covariates = File(
        desc='name of a text file with a table for the covariate(s).'
        ' Each column in the file is treated as a separate covariate, and each'
        ' row contains the values of these covariates for one sample (dataset).',
        argstr='-covariates %s ',
        exists=True,
        )
    center = traits.Enum('NONE', 'DIFF', 'SAME',
        desc='how the mean across subjects of a covariate will be processed.',
        argstr='-center %s ',
        requires=['covariates'],
        )
    paired = traits.Bool(
        desc='specifies the use of a paired-sample t-test to compare setA and setB.',
        argstr='-paired ',
        requires=['set_a', 'set_b'],
    )
    unpooled = traits.Bool(
        desc='specifies that the variance estimates for setA and setB be computed '
        'separately (not pooled together).',
        argstr='-paired ',
        requires=['set_a', 'set_b'],
        xor=['paired', 'covariates']
    )
    toz = traits.Bool(
        desc='convert output t-statistics to z-scores.',
        argstr='-toz ',
    )
    rankize = traits.Bool(
        desc='convert the data (and covariates, if any) into ranks before '
        'doing the 2-sample analyses.',
        argstr='-rankize ',
    )
    no1sam = traits.Bool(
        desc='do not calculate 1-sample test results when '
        'doing 2-sample analyses.',
        argstr='-no1sam ',
    )
    nomeans = traits.Bool(
        desc='turn off output of the `mean` sub-bricks.',
        argstr='-nomeans ',
    )
    notests = traits.Bool(
        desc='turn off output of the `test` sub-bricks.',
        argstr='-notests ',
    )
    mask = File(
        desc='Only compute results for voxels in the specified mask.',
        argstr='-mask %s ',
        exists=True,
    )
    exblur = traits.Float(
        desc='Before doing the t-test, apply some extra blurring to the input datasets; '
        "parameter 'b' is the Gaussian FWHM of the smoothing kernel (in mm).",
        argstr='-exblur %d ',
    )
    brickwise = traits.Bool(
        desc='carry out t-tests sub-brick by sub-brick',
        argstr='-brickwise ',
        position=0
    )
    out_file = Str(
        desc='the name of the output dataset file.',
        argstr='-prefix %s ',
        position=-1
        )
    out_residuals = Str(
        desc='output the residuals into a dataset with given prefix.',
        argstr='-resid %s ',
        position=-2
        )
    clustsim = traits.Bool(
        desc='run the cluster-size threshold simulation program 3dClustSim.',
        argstr='-Clustsim ',
        position=-4
    )
    seed = traits.Tuple(
        traits.Int, traits.Int,
        desc='This option is used to set the random number seed for'
        '`-randomsign` to the first positive integer. If a second integer'
        'follows, then that value is used for the random number seed for `-permute`.',
        argstr='-seed %d %d ',
        requires=['clustsim'],
        position=-3
    )

class Ttestpp(AFNICommand):
    """ Gosset (Student) t-test of sets of 3D datasets.

    For complete details, see the `3dttest++ Documentation.
    <https://afni.nimh.nih.gov/pub/dist/doc/program_help/3dttest++.html>`_
    """

    _cmd = '3dttest++'
    input_spec = TtestppInputSpec
    output_spec = AFNICommandOutputSpec

    def _format_arg(self, name, trait_spec, value):
        """ Format arguments before actually building the command line """
        out_value = value

        # For arguments -setA and -setB, we want a list such as :
        #      dataset1'[index]' dataset2'[index]' dataset3'[index]' ...
        if name in ['set_a', 'set_b']:
            out_value = ''
            for set_tuple in value:
                out_value += f'{set_tuple[0]}\'[{set_tuple[1]}]\' '
            out_value = [out_value] # Return a list as the input value

        return super()._format_arg(name, trait_spec, out_value)

    def _list_outputs(self):
        outputs = self.output_spec().get()

        for key in outputs.keys():
            if isdefined(self.inputs.get()[key]):
                outputs[key] = abspath(self.inputs.get()[key])

        return outputs

class SelectSBInputSpec(AFNICommandInputSpec):
    """ The input specification for SelectSubBrick """
    in_file = File(
        desc = 'File name to select a subbrick from.',
        argstr = '%s',
        position = -2,
        mandatory = True,
        copyfile = False,
        exists = True
    )
    index = traits.Int(
        desc = 'Index of the subbrick inside in_file.',
        mandatory = True
    )
    out_file = File(desc = 'Output image file name.', argstr = '-prefix %s', genfile = True)

class SelectSubBrick(AFNICommand):
    """ Sub-brick selection from AFNI files.

    For complete details, see the `3dTcat Documentation.
    <https://afni.nimh.nih.gov/pub/dist/doc/program_help/3dTcat.html>
    """

    _cmd = '3dTcat'
    input_spec = SelectSBInputSpec
    output_spec = AFNICommandOutputSpec

    #def _gen_filename(self, name):
    #    if name == 'out_file':
    #        return self._gen_fname(self.inputs.in_file, suffix = '_tcat')

    def _list_outputs(self):
        outputs = self.output_spec().get()

        for key in outputs.keys():
            if isdefined(self.inputs.get()[key]):
                outputs[key] = abspath(self.inputs.get()[key])

        return outputs

    def _format_arg(self, name, trait_spec, value):
        """ Format arguments before actually building the command line """
        out_value = value

        # For argument in_file, append index, such as : in_file'[index]'
        if name == 'in_file':
            out_value = f'{value}\'[{self.inputs.index}]\''

        return super()._format_arg(name, trait_spec, out_value)
