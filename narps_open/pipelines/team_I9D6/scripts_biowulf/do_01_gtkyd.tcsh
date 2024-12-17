#!/bin/tcsh

# GTKYD: Getting To Know Your Data
# -> preliminary info and QC

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

# important for 'clean' output here
setenv AFNI_NO_OBLIQUE_WARNING YES

# initial exit code; we don't exit at fail, to copy partial results back
set ecode = 0
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# top level definitions (constant across demo)
# ---------------------------------------------------------------------------

# labels: different than most other do*.tcsh scripts
set file_all_epi   = $1
set file_all_anat  = $2

set template       = MNI152_2009_template_SSW.nii.gz 

# upper directories
set dir_inroot     = ${PWD:h}                        # one dir above scripts/
set dir_log        = ${dir_inroot}/logs
set dir_store      = /data/SSCC_NARPS/globus_sync/ds001205 # data on biowulf 
set dir_basic      = ${dir_store}                    # holds all sub-* dirs
set dir_gtkyd      = ${dir_inroot}/data_01_gtkyd

# --------------------------------------------------------------------------
# data and control variables
# --------------------------------------------------------------------------

# dataset inputs
set all_anat      = `cat ${file_all_anat}`
set all_epi       = `cat ${file_all_epi}`

# 3dinfo params
set all_info = ( n4 orient ad3 obliquity tr slice_timing \
                 datum )

# 3dBrickStat params
set all_bstat = ( min max )

# nifti_tool fields
set all_nfield = ( datatype sform_code qform_code )


# check available N_threads and report what is being used
set nthr_avail = `afni_system_check.py -disp_num_cpu`
set nthr_using = `afni_check_omp`

echo "++ INFO: Using ${nthr_avail} of available ${nthr_using} threads"

# ----------------------------- biowulf-cmd --------------------------------
# 
# *** not used here ***
#
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# run programs
# ---------------------------------------------------------------------------

# report per data dir
\mkdir -p ${dir_gtkyd}/anat
\mkdir -p ${dir_gtkyd}/func

# report both individual columns, and sort+uniq ones
foreach info ( ${all_info} )
    echo "++ 3dinfo -${info} ..."

    set otxt = ${dir_gtkyd}/anat/rep_info_${info}_su.dat
    echo "# 3dinfo -${info}" > ${otxt}
    3dinfo -${info} ${all_anat} | sort | uniq >> ${otxt}

    set otxt = ${dir_gtkyd}/anat/rep_info_${info}_detail.dat
    echo "# 3dinfo -${info}" > ${otxt}
    3dinfo -${info} -prefix ${all_anat} >> ${otxt}

    set otxt = ${dir_gtkyd}/func/rep_info_${info}_su.dat
    echo "# 3dinfo -${info}" > ${otxt}
    3dinfo -${info} ${all_epi} | sort | uniq >> ${otxt}

    set otxt = ${dir_gtkyd}/func/rep_info_${info}_detail.dat
    echo "# 3dinfo -${info}" > ${otxt}
    3dinfo -${info} -prefix ${all_epi} >> ${otxt}
end

if ( ${status} ) then
    set ecode = 1
    goto COPY_AND_EXIT
endif


# only sort+uniq at the moment
foreach nfield ( ${all_nfield} )
    echo "++ nifti_tool -disp_hdr -field ${nfield} ..."

    set otxt = ${dir_gtkyd}/anat/rep_ntool_${nfield}_su.dat
    echo "# nifti_tool -disp_hdr -field ${nfield}" > ${otxt}
    nifti_tool -disp_hdr -field ${nfield} -quiet -infiles ${all_anat} \
        | sort | uniq >> ${otxt}

    set otxt = ${dir_gtkyd}/func/rep_ntool_${nfield}_su.dat
    echo "# nifti_tool -disp_hdr -field ${nfield}" > ${otxt}
    nifti_tool -disp_hdr -field ${nfield} -quiet -infiles ${all_epi} \
        | sort | uniq >> ${otxt}
end

# report both individual columns, and sort+uniq ones
foreach bstat ( ${all_bstat} )
    echo "++ 3dBrickStat -slow -${bstat} ..."

    set otxt = ${dir_gtkyd}/anat/rep_brickstat_${bstat}_detail.dat
    foreach dset ( ${all_anat} )
        set val  = `3dBrickStat -slow -${bstat} ${dset}`
        set name = `3dinfo -prefix ${dset}`
        printf "%12s %12s\n" "${val}" "${name}" >> ${otxt}
    end

    set otxt_su = ${dir_gtkyd}/anat/rep_brickstat_${bstat}_su.dat
    cat ${otxt} | awk '{print $1}' | sort -n | uniq > ${otxt_su}

    set otxt = ${dir_gtkyd}/func/rep_brickstat_${bstat}_detail.dat
    foreach dset ( ${all_epi} )
        set val  = `3dBrickStat -slow -${bstat} ${dset}`
        set name = `3dinfo -prefix ${dset}`
        printf "%12s %12s\n" "${val}" "${name}" >> ${otxt}
    end

    set otxt_su = ${dir_gtkyd}/func/rep_brickstat_${bstat}_su.dat
    cat ${otxt} | awk '{print $1}' | sort -n | uniq > ${otxt_su}

end

echo "++ done proc ok"

# ---------------------------------------------------------------------------

COPY_AND_EXIT:

# ----------------------------- biowulf-cmd --------------------------------
# 
# *** not used here ***
#
# ---------------------------------------------------------------------------

if ( ${ecode} ) then
    echo "++ BAD FINISH: GTKYD (ecode = ${ecode})"
else
    echo "++ GOOD FINISH: GTKYD"
endif

exit ${ecode}

