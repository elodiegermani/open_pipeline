#!/bin/tcsh

# RBA: run RBA on datatable
# this runs for a particular *group* and *cond*

# NOTES
#
# + This is a Biowulf script (has slurm stuff)
# + Run this script in the scripts/ dir, to execute the corresponding do_*tcsh
# NO session level here

# To execute:  
#     tcsh RUN_SCRIPT_NAME

# --------------------------------------------------------------------------

# specify script to execute---and which AP results to use
set cmd           = 71c_rba
set ap_label      = 22_ap_task

# upper directories
set dir_scr       = $PWD
set dir_inroot    = ..
set dir_log       = ${dir_inroot}/logs
set dir_swarm     = ${dir_inroot}/swarms
set dir_store      = /data/SSCC_NARPS/globus_sync/ds001205 # data on biowulf
set dir_basic      = ${dir_store}   #${dir_inroot}/data_00_basic

set dir_ap         = ${dir_inroot}/data_${ap_label}
set dir_grpqc      = ${dir_ap}/QC

# running
set cdir_log      = ${dir_log}/logs_${cmd}
set scr_swarm     = ${dir_swarm}/swarm_${cmd}.txt
set scr_cmd       = ${dir_scr}/do_${cmd}.tcsh

# --------------------------------------------------------------------------

\mkdir -p ${cdir_log}
\mkdir -p ${dir_swarm}

# clear away older swarm script 
if ( -e ${scr_swarm} ) then
    \rm ${scr_swarm}
endif

# --------------------------------------------------------------------------
# simply run, don't swarm

set grp      = equalRange
set cond     = gain

cd ${dir_inroot}/data_71_rba_prep/${grp}.${cond}
set bpath = $PWD
set all_dtable = ( table*txt )
cd -

foreach dtable ( ${all_dtable} )
    set bname = ${dtable:t:r}
    set opref = fit_rba.${bname}.dat

    set log      = ${cdir_log}/log_${cmd}_grp_${grp}.${cond}.${bname}.txt

    echo "tcsh -xf ${scr_cmd} ${grp} ${cond}   \\" >> ${scr_swarm}
    echo "         ${bpath}/${dtable} ${opref} \\" >> ${scr_swarm}
    echo "   |& tee ${log}"                        >> ${scr_swarm}
end


# -------------------------------------------------------------------------
# run swarm command
cd ${dir_scr}

echo "++ And start swarming: ${scr_swarm}"

# don't need to use scratch disk here, just text files
swarm                                                              \
    -f ${scr_swarm}                                                \
    --partition=norm                                               \
    --threads-per-process=8                                        \
    --gb-per-process=3                                             \
    --time=10:59:00                                                \
    #--gres=lscratch:100                                            \
    --logdir=${cdir_log}                                           \
    --job-name=job_${cmd}                                          \
    --merge-output                                                 \
    --usecsh
