#!/bin/tcsh

# AP_TASK: full task-based processing (voxelwise), with blurring
# with local EPI unifize 

# NOTES
#
# + This is a Biowulf script (has slurm stuff)
# + Run this script in the scripts/ dir, via the corresponding run_*tcsh
# + NO session level here.

# ----------------------------- biowulf-cmd ---------------------------------
# load modules
source /etc/profile.d/modules.csh
module load afni

# set N_threads for OpenMP
# + consider using up to 4 threads, because of "-parallel" in recon-all
setenv OMP_NUM_THREADS $SLURM_CPUS_PER_TASK

# compress BRIK files
setenv AFNI_COMPRESSOR GZIP

# initial exit code; we don't exit at fail, to copy partial results back
set ecode = 0
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# top level definitions (constant across demo)
# ---------------------------------------------------------------------------

# labels
set subj           = $1
#set ses            = $2
set ap_label       = 23_ap_task_b

# upper directories
set dir_inroot     = ${PWD:h}                        # one dir above scripts/
set dir_log        = ${dir_inroot}/logs
set dir_store      = /data/SSCC_NARPS/globus_sync/ds001205 # data on biowulf
set dir_basic      = ${dir_store}    #${dir_inroot}/data_00_basic
set dir_deob       = ${dir_inroot}/data_02_deob
set dir_fs         = ${dir_inroot}/data_12_fs
set dir_ssw        = ${dir_inroot}/data_13_ssw
set dir_events     = ${dir_inroot}/data_15_events
set dir_ap         = ${dir_inroot}/data_${ap_label}

# subject directories
set sdir_basic     = ${dir_basic}/${subj}  #/${ses}
set sdir_epi       = ${sdir_basic}/func
set sdir_anat      = ${sdir_basic}/anat
set sdir_timing    = ${sdir_epi}
set sdir_deob      = ${dir_deob}/${subj}   #/${ses}
set sdir_fs        = ${dir_fs}/${subj}  #/${ses}
set sdir_suma      = ${sdir_fs}/SUMA
set sdir_ssw       = ${dir_ssw}/${subj} #/${ses}
set sdir_events    = ${dir_events}/${subj} #/${ses}
set sdir_ap        = ${dir_ap}/${subj}  #/${ses}

# extra datasets
set dir_extra      = ${dir_inroot}/extra_dsets
set template       = ${dir_extra}/MNI152_2009_template_SSW.nii.gz
set grid_template  = ${dir_extra}/T1.grid_template.nii.gz

# --------------------------------------------------------------------------
# data and control variables
# --------------------------------------------------------------------------

# dataset inputs
set dsets_epi     = ( ${sdir_epi}/${subj}_*task*bold.nii* )

set dset_anat_00  = ${sdir_deob}/${subj}_T1w-deobl_nu.nii.gz  #/${ses}
set anat_cp       = ${sdir_ssw}/anatSS.${subj}.nii
set anat_skull    = ${sdir_ssw}/anatU.${subj}.nii

set dsets_NL_warp = ( ${sdir_ssw}/anatQQ.${subj}.nii         \
                      ${sdir_ssw}/anatQQ.${subj}.aff12.1D    \
                      ${sdir_ssw}/anatQQ.${subj}_WARP.nii  )

# might not always use these
set mask_wm      = ${sdir_suma}/fs_ap_wm.nii.gz
set roi_all_2000 = ${sdir_suma}/aparc+aseg_REN_all.nii.gz
set roi_gmr_2000 = ${sdir_suma}/aparc+aseg_REN_gmrois.nii.gz

set timing_files  = ( ${sdir_events}/times.{Resp,NoResp}.txt )
set stim_classes  = ( Resp NoResp )

# control variables
###set nt_rm         = 0      
set blur_size     = 4.0     
set final_dxyz    = 2.0
set cen_motion    = 0.3
set cen_outliers  = 0.05

# one way of many ways to set to available number of CPUs:
# afni_check_omp respects ${OMP_NUM_THREADS}
set njobs         = `afni_check_omp`

