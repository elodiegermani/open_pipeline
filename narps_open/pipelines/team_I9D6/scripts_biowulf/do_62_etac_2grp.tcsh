#!/bin/tcsh

# ETAC: 3dttest with ETAC opts for a group contrast
# will output into the particular AP dir, hence use ap_label

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
set grp1           = "$1"                          # grep to extract from TSV
set grp2           = "$2"
set cond           = "$3"
set ap_label       = 22_ap_task
set grp_label      = group_analysis.ETAC.2grp.${grp1}-${grp2}.${cond}

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

set dir_grpqc      = ${dir_ap}/QC
set dir_etac       = ${dir_ap}/${grp_label}

# subject directories
#set sdir_basic     = ${dir_basic}/${subj}  #/${ses}
#set sdir_epi       = ${sdir_basic}/func
#set sdir_anat      = ${sdir_basic}/anat
#set sdir_timing    = ${sdir_epi}
#set sdir_deob      = ${dir_deob}/${subj}   #/${ses}
#set sdir_fs        = ${dir_fs}/${subj}  #/${ses}
#set sdir_suma      = ${sdir_fs}/SUMA
#set sdir_ssw       = ${dir_ssw}/${subj} #/${ses}
#set sdir_events    = ${dir_events}/${subj} #/${ses}
#set sdir_ap        = ${dir_ap}/${subj}  #/${ses}

# extra datasets
set dir_extra      = ${dir_inroot}/extra_dsets
set template       = ${dir_extra}/MNI152_2009_template_SSW.nii.gz
set grid_template  = ${dir_extra}/T1.grid_template.nii.gz

# --------------------------------------------------------------------------
# data and control variables
# --------------------------------------------------------------------------

# dataset inputs

set mask_name     = group_mask.inter.nii.gz
set all_dset_reml = ( ${dir_ap}/sub-*/*.results/stats.sub*REML+tlrc.HEAD )

# participants file
set part_file   = ${dir_store}/participants.tsv
# all subs in input group
set all_subj1    = ( `grep --color=never ${grp1} ${part_file} \
                        | awk '{print $1}'` )
set all_subj2    = ( `grep --color=never ${grp2} ${part_file} \
                        | awk '{print $1}'` )
# all subs to drop
set all_drop    = ( `cat ${dir_grpqc}/outliers.c.drop.subs.txt` )

echo "++ Found ${#all_subj1} in the initial list of subs in grp1 '${grp1}'"
echo "++ Found ${#all_subj2} in the initial list of subs in grp2 '${grp2}'"
echo "++ The full (multi-group) drop list has ${#all_drop} subj"
echo "++ The full (multi-group) REML dset list has ${#all_dset_reml} files"

# if there are subjects to drop, include such an option
if ( ${#all_drop} > 0 ) then
   set drop_opt = ( -dset_sid_omit_list ${all_drop} )
else
   set drop_opt = ( )
endif

# control variables
set label     = ${grp1}-${grp2}.${cond}
set tt_script = run.tt.${label}.tcsh

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
    set sdir_BW  = ${dir_etac}
    set dir_etac = /lscratch/$SLURM_JOBID #/${subj} #_${ses}

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

\mkdir -p ${dir_etac}

# copy a couple of datasets, for convenience
\cp -p ${template} ${dir_etac}/.
3dcopy -overwrite ${dir_grpqc}/${mask_name} ${dir_etac}/

cd ${dir_etac}

# list ALL subject datasets, then specify which to use/drop
gen_group_command.py                                                         \
    -command        3dttest++                                                \
    -write_script   ${tt_script}                                             \
    -dsets          ${all_dset_reml}                                         \
    -dset_sid_list  ${all_subj1}                                             \
    ${drop_opt}                                                              \
    -dsets          ${all_dset_reml}                                         \
    -dset_sid_list  ${all_subj2}                                             \
    ${drop_opt}                                                              \
    -subj_prefix    sub-                                                     \
    -set_labels     ${label}                                                 \
    -subs_betas     "${beta}"                                                \
    -verb           2                                                        \
    -options                                                                 \
          -mask     ${mask_name}                                             \
          -Clustsim                                                          \
          -ETAC     -ETAC_blur  2 4 6                                        \
          -ETAC_opt pthr=0.01,0.005,0.002,0.001,0.0005:fpr=MUCHO             \
    |& tee out.ggc


if ( ${status} ) then
    set ecode = 1
    goto COPY_AND_EXIT
endif

tcsh -x ${tt_script} |& tee out.${tt_script}


if ( ${status} ) then
    echo "++ FAILED ETAC: ${grp_label}"
    set ecode = 1
    goto COPY_AND_EXIT
else
    echo "++ FINISHED ETAC: ${grp_label}"
endif

# ---------------------------------------------------------------------------

COPY_AND_EXIT:

# ----------------------------- biowulf-cmd --------------------------------
# copy back from /lscratch to "real" location
if( ${usetemp} && -d ${dir_etac} ) then
    echo "++ Used /lscratch"
    echo "++ Copy from: ${dir_etac}"
    echo "          to: ${sdir_BW}"
    \mkdir -p ${sdir_BW}
    \cp -pr   ${dir_etac}/* ${sdir_BW}/.

    # reset group permission
    chgrp -R ${grp_own} ${sdir_BW}
    chmod -R g+w ${sdir_BW}
endif
# ---------------------------------------------------------------------------

if ( ${ecode} ) then
    echo "++ BAD FINISH: ETAC (ecode = ${ecode})"
else
    echo "++ GOOD FINISH: ETAC"
endif

exit ${ecode}

