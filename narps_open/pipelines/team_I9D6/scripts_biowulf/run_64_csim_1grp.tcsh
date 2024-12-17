#!/bin/tcsh

# CSIM: 3dttest with CSIM opts for a single group

# NOTES
#
# + This is a Biowulf script (has slurm stuff)
# + Run this script in the scripts/ dir, to execute the corresponding do_*tcsh
# NO session level here

# To execute:  
#     tcsh RUN_SCRIPT_NAME

# --------------------------------------------------------------------------

# specify script to execute
set cmd           = 64_csim_1grp

# upper directories
set dir_scr       = $PWD
set dir_inroot    = ..
set dir_log       = ${dir_inroot}/logs
set dir_swarm     = ${dir_inroot}/swarms
set dir_store      = /data/SSCC_NARPS/globus_sync/ds001205 # data on biowulf
set dir_basic      = ${dir_store}   #${dir_inroot}/data_00_basic


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

set all_grp  = ( equalRange equalIndif )
set all_cond = ( gain loss)

foreach grp ( ${all_grp} )
    foreach cond ( ${all_cond} )
        echo "++ Prepare cmd for: ${grp} ${cond}"

        set log = ${cdir_log}/log_${cmd}_${grp}_${cond}.txt

        # run command script (verbosely, and don't use '-e'); log terminal text.
        echo "tcsh -xf ${scr_cmd} ${grp} ${cond}  \\"  >> ${scr_swarm}
        echo "     |& tee ${log}"                      >> ${scr_swarm}
    end
end

# -------------------------------------------------------------------------
# run swarm command
cd ${dir_scr}

echo "++ And start swarming: ${scr_swarm}"

swarm                                                              \
    -f ${scr_swarm}                                                \
    --partition=norm,quick                                         \
    --threads-per-process=16                                       \
    --gb-per-process=30                                            \
    --time=3:59:00                                                 \
    --gres=lscratch:30                                             \
    --logdir=${cdir_log}                                           \
    --job-name=job_${cmd}                                          \
    --merge-output                                                 \
    --usecsh
