# NARPS team description : 27SS
## General
* `teamID` : 27SS
* `NV_collection_link` : https://neurovault.org/collections/4975/
* `results_comments` : We coded losses in our regression as positive values, meaning a POSITIVE parametric effect of losses indicates greater activity as the loss magnitude increases (i.e. more activity to -20 than -10). 
* `preregistered` : No
* `link_preregistration_form` : NA
* `regions_definition` : For the ventral striatum and amygdala, bilateral regions of interest were defined using the MNI_152 atlas included with AFNI. For these regions, spherical ROIs with radius 5mm were specified with their center at the center of the region as defined by MNI atlas. For the vmPFC, we specified two possible distinct ROIs based on locations indicated by review papers on decision making literature. One vmPFC ROI was defined using a single centered spherical ROI with a 9mm radius based on Clithero & Rangel, 2014 (Table 6). Another was defined using bilateral spherical ROIs with 5mm radius using coordinates from Bartra, Mcguire & Kable, 2013 (Table 3). After visual inspection of the ROIs, we chose to use the Clithero & Rangel (2014) ROI as it was larger, and so a better choice given the uncertainty about the location of the VMPFC (and its susceptibility to fMRI artifacts). 

Amygdala L (-23, 5, -15)
Amygdala R (23, 5, -15)
VMPFC (0, 39, -3)
VS/NACC L (-12, -8, -8)
VS/NACC R (12, -8, -8) 
* `softwares` : AFNI 18.3.12
* `general_comments` : NA
## Exclusions
* `n_participants` : 108
* `exclusions_details` : NA
## Preprocessing
* `used_fmriprep_data` : No
* `preprocessing_order` : 1. Slice time correction.
2.  Alignment of anatomical and EPI image (intra-subject coregistration)
2. Non-linear warping of anatomical image into standard space
3. EPI volume registration to minimum outlier
4. Non-linear warping of volumes into standard space
5. Blurring with 6mm kernel size
6. Deconvolution of BOLD signal on task and nuisance regressors
* `brain_extraction` : Not performed beyond standard AFNI skull-stripping as part of anatomical alignment.
* `segmentation` : None
* `slice_time_correction` : AFNI's 3dTshift command. Performed before motion correction. Reference slice = 1. Used quintic (5th order) Lagrange polynomial interpolation. 
* `motion_correction` : AFNI 3dvolreg command. Cubic polynomial interpolation to minimum outlier volume of each subject (align_to_MIN_OUTLIER) using iterated linearized weighted least squares.
* `motion` : 
* `gradient_distortion_correction` : Not performed
* `intra_subject_coreg` : AFNI's align_epi_anat.py command. Aligns anatomical image to EPI image using affine transformation with the cost function lpc+ZZ (mainly uses the local pearson correlation, a nonlinear average of the Pearson's correlation over local neighborhoods).
* `distortion_correction` : Not performed
* `inter_subject_reg` : Each subject's anatomical/EPI volumes were warped non-linearly using auto_warp.py in AFNI, performing an affine transform, normalizing participants to the MNI 152 template. Anatomical images were warped first, with the resulting warp calculations later applied to EPI images after motion correction. 
* `intensity_correction` : Not performed
* `intensity_normalization` : Scaling of each voxel time series to have mean intensity 100.
* `noise_removal` : AFNI 3dDeconvolve used demeaned motion parameters for roll, pitch, yaw, dS, dL, and dP during first-level regressions. 
* `volume_censoring` : Motion outliers with framewise displacement (FD) greater than 1.5mm were also censored from analysis. 
* `spatial_smoothing` : Blurring at 6mm FWHM kernel size using AFNI 3dmerge. Smoothing was performed as the final step (following motion correction, coregistration, and warping).
* `preprocessing_comments` : NA
## Analysis
* `data_submitted_to_model` : 108 participants' data were submitted for statistical modeling. As mentioned above, volumes with more than 1.5mm Framewise Displacement were censored from analysis. The following subjects had volumes removed from their analysis for motion: subject (# of volumes), 22 (2), 36 (2), 100 (2), 106 (2), 120 (2), 93 (4), 110 (6), 26 (7), 88 (12), 116 (13), 18 (15), 16 (19), 30 (312). Every subject had 1792 TRs per stimulus (less the number excluded for motion, where applicable). 

