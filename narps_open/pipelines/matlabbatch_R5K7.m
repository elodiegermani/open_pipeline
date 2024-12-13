% first-level job ----

% $ narps_description -t R5K7 -d preprocessing --json

clear matlabbatch;

% 1) motion correction

% "motion_correction": "SPM12, Realign & Unwarp using the phase map 
% generated from the fieldmap data with SPM12 Fieldmap Toolbox v2.1 
% (default options). \nOther than defaults: \n- estimation: quality 0.95, 
% separation 3, two-pass procedure (i. registering to 1st scan, ii. 
% registering to mean image), interpolation 7th degree B-spline; \n- unwarp
% & reslice: interpolation 7th degree B-spline ",

% *** Create VDM map from field maps
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.data.presubphasemag.phase = {
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/fmap/sub-001_phasediff.nii,1'};
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.data.presubphasemag.magnitude = {
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/fmap/sub-001_magnitude1.nii,1'};
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.defaults.defaultsval.et = [4.92 7.38];
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.defaults.defaultsval.maskbrain = 0;
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.defaults.defaultsval.blipdir = -1;
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.defaults.defaultsval.tert = 29.15;
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.defaults.defaultsval.epifm = 0;
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.session(1).epi = {
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-01_bold.nii,1'};
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.session(2).epi = {
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-02_bold.nii,1'};
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.session(3).epi = {
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-03_bold.nii,1'};
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.session(4).epi = {
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-04_bold.nii,1'};
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.matchvdm = 1;
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.writeunwarped = 0;
matlabbatch{1}.spm.tools.fieldmap.calculatevdm.subj.matchanat = 0;

% --> This generates 4 files whose name start with vdm5_
% In the following we will denote them by vdm5_runXX.extension


matlabbatch{end+1}.spm.spatial.realignunwarp.data(1).scans = {
    % Note: as many volumes as 3d volume in the fmri 4D image    
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-01_bold.nii,1'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-01_bold.nii,2'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-01_bold.nii,3'};
matlabbatch{end}.spm.spatial.realignunwarp.data(1).pmscan = {'ABS_PATH/vdm5_run01.nii'};
matlabbatch{end}.spm.spatial.realignunwarp.data(2).scans = {
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-02_bold.nii,1'
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-02_bold.nii,2'
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-02_bold.nii,3'};
matlabbatch{end}.spm.spatial.realignunwarp.data(2).pmscan = {'ABS_PATH/vdm5_run02.nii'};
matlabbatch{end}.spm.spatial.realignunwarp.data(3).scans = {
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-03_bold.nii,1'
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-03_bold.nii,2'
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-02_bold.nii,3'};
matlabbatch{end}.spm.spatial.realignunwarp.data(3).pmscan = {'ABS_PATH/vdm5_run03.nii'};
matlabbatch{end}.spm.spatial.realignunwarp.data(4).scans = {
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-04_bold.nii,1'
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-04_bold.nii,2'
    '/Users/camaumet/Softs/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-04_bold.nii,3'};
matlabbatch{end}.spm.spatial.realignunwarp.data(4).pmscan = {'ABS_PATH/vdm5_run04.nii'};
matlabbatch{end}.spm.spatial.realignunwarp.eoptions.quality = 0.95;
matlabbatch{end}.spm.spatial.realignunwarp.eoptions.sep = 3;
matlabbatch{end}.spm.spatial.realignunwarp.eoptions.rtm = 1;
matlabbatch{end}.spm.spatial.realignunwarp.eoptions.einterp = 7;
matlabbatch{end}.spm.spatial.realignunwarp.uwroptions.rinterp = 7;

% --> Here we get 4 files usub-001_task-MGT_run-XX_bold.nii as well as 1
% unwarped_mean_image.nii


% 2) intersubject registration (normalization)

% Note: we need to do segmentation first
matlabbatch{end+1}.spm.tools.oldseg.data = {
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/anat/sub-001_T1w.nii,1'};

% --> Here we get a c1sub-001_T1w.nii file that is the grey matter
% probability map and transfo.nii file (not sure it is a .nii) that is the
% calculated transformation between anat and standardized space

% Coreg each sbref onto mean unwarp

% --> For each run, the distortion-corrected single-band reference EPI image 
% was co-registered to the mean EPI image obtained from Realignment & Unwarping
 % using normalised mutual information. 

% Note in Python implem: This sounds like there were 4 coreg and not a single 
% as done below (4 coregs were implemented in the Python code)

matlabbatch{end+1}.spm.spatial.coreg.estimate.ref(1) = {
    'ABS_PATH/unwarped_mean_image.nii'
    };
matlabbatch{end}.spm.spatial.coreg.estimate.source(1) = {
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-01_sbref.nii'};
matlabbatch{end}.spm.spatial.coreg.estimate.eoptions.cost_fun = 'nmi';

matlabbatch{end+1}.spm.spatial.coreg.estimate.ref(1) = {
    'ABS_PATH/unwarped_mean_image.nii'
    };
matlabbatch{end}.spm.spatial.coreg.estimate.source(1) = {
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-02_sbref.nii'};
matlabbatch{end}.spm.spatial.coreg.estimate.eoptions.cost_fun = 'nmi';

matlabbatch{end+1}.spm.spatial.coreg.estimate.ref(1) = {
    'ABS_PATH/unwarped_mean_image.nii'
    };
matlabbatch{end}.spm.spatial.coreg.estimate.source(1) = {
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-03_sbref.nii'};
matlabbatch{end}.spm.spatial.coreg.estimate.eoptions.cost_fun = 'nmi';

matlabbatch{end+1}.spm.spatial.coreg.estimate.ref(1) = {
    'ABS_PATH/unwarped_mean_image.nii'
    };
matlabbatch{end}.spm.spatial.coreg.estimate.source(1) = {
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-04_sbref.nii'};
matlabbatch{end}.spm.spatial.coreg.estimate.eoptions.cost_fun = 'nmi';

% --> HERE WE get 4 file ssub-001_task-MGT_run-XX_sbref.nii (that
% keeps the same name as before *but* the header has been modified to apply
% the coregistration'


% Note in Python implem: The coreg are done separatly in each run and therefore
% other only includes 'usub-001_task-MGT_run-01_bold.nii'
matlabbatch{end+1}.spm.spatial.coreg.estimate.ref(1) = {
    'ABS_PATH/c1sub-001_T1w.nii'
};
matlabbatch{end}.spm.spatial.coreg.estimate.source(1) = {
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-01_sbref.nii'
    };
matlabbatch{end}.spm.spatial.coreg.estimate.other = {'usub-001_task-MGT_run-01_bold.nii'
    'usub-001_task-MGT_run-02_bold.nii'
    'usub-001_task-MGT_run-03_bold.nii'
    'usub-001_task-MGT_run-04_bold.nii'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-02_sbref.nii'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-03_sbref.nii'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-04_sbref.nii'
};
matlabbatch{end}.spm.spatial.coreg.estimate.eoptions.cost_fun = 'nmi';


% We apply the transformation to standardized space

matlabbatch{end+1}.spm.spatial.normalise.write.subj.def = {'transfo.nii'};
matlabbatch{end}.spm.spatial.normalise.write.subj.resample = {
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/usub-001_task-MGT_run-01_bold.nii'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/usub-001_task-MGT_run-02_bold.nii'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/usub-001_task-MGT_run-03_bold.nii'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/usub-001_task-MGT_run-04_bold.nii'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-02_sbref.nii'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-03_sbref.nii'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/sub-001_task-MGT_run-04_sbref.nii'
};

% 3) spatial smoothing
matlabbatch{end+1}.spm.spatial.smooth.data = {
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/usub-001_task-MGT_run-01_bold.nii'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/usub-001_task-MGT_run-02_bold.nii'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/usub-001_task-MGT_run-03_bold.nii'
    'ABS_PATH/narps_open_pipelines/data/original/ds001734/sub-001/func/usub-001_task-MGT_run-04_bold.nii'
};
matlabbatch{end}.spm.spatial.smooth.fwhm = [8 8 8];

% ##### 4) First-level statistical analysis

% We'll reuse Python code from DC61 to generate the conditions with parametric 
% modulation

def get_subject_information(event_files: list):
        from nipype.interfaces.base import Bunch

        subject_info = []

        for run_id, event_file in enumerate(event_files):

            onsets = []
            durations = []
            gain_value = []
            loss_value = []
            reaction_time = []

            # Parse the events file
            with open(event_file, 'rt') as file:
                next(file)  # skip the header

                for line in file:
                    info = line.strip().split()

% --> independent_vars_first_level : - event-related design with each trial 
% modelled with a duration of 4 sec and 3 linear parametric modulators (PMs 
% orthogonalized via de-meaning against task and preceding PMs, respectively) 
% for gain, loss and reaction time (in that order) as given in the .tsv log 
% files

                    onsets.append(float(info[0]))
                    durations.append(float(info[1]))
                    gain_value.append(float(info[2]))
                    loss_value.append(float(info[3]))
                    reaction_time.append(float(info[4]))

            # Create a Bunch for the run
            subject_info.append(
                Bunch(
                    conditions = [f'gamble_run{run_id + 1}'],
                    onsets = [onsets],
                    durations = [durations], % duration is 4s
                    amplitudes = None,
                    tmod = None,
                    pmod = [
                        Bunch(
                            name = ['gain_param', 'loss_param', 'rt_param'],
                            poly = [1, 1, 1],
                            param = [gain_value, loss_value, reaction_time]
                        )
                    ],
                    regressor_names = None,
                    regressors = None
                ))

        return subject_info


matlabbatch{1}.spm.stats.fmri_spec.dir = '<UNDEFINED>';
matlabbatch{1}.spm.stats.fmri_spec.timing.units = 'secs';
matlabbatch{1}.spm.stats.fmri_spec.timing.RT = '<UNDEFINED>'; % Same as usual = TR 
matlabbatch{1}.spm.stats.fmri_spec.sess(1).scans = '<UNDEFINED>'; % scans from session 1
% Note that parametric modulation was done in the Python code above and is not repeated here
matlabbatch{1}.spm.stats.fmri_spec.sess(1).cond = struct('name', {}, 'onset', {}, 'duration', {}, 'tmod', {}, 'pmod', {}, 'orth', {});
matlabbatch{1}.spm.stats.fmri_spec.sess(1).multi = {''};
matlabbatch{1}.spm.stats.fmri_spec.sess(1).regress = struct('name', {}, 'val', {});
% --> 6 motion regressors (1st-order only) reflecting the 6 realignment parameters for translation and rotation movements obtained during preprocessing
matlabbatch{1}.spm.stats.fmri_spec.sess(1).multi_reg = {'<PATH_TO_REALIGN_SESS1>'}; % link to parameter motion files created by realign
matlabbatch{1}.spm.stats.fmri_spec.sess(1).hpf = 128;
matlabbatch{1}.spm.stats.fmri_spec.sess(2).scans = '<UNDEFINED>'; % scans from session 2
matlabbatch{1}.spm.stats.fmri_spec.sess(2).cond = struct('name', {}, 'onset', {}, 'duration', {}, 'tmod', {}, 'pmod', {}, 'orth', {});
matlabbatch{1}.spm.stats.fmri_spec.sess(2).multi = {''};
matlabbatch{1}.spm.stats.fmri_spec.sess(2).regress = struct('name', {}, 'val', {});
matlabbatch{1}.spm.stats.fmri_spec.sess(2).multi_reg = {'<PATH_TO_REALIGN_SESS2>'}; % link to parameter motion files created by realign
matlabbatch{1}.spm.stats.fmri_spec.sess(2).hpf = 128;
matlabbatch{1}.spm.stats.fmri_spec.sess(3).scans = '<UNDEFINED>'; % scans from session 3
matlabbatch{1}.spm.stats.fmri_spec.sess(3).cond = struct('name', {}, 'onset', {}, 'duration', {}, 'tmod', {}, 'pmod', {}, 'orth', {});
matlabbatch{1}.spm.stats.fmri_spec.sess(3).multi = {''};
matlabbatch{1}.spm.stats.fmri_spec.sess(3).regress = struct('name', {}, 'val', {});
matlabbatch{1}.spm.stats.fmri_spec.sess(3).multi_reg = {'<PATH_TO_REALIGN_SESS3>'}; % link to parameter motion files created by realign
matlabbatch{1}.spm.stats.fmri_spec.sess(3).hpf = 128;
matlabbatch{1}.spm.stats.fmri_spec.sess(4).scans = '<UNDEFINED>'; % scans from session 4
matlabbatch{1}.spm.stats.fmri_spec.sess(4).cond = struct('name', {}, 'onset', {}, 'duration', {}, 'tmod', {}, 'pmod', {}, 'orth', {});
matlabbatch{1}.spm.stats.fmri_spec.sess(4).multi = {''};
matlabbatch{1}.spm.stats.fmri_spec.sess(4).regress = struct('name', {}, 'val', {});
matlabbatch{1}.spm.stats.fmri_spec.sess(4).multi_reg = {'<PATH_TO_REALIGN_SESS4>'}; % link to parameter motion files created by realign
matlabbatch{1}.spm.stats.fmri_spec.fact = struct('name', {}, 'levels', {});
% --> canonical HRF plus temporal derivative
matlabbatch{1}.spm.stats.fmri_spec.bases.hrf.derivs = [1 0];

% Those are just the default
% matlabbatch{1}.spm.stats.fmri_spec.volt = 1;
% matlabbatch{1}.spm.stats.fmri_spec.global = 'None';
% matlabbatch{1}.spm.stats.fmri_spec.mthresh = 0.8;
% matlabbatch{1}.spm.stats.fmri_spec.mask = {''};

% --> model_settings : 1st-level model: "AR(1) + w" autocorrelation model in 
% SPM, high-pass filter: 128 s (Note: those are default in SPM)
matlabbatch{1}.spm.stats.fmri_spec.cvi = 'AR(1)';
matlabbatch{1}.spm.stats.fmri_spec.sess(4).hpf = 128;

% ##### 5) Contrast definition at the first-level
% --> After model estimation, sum contrast images for each regressor of 
% interest [task, gain (PM1), loss (PM2) and RT (PM3)] were computed across 
% the 4 sessions in each participant.

self.contrast_list = ['0001', '0002', '0003', '0004']
self.subject_level_contrasts = [
    ('task', 'T',
        [f'gamble_run{r}' for r in range(1, len(self.run_list) + 1)],
        [1]*len(self.run_list)),
    ('effect_of_gain', 'T',
        [f'gamble_run{r}xgain_param^1' for r in range(1, len(self.run_list) + 1)],
        [1]*len(self.run_list)),
    ('effect_of_loss', 'T',
        [f'gamble_run{r}xloss_param^1' for r in range(1, len(self.run_list) + 1)],
        [1]*len(self.run_list))
    ('effect_of_RT', 'T',
        [f'gamble_run{r}xRT_param^1' for r in range(1, len(self.run_list) + 1)],
        [1]*len(self.run_list))
]

% ##### 6) Group-level statistical analysis
% --> A flexible factorial design was used to examine the effects of 4 factors 
% of interest [task, gain (PM1), loss (PM2) and RT (PM3); cf. description 
% above] for each of the 2 groups (Equal Indifference vs. Equal Range).

% --> 2nd-level model: random-effects GLM implemented with weighted least 
% squares (via SPM's restricted maximum likelihood estimation); both between-condition and between-group variances assumed to be unequal

I think this means we have a single stat model with the 4 factors and the 2 
groups and that the contrast.

matlabbatch{1}.spm.stats.factorial_design.des.fblock.fac(1).name = 'Factor';
matlabbatch{1}.spm.stats.factorial_design.des.fblock.fac(1).dept = 0;
matlabbatch{1}.spm.stats.factorial_design.des.fblock.fac(1).variance = 1;
matlabbatch{1}.spm.stats.factorial_design.des.fblock.fac(1).gmsca = 0;
matlabbatch{1}.spm.stats.factorial_design.des.fblock.fac(1).ancova = 0;
matlabbatch{1}.spm.stats.factorial_design.des.fblock.fac(2).name = 'Group';
matlabbatch{1}.spm.stats.factorial_design.des.fblock.fac(2).dept = 0;
matlabbatch{1}.spm.stats.factorial_design.des.fblock.fac(2).variance = 1;
matlabbatch{1}.spm.stats.factorial_design.des.fblock.fac(2).gmsca = 0;
matlabbatch{1}.spm.stats.factorial_design.des.fblock.fac(2).ancova = 0;
matlabbatch{1}.spm.stats.factorial_design.des.fblock.fsuball.fsubject.scans = '<UNDEFINED>';
matlabbatch{1}.spm.stats.factorial_design.des.fblock.fsuball.fsubject.conds = [1 1
                                                                               2 1
                                                                               3 1
                                                                               4 1];


% ##### 6) Group-level contrast
% --> inference_contrast_effect : Linear T contrasts for the two parameters of 
% interest (PM1 indicating linear hemodynamic changes with Gain value over 
% trials within each subject, PM2 indicating such changes with Loss value) were
 % used to test for the effects specified in the 9 hypotheses given.

 task_range gain_range loss_range RT_range task_indiff gain_indiff loss_indiff RT_indiff

% H1 - Positive parametric effect of gains in the vmPFC (equal indifference group)
% H3 -  Positive parametric effect of gains in the ventral striatum (equal indifference group) 
['gain_indiff_pos', 'T', ['gain_indiff'], [1]],
% H2 - Positive parametric effect of gains in the vmPFC (equal range group) 
% H4 - Positive parametric effect of gains in the ventral striatum (equal range group) 
['gain_range_pos', 'T', ['gain_range'], [1]],
% H5 - Negative parametric effect of losses in the vmPFC (equal indifference group) 
['loss_indiff_neg', 'T', ['loss_indiff'], [-1]] 
% H6 - Negative parametric effect of losses in the vmPFC (equal range group) 
['loss_range_neg', 'T', ['loss_range'], [-1]] 
% H7 - Positive parametric effect of losses in the amygdala (equal indifference group)
['loss_indiff_pos', 'T', ['loss_indiff'], [1]] 
% H8 - Positive parametric effect of losses in the amygdala (equal range group) 
['loss_range_pos', 'T', ['loss_range'], [1]] 
% H9 - Greater positive response to losses in amygdala (equal range group vs. equal indifference group)
['loss_range_pos_range_vs_indiff', 'T', ['loss_range' 'loss_indiff'], [1 -1]] 

% ##### 7) Inference
% --> pval_computation : standard parametric inference
% --> multiple_testing_correction : family-wise error correction, based on Random Field Theory