# check available N_threads and report what is being used
set nthr_avail = `afni_system_check.py -disp_num_cpu`
set nthr_using = `afni_check_omp`

echo "++ INFO: Using ${nthr_avail} of available ${nthr_using} threads"

# ----------------------------- biowulf-cmd --------------------------------
# try to use /lscratch for speed 
if ( -d /lscratch/$SLURM_JOBID ) then
    set usetemp  = 1
    set sdir_BW  = ${sdir_ap}
    set sdir_ap  = /lscratch/$SLURM_JOBID/${subj} #_${ses}

    # prep for group permission reset
    \mkdir -p ${sdir_BW}
    set grp_own = `\ls -ld ${sdir_BW} | awk '{print $4}'`
else
    set usetemp  = 0
endif
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# run programs
# ---------------------------------------------------------------------------

set ap_cmd = ${sdir_ap}/ap.cmd.${subj}

\mkdir -p ${sdir_ap}

# write AP command to file
cat <<EOF >! ${ap_cmd}

# Some notes on afni_proc.py (AP) option choices:
#
# The blur block is used here, because this is processing for voxelwise
# analysis. See the 'do_22*.tcsh' script for the related processing that 
# does **not** include blurring (for ROI-based analysis).  The blur size
# is set to be about 2 times the average voxel edge length.
#
# This adds useful APQC HTML items, radial correlation images of initial
# and volume-registered data (might see artifacts):
#   -radial_correlate_blocks  tcat volreg
# 
# Even though we load the skullstripped anatomical (proc'ed by @SSwarper), 
# having the original, skull-on dataset brought along as a follower dset
# can be useful for verifying EPI-anatomical alignment when the brigt CSF
# extends outside the brain.
#   -anat_follower            anat_w_skull anat \${anat_skull}
#
# Generally recommended to run @SSwarper prior to afni_proc.py for 
# skullstripping (SS) the anatomical and estimating nonlinear warp to
# template;  then provide those results in options here:
#   -copy_anat                \${anat_cp}
#   ...
#   -tlrc_base                \${template}
#   -tlrc_NL_warp                               
#   -tlrc_NL_warped_dsets     \${dsets_NL_warp} 
#
# This option can help improve EPI-anatomical alignment, esp. if the EPI
# has brightness inhomogeneity (and it doesn't seem to hurt alignment even
# if that is not the case); generally recommended with human FMRI 
# data processing nowadays:
#   -align_unifize_epi        local 
#
# Generally recommended starting point for EPI-anatomical alignment in human
# FMRI proc (left-right flipping can still occur...):
#   -align_opts_aea           -cost lpc+ZZ -giant_move -check_flip 
#
# Which EPI should be a consistently good choice to serve as a
# reference for both motion correction and EPI-anatomical alignment?  
# The one with the fewest outliers (and so low motion) sounds good:
#   -volreg_align_to          MIN_OUTLIER
#
# Add a post-volreg TSNR plot to the APQC HTML:
#   -volreg_compute_tsnr      yes
#
# Create useful mask from EPI-anatomical mask intersection (not applied
# to the EPI data here, but used to identify brain region):
#   -mask_epi_anat            yes
#
# Compute a time series that is the sum of all non-baseline regressors,
# for QC visualization:
#   -regress_make_ideal_sum   sum_ideal.1D
#
# Choose this shape and scaling for the regression basis; the '-1' in the
# argument means that an event with 1 s duration is scaled to 1; the choice
# of number is based on typical or average event duration:
#   -regress_basis_multi      "dmUBLOCK(-1)" 
#
# Try to use Python's Matplotlib module when making the APQC HTML doc, for
# prettier (and more informative) plots; this is actually the default now:
#   -html_review_style        pythonic
#


