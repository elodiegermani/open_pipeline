#!/bin/tcsh

# EVENTS: create stim events files

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

# upper directories
set dir_inroot     = ${PWD:h}                        # one dir above scripts/
set dir_log        = ${dir_inroot}/logs
set dir_store      = /data/SSCC_NARPS/globus_sync/ds001205 # data on biowulf
set dir_basic      = ${dir_store}    #${dir_inroot}/data_00_basic
set dir_deob       = ${dir_inroot}/data_02_deob
set dir_fs         = ${dir_inroot}/data_12_fs
set dir_ssw        = ${dir_inroot}/data_13_ssw
set dir_events     = ${dir_inroot}/data_15_events

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

# extra datasets
set dir_extra      = ${dir_inroot}/extra_dsets
set template       = ${dir_extra}/MNI152_2009_template_SSW.nii.gz
set grid_template  = ${dir_extra}/T1.grid_template.nii.gz

# --------------------------------------------------------------------------
# data and control variables
# --------------------------------------------------------------------------

# dataset inputs
set taskname      = MGT
set all_tfile     = ( ${sdir_timing}/${subj}_task-${taskname}_run-0{1,2,3,4}_events.tsv )

set all_class     = ( Resp NoResp )

# control variables

# check available N_threads and report what is being used
set nthr_avail = `afni_system_check.py -disp_num_cpu`
set nthr_using = `afni_check_omp`

echo "++ INFO: Using ${nthr_avail} of available ${nthr_using} threads"

# ----------------------------- biowulf-cmd --------------------------------
# try to use /lscratch for speed 
if ( -d /lscratch/$SLURM_JOBID ) then
    set usetemp  = 1
    set sdir_BW  = ${sdir_events}
    set sdir_events  = /lscratch/$SLURM_JOBID/${subj} #_${ses}

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

\mkdir -p ${sdir_events}

# create both duration modulated and non-modulated timing files
set tempfile = ${sdir_events}/tmp.awk.txt

foreach class ( ${all_class} )
    set oname = ${sdir_events}/times.$class.txt
    printf "" > ${oname}

    foreach tfile ( ${all_tfile} )

        # for NoResp, just use 4s events, without modulation
        if ( "${class}" == "NoResp" ) then
            awk '{if($6 == "NoResp") printf "%s:%s ", $1, $2}' \
                ${tfile} >! ${tempfile}
        else
            awk '{if($2 == 4 && $6 != "NoResp")          \
                printf "%s*%s*%s:%s ", $1, $3, $4, $5}'  \
                ${tfile} >! ${tempfile}
        endif
        set nc = `cat ${tempfile} | wc -w`

        if ( ${nc} == 0 ) then
            echo "-1:1 -1:1" >> ${oname}
        else if ( ${nc} == 1 ) then
            echo "`cat ${tempfile}` -1:1" >> ${oname}
        else
            echo "`cat ${tempfile}`" >> ${oname}
        endif
    end
    echo "++ created timing file: ${oname}"
end

\rm -f ${tempfile}


# and make an event_list file, for easy perusal
cd ${sdir_events}
timing_tool.py                                                               \
    -multi_timing                times.*.txt                                 \
    -multi_timing_to_event_list  GE:ALL events.txt
cd -

if ( ${status} ) then
    set ecode = 1
    goto COPY_AND_EXIT
endif

echo "++ done proc ok"

# ---------------------------------------------------------------------------

COPY_AND_EXIT:

# ----------------------------- biowulf-cmd --------------------------------
# copy back from /lscratch to "real" location
if( ${usetemp} && -d ${sdir_events} ) then
    echo "++ Used /lscratch"
    echo "++ Copy from: ${sdir_events}"
    echo "          to: ${sdir_BW}"
    \mkdir -p ${sdir_BW}
    \cp -pr   ${sdir_events}/* ${sdir_BW}/.

    # reset group permission
    chgrp -R ${grp_own} ${sdir_BW}
    chmod -R g+w ${sdir_BW}
endif
# ---------------------------------------------------------------------------

if ( ${ecode} ) then
    echo "++ BAD FINISH: EVENTS (ecode = ${ecode})"
else
    echo "++ GOOD FINISH: EVENTS"
endif

exit ${ecode}

