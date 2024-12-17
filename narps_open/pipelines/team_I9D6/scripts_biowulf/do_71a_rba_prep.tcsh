#!/bin/tcsh

# RBA_PREP: make tables of ROI properties per subj, to be combined for RBA

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
set grp            = $2
set cond           = $3

set ap_label       = 22_ap_task
set grp_label      = ${grp}.${cond}

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
set dir_rba_prep   = ${dir_inroot}/data_71_rba_prep/${grp_label}

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
set sdir_rba_prep  = ${dir_rba_prep}/${subj}  #/${ses}

# extra datasets
set dir_extra      = ${dir_inroot}/extra_dsets
set template       = ${dir_extra}/MNI152_2009_template_SSW.nii.gz
set grid_template  = ${dir_extra}/T1.grid_template.nii.gz
set atl_glass      = ${dir_extra}/MNI_Glasser_HCP_v1.0.nii.gz

# --------------------------------------------------------------------------
# data and control variables
# --------------------------------------------------------------------------

# dataset inputs
set sdir_apres = ${sdir_ap}/${subj}.results

# control variables

# put this here, because having the '#' creates issues with swarm execution
if ( "${cond}" == "gain" ) then
    set beta = "Resp#1_Coef"
else if ( "${cond}" == "loss" ) then
    set beta = "Resp#2_Coef"
else
    echo "** ERROR: bad variable value for cond: '${cond}'"
    exit 1
endif


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
    set sdir_BW  = ${sdir_rba_prep}
    set sdir_rba_prep  = /lscratch/$SLURM_JOBID/${subj} #_${ses}

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

\mkdir -p ${sdir_rba_prep}

cd ${sdir_rba_prep}

# ============================================================
echo "++ Extract ROI info for: FS-2000 (Desikan Killiany)"

set dset_roi  = ${sdir_apres}/follow_ROI_e00gmr+tlrc.HEAD    # FS D-K atl

# get GM ROI list, remove non-ROI like ones, and then get the col of names
set dir_abin = `which afni`
set dir_abin = ${dir_abin:h}
set all_gmrois = `grep --color=never tiss__gm                 \
                    ${dir_abin}/afni_fs_aparc+aseg_2000.txt   \
                    | grep -v "Cerebral-Cortex"               \
                    | awk '{print $2}'`

echo "++ Found ${#all_gmrois} ROI labels"

# prep and clear stats file
set bname       = roistats_${subj}_ROI_FS_REN_gmrois
set file_ostats = ${bname}.txt

printf "%-10s  %-35s %10s\n" "subjID"   "roi"  "eff_est" > ${file_ostats}

foreach gmroi ( ${all_gmrois} )
    echo "++ proc gmroi: ${gmroi}"
    set info = `3dROIstats \
                -quiet \
                -mask ${dset_roi}"<${gmroi}>" \
                "${sdir_apres}/stats.${subj}_REML+tlrc.HEAD[${beta}]"`

    if ( ${status} ) then
        set ecode = 1
        goto COPY_AND_EXIT
    endif

    printf "%-10s  %-35s %10f\n" ${subj} ${gmroi} ${info} >> ${file_ostats}

    # and prep for ttest
    set file_1D     = ${bname}/beta.${subj}.${gmroi}.1D
    \mkdir -p ${bname}
    printf "%10s\n" "${info}" > ${file_1D}
end

# ============================================================
echo "++ Extract ROI info for: Glasser atlas"

# for grid reference
set dset_stats = ( ${sdir_apres}/stats.${subj}_REML+tlrc.HEAD )

set dset_roi = tmp_MNI_Glasser_${subj}.nii.gz
3dresample  -overwrite       \
    -input   ${atl_glass}    \
    -master  ${dset_stats}   \
    -rmode   NN              \
    -prefix  ${dset_roi}

if ( ${status} ) then
    set ecode = 1
    goto COPY_AND_EXIT
endif

# reattach labels and cmap
3drefit -copytables ${atl_glass} \
    ${dset_roi}
3drefit -cmap INT_CMAP           \
    ${dset_roi}

# get GM ROI list, remove 'unknown', sort
set lt_temp = tmp_MNI_Glasser_labeltable.niml.lt
3dinfo -labeltable ${dset_roi}  > ${lt_temp}
set all_gmrois = `@MakeLabelTable -all_labels -labeltable ${lt_temp} \
                    | grep --color=never -v "Unknown"                \
                    | sort`

echo "++ Found ${#all_gmrois} ROI labels"

# prep and clear stats file
set bname       = roistats_${subj}_ROI_MNI_Glass_gmrois
set file_ostats = ${bname}.txt

printf "%-10s  %-35s %10s\n" "subjID"   "roi"  "eff_est" > ${file_ostats}

foreach gmroi ( ${all_gmrois} )
    echo "++ proc gmroi: ${gmroi}"
    set info = `3dROIstats \
                -quiet \
                -mask ${dset_roi}"<${gmroi}>" \
                "${sdir_apres}/stats.${subj}_REML+tlrc.HEAD[${beta}]"`

    if ( ${status} ) then
        set ecode = 1
        goto COPY_AND_EXIT
    endif

    printf "%-10s  %-35s %10f\n" ${subj} ${gmroi} ${info} >> ${file_ostats}

    # and prep for ttest
    set file_1D     = ${bname}/beta.${subj}.${gmroi}.1D
    \mkdir -p ${bname}
    printf "%10s\n" "${info}" > ${file_1D}
end


if ( ${status} ) then
    echo "++ FAILED RBA_PREP: ${ap_label}"
    set ecode = 10
    goto COPY_AND_EXIT
else
    echo "++ FINISHED RBA_PREP: ${ap_label}"
endif

# ---------------------------------------------------------------------------

COPY_AND_EXIT:

# ----------------------------- biowulf-cmd --------------------------------
# copy back from /lscratch to "real" location
if( ${usetemp} && -d ${sdir_rba_prep} ) then
    echo "++ Used /lscratch"
    echo "++ Copy from: ${sdir_rba_prep}"
    echo "          to: ${sdir_BW}"
    \mkdir -p ${sdir_BW}
    \cp -pr   ${sdir_rba_prep}/* ${sdir_BW}/.

    # reset group permission
    chgrp -R ${grp_own} ${sdir_BW}
    chmod -R g+w ${sdir_BW}
endif
# ---------------------------------------------------------------------------

if ( ${ecode} ) then
    echo "++ BAD FINISH: RBA_PREP (ecode = ${ecode})"
else
    echo "++ GOOD FINISH: RBA_PREP"
endif

exit ${ecode}