Additionally, trials with reaction times less than or equal to .001 seconds were considered missed trials and were thus excluded from analysis. Five participants total had this happen: subject (# of trials with responses that were considered as missed), 53 (3), 55 (1), 67 (1), 82 (2), 105 (4).
* `spatial_region_modeled` : Full brain was modeled at the individual subject level, unmasked. 
* `independent_vars_first_level` : We modeled our first level analysis using regressors for trial onset, missed trials, and button press separately. Trial onset was additionally parametrically modulated by gain and loss and duration was set to the trial-level reaction time. Stimulus onset HRF was modeled as an event related canonical HRF with amplitude and duration modulation as described above (AFNI specifications stim_type AM2 and basis 'dmBLOCK(0)'). Missed trials and button presses HRFs were modeled using AFNI's 'GAM', which is a 12 second canonical HRF). 

Motion regressors were modeled according to demeaned motion in 6 directions: roll, pitch, yaw, dS, dL, and dP. No temporal derivitaves were used. AFNI standard mean and de-trending regressors were included for each run separately.
* `RT_modeling` : duration
* `movement_modeling` : 1
* `independent_vars_higher_level` : No covariates were included in these group level models. For loss ER vs EI, these two groups were modeled according to 3dMEMA two-sample t-test specifications (i.e. using -groups command). 

We had five total models to test the nine questions:
gain_ei (modeled gain vs. 0 for only participants in the equal indifference condition)
gain_er (modeled gain vs. 0 for only participants in the equal range condition)
loss_ei (modeled loss vs. 0 for only participants in the equal indifference condition)
loss_er (modeled loss vs. 0 for only participants in the equal range condition)
loss_er_vs_loss_ei (modeled as loss for the ER group vs. loss for the EI group).

The use of 3dMEMA in AFNI meant that 2nd-level analyses weighted (using the KH test) individual subjects' beta values with their individual t-statistic such that individuals with higher t-statistics were given greater voxelwise weight in the group-level analysis. 
* `model_type` : Mass univariate. One and two-sample t-tests were modeled using AFNI '3dMEMA' specification, using mixed effects modeling. This model uses each individual subjects' REML-estimated coefficient and t-statistic.
* `model_settings` : First level model: a spatial autocorrelation function for each subject was estimated according to mixed-model ACF specified in the blur procedure of afni_proc.py. This computes an ACF blur estimate for each subject in the x,y, and z directions that is then averaged across subjects and used for cluster extent thresholding at the group level. Standard AFNI detrending and mean regressors were included in the first-level regressions for each run. Analyses used AFNI's 3dREMLfit function, which solves linear equations for each voxel in the generalized (prewhitened) least squares sense, using the REML estimation method to find a best-fit ARMA(1,1) model.

Group level models were mixed-effects models using AFNI '3dMEMA' and individual subject's restricted maximum likelihood (REML) estimates of task and motion regressors. For Hypothesis 9 (contrasting the ER and EI groups), equal variance was assumed. 
* `inference_contrast_effect` : All contrasts were two-sided, and were simple one-sample and two-sample (independent sample) t-tests subject to the 3dMEMA mixed effects adjustments (e.g. for gain vs. 0, we examined the main effect of parametric gain on whole brain BOLD signal).
* `search_region` : The group level models were constructed and subsequently thresholded on a whole-brain basis. These were then further masked according to anatomically defined ROIs as specified in Analysis: General (see above).
* `statistic_type` : Cluster-wise statistics were extracted from the ROI-masked whole brain model. This masked whole brain model (for each ROI separately) was first cluster thresholded according to AFNI's 3dClustSim -acf specification and the mean ACF values across subjects (using an uncorrected p value of 0.001, and a cluster threshold of 52 voxels to attain a final, whole-brain corrected p-value of 0.05). AFNI's cluster report was then used to determine the presence of any clusters remaining in the specified ROI, which formed the basis for the binary Yes/No decision for each of the 9 hypotheses.
* `pval_computation` : Parametric inference at the whole brain level assessed statistical significance. Using AFNI's 3dClustSim, it was determined that a p<.001 threshold with a cluster size extent of 52 voxels was equivalent to a whole-brain thresholded p-value of p < .05. Any clusters that were larger than 52 voxels in size at p<.001 in the whole brain model were considered statistically signficant. 
* `multiple_testing_correction` : None. 
* `comments_analysis` : In addition to the whole brain models run above, we also extracted mean beta and t-values for each subject (using restricted maximum likelihood estimates) from ROI masks before they were entered into a whole brain analysis and did post-hoc tests on the resulting betas (one for each subject, for each ROI).  These tests, effectively small-volume corrected tests, identified, at the p < 0.01 level, the following answers to the 9 hypotheses: 1) No, 2) No, 3) Yes, 4) No, 5) Yes, 6) Yes, 7) No, 8), No, 9) No. We formed these binary judgments on the basis of non-parametric Wilcoxon signed-rank test.  
## Categorized for analysis
* `region_definition_vmpfc` : Other
* `region_definition_striatum` : atlas MNI_152
* `region_definition_amygdala` : atlas MNI_152
* `analysis_SW` : AFNI
* `analysis_SW_with_version` : AFNI 18.3.12
* `smoothing_coef` : 6
* `testing` : parametric
* `testing_thresh` : p<0.001
* `correction_method` : ClustSim
* `correction_thresh_` : p<0.05
## Derived
* `n_participants` : 108
* `excluded_participants` : n/a
* `func_fwhm` : 6
* `con_fwhm` : 
## Comments
* `excluded_from_narps_analysis` : No
* `exclusion_comment` : N/A
* `reproducibility` : 2
* `reproducibility_comment` : 

