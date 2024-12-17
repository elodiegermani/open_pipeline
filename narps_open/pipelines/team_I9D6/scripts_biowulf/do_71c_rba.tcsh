#!/bin/tcsh

# RBA: run RBA on the data tables that are present

# NOTES
#
# + This is a Biowulf script (has slurm stuff)
# + Run this script in the scripts/ dir, via the corresponding run_*tcsh
# + NO session level here.

# ----------------------------- biowulf-cmd ---------------------------------
# load modules
source /etc/profile.d/modules.csh
module load afni R

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
set grp            = $1
set cond           = $2
set fname_dtable   = $3
set prefix         = $4

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

# extra datasets
set dir_extra      = ${dir_inroot}/extra_dsets
set template       = ${dir_extra}/MNI152_2009_template_SSW.nii.gz
set grid_template  = ${dir_extra}/T1.grid_template.nii.gz
set atl_glass      = ${dir_extra}/MNI_Glasser_HCP_v1.0.nii.gz

# --------------------------------------------------------------------------
# data and control variables
# --------------------------------------------------------------------------

# dataset inputs

# control variables


# one way of many ways to set to available number of CPUs:
# afni_check_omp respects ${OMP_NUM_THREADS}
set njobs         = `afni_check_omp`

# check available N_threads and report what is being used
set nthr_avail = `afni_system_check.py -disp_num_cpu`
set nthr_using = `afni_check_omp`

echo "++ INFO: Using ${nthr_avail} of available ${nthr_using} threads"

# ----------------------------- biowulf-cmd --------------------------------
# don't use lscratch here

set usetemp  = 0

# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# run programs
# ---------------------------------------------------------------------------

cd ${dir_rba_prep}

# ============================================================

RBA                                                                          \
    -prefix      ${prefix}                                                   \
    -chains      4                                                           \
    -iterations  1000                                                        \
    -mean        'eff_est~1+(1|roi)+(1|subjID)'                              \
    -sigma       '1+(1|roi)+(1|subjID)'                                      \
    -ROI         'roi'                                                       \
    -EOI         'Intercept'                                                 \
    -dataTable   ${fname_dtable}

if ( ${status} ) then
    set ecode = 3
    goto COPY_AND_EXIT
endif

# ---------------------------------------------------------------------------

COPY_AND_EXIT:

# ----------------------------- biowulf-cmd --------------------------------
# not using lscratch here
# ---------------------------------------------------------------------------

if ( ${ecode} ) then
    echo "++ BAD FINISH: RBA_COMB (ecode = ${ecode})"
else
    echo "++ GOOD FINISH: RBA_COMB"
endif

exit ${ecode}