afni_proc.py                                                                 \
    -subj_id                  ${subj}                                        \
    -blocks                   tshift align tlrc volreg blur mask scale regress \
    -radial_correlate_blocks  tcat volreg                                    \
    -copy_anat                ${anat_cp}                                     \
    -anat_has_skull           no                                             \
    -anat_follower            anat_w_skull anat ${anat_skull}                \
    -anat_follower_ROI        a00all       anat ${roi_all_2000}              \
    -anat_follower_ROI        e00all       epi  ${roi_all_2000}              \
    -anat_follower_ROI        a00gmr       anat ${roi_gmr_2000}              \
    -anat_follower_ROI        e00gmr       epi  ${roi_gmr_2000}              \
    -anat_follower_ROI        eWMe         epi  ${mask_wm}                   \
    -anat_follower_erode      eWMe                                           \
    -dsets                    ${dsets_epi}                                   \
    -tcat_remove_first_trs    0                                              \
    -tshift_opts_ts           -tpattern alt+z2                               \
    -align_unifize_epi        local                                          \
    -align_opts_aea           -cost lpc+ZZ                                   \
                              -giant_move                                    \
                              -check_flip                                    \
    -tlrc_base                ${template}                                    \
    -tlrc_NL_warp                                                            \
    -tlrc_NL_warped_dsets     ${dsets_NL_warp}                               \
    -volreg_align_to          MIN_OUTLIER                                    \
    -volreg_align_e2a                                                        \
    -volreg_tlrc_warp                                                        \
    -volreg_compute_tsnr      yes                                            \
    -volreg_warp_dxyz         ${final_dxyz}                                  \
    -blur_size                ${blur_size}                                   \
    -mask_epi_anat            yes                                            \
    -test_stim_files          no                                             \
    -regress_stim_times       ${timing_files}                                \
    -regress_stim_labels      ${stim_classes}                                \
    -regress_stim_types       AM2 AM1                                        \
    -regress_basis_multi      "dmUBLOCK(-1)"                                 \
    -regress_motion_per_run                                                  \
    -regress_anaticor_fast                                                   \
    -regress_anaticor_fwhm    20                                             \
    -regress_anaticor_label   eWMe                                           \
    -regress_censor_motion    ${cen_motion}                                  \
    -regress_censor_outliers  ${cen_outliers}                                \
    -regress_compute_fitts                                                   \
    -regress_opts_3dD         -jobs ${njobs}                                 \
                              -num_glt 1                                     \
                              -gltsym 'SYM: Resp[1] -Resp[2]'                \
                              -glt_label 1 gain-loss                         \
                              -GOFORIT 10                                    \
    -regress_3dD_stop                                                        \
    -regress_reml_exec                                                       \
    -regress_opts_reml        -GOFORIT                                       \
    -regress_make_ideal_sum   sum_ideal.1D                                   \
    -regress_make_corr_vols   eWMe                                           \
    -regress_est_blur_errts                                                  \
    -regress_run_clustsim     no                                             \
    -html_review_style        pythonic

EOF

if ( ${status} ) then
    set ecode = 1
    goto COPY_AND_EXIT
endif

cd ${sdir_ap}

# execute AP command to make processing script
tcsh -xef ${ap_cmd} |& tee output.ap.cmd.${subj}

if ( ${status} ) then
    set ecode = 1
    goto COPY_AND_EXIT
endif

# execute the proc script, saving text info
time tcsh -xef proc.${subj} |& tee output.proc.${subj}

if ( ${status} ) then
    echo "++ FAILED AP: ${ap_label}"
    set ecode = 1
    goto COPY_AND_EXIT
else
    echo "++ FINISHED AP: ${ap_label}"
endif

# ---------------------------------------------------------------------------

COPY_AND_EXIT:

# ----------------------------- biowulf-cmd --------------------------------
# copy back from /lscratch to "real" location
if( ${usetemp} && -d ${sdir_ap} ) then
    echo "++ Used /lscratch"
    echo "++ Copy from: ${sdir_ap}"
    echo "          to: ${sdir_BW}"
    \mkdir -p ${sdir_BW}
    \cp -pr   ${sdir_ap}/* ${sdir_BW}/.

    # reset group permission
    chgrp -R ${grp_own} ${sdir_BW}
    chmod -R g+w ${sdir_BW}
endif
# ---------------------------------------------------------------------------

if ( ${ecode} ) then
    echo "++ BAD FINISH: AP (ecode = ${ecode})"
else
    echo "++ GOOD FINISH: AP"
endif

exit ${ecode}

