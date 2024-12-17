#!/bin/tcsh

# GTKYD: Getting To Know Your Data 
# -> preliminary info and QC  
# -> does not use lscratch

# NOTES
#
# + This is a Biowulf script (has slurm stuff)
# + Run this script in the scripts/ dir, to execute the corresponding do_*tcsh
# NO session level here

# To execute:  
#     tcsh RUN_SCRIPT_NAME

# --------------------------------------------------------------------------

# specify script to execute
set cmd           = 01_gtkyd

# upper directories
set dir_scr       = $PWD

# define this with abs path here
cd ..
set dir_inroot    = $PWD
cd -

set dir_log        = ${dir_inroot}/logs
set dir_swarm      = ${dir_inroot}/swarms
set dir_store      = /data/SSCC_NARPS/globus_sync/ds001205 # data on biowulf
set dir_basic      = ${dir_store}   #${dir_inroot}/data_00_basic
set dir_gtkyd      = ${dir_inroot}/data_${cmd}

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

# ** make the output directory here **
\mkdir -p ${dir_gtkyd}

# get list of all subj IDs for proc, per group
cd ${dir_basic}
set all_subj = ( sub-* )
cd -

cat <<EOF

++ Proc command:  ${cmd}
++ Found ${#all_subj} subj:

EOF

# -------------------------------------------------------------------------
# **build glob**

# initialize and clear text files to hold lists of subj dsets
set file_all_anat = ${dir_gtkyd}/list_anat.txt
set file_all_epi  = ${dir_gtkyd}/list_epi.txt

printf "" > ${file_all_anat}
printf "" > ${file_all_epi}

# count the number of dsets per modality
set file_num_anat = ${dir_gtkyd}/list_num_anat.txt
set file_num_epi  = ${dir_gtkyd}/list_num_epi.txt

printf "" > ${file_num_anat}
printf "" > ${file_num_epi}


# loop over all subj
foreach subj ( ${all_subj} )
    echo "++ Prepare cmd for: ${subj}"

    # mirror dirs/globbing in later scripts; note that this format
    # assumes there is no ses dir, which is true here
    set sdir_anat = ( ${dir_basic}/${subj}/anat )
    set sdir_epi  = ( ${dir_basic}/${subj}/func )

    set dset_anat_00  = ( ${sdir_anat}/${subj}*T1w.nii.gz )  #${ses}
    set dsets_epi     = ( ${sdir_epi}/${subj}_*task*bold.nii* ) #${ses}

    # write out dset lists

    foreach dset ( ${dset_anat_00} )
        echo ${dset} >> ${file_all_anat}
    end

    foreach dset ( ${dsets_epi} )
        echo ${dset} >> ${file_all_epi}
    end

    # write out dset counts

    echo ${#dset_anat_00} >> ${file_num_anat}
    echo ${#dsets_epi}    >> ${file_num_epi}
end

# set up log and run
set log = ${cdir_log}/log_${cmd}.txt

echo "tcsh -x do_${cmd}.tcsh ${file_all_epi}  \\"         >> ${scr_swarm}
echo "       ${file_all_anat} |& tee ${log}"              >> ${scr_swarm}




# -------------------------------------------------------------------------
# run swarm command
cd ${dir_scr}

echo "++ And start swarming: ${scr_swarm}"

swarm                                                              \
    -f ${scr_swarm}                                                \
    --partition=norm,quick                                         \
    --threads-per-process=2                                        \
    --gb-per-process=3                                             \
    --time=03:59:00                                                \
    #--gres=lscratch:10                                             \
    --logdir=${cdir_log}                                           \
    --job-name=job_${cmd}                                          \
    --merge-output                                                 \
    --usecsh
