#!/bin/tcsh

# QC: GSSRT QC, inclusion/exclusion criteria for subj
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
#set subj           = $1                             # subj not used here
#set ses            = $2
set ap_label       = 22_ap_task

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

# for globbing participants.tsv
set all_grp = ( equalRange equalIndif )

# control variables
set part_file   = ${dir_store}/participants.tsv

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
    set sdir_BW  = ${dir_grpqc}
    set dir_grpqc = /lscratch/$SLURM_JOBID #/${subj} #_${ses}

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

\mkdir -p ${dir_grpqc}

set gssrt_cmd = ${dir_grpqc}/do_gssrt.tcsh

# write AP command to file
cat <<EOF >! ${gssrt_cmd}
#!/bin/tcsh

echo "++ Start GSSRT script"

set dir_ap      = ${dir_ap}
set all_infiles = ( \${dir_ap}/sub*/s*.results/out.ss*.txt )

echo "++ Found \${#all_infiles} out.ss*.txt review files"

# a kind of look for bad subjects
gen_ss_review_table.py                                                       \
    -outlier_sep      space                                                  \
    -report_outliers  'AFNI version' VARY                                    \
    -report_outliers  'censor fraction' GE 0.1                               \
    -report_outliers  'average censored motion' GE 0.1                       \
    -report_outliers  'max censored displacement' GE 8                       \
    -report_outliers  'num regs of interest' NE 4                            \
    -report_outliers  'TSNR average' LT 30                                   \
    -report_outliers  'final voxel resolution' NE 2                          \
    -report_outliers  'num TRs per run' NE 453                               \
    -infiles          \${all_infiles}                                        \
    -write_outliers   outliers.a.long.txt                                    \
    -overwrite

gen_ss_review_table.py                                                       \
    -outlier_sep      space                                                  \
    -report_outliers  'AFNI version' VARY                                    \
    -report_outliers  'num regs of interest' VARY                            \
    -report_outliers  'final voxel resolution' VARY                          \
    -report_outliers  'num TRs per run' VARY                                 \
    -infiles          \${all_infiles}                                        \
    -write_outliers   outliers.a.VARY.txt                                    \
    -overwrite

# ** the one that will be used for incl/excl in this study **
gen_ss_review_table.py                                                       \
    -outlier_sep      space                                                  \
    -report_outliers  'censor fraction' GE 0.1                               \
    -report_outliers  'average censored motion' GE 0.1                       \
    -report_outliers  'max censored displacement' GE 8                       \
    -infiles          \${all_infiles}                                        \
    -write_outliers   outliers.b.short.txt                                   \
    -overwrite

# ============================================================================
# list bad subj to drop

set bad_subs = ( \`awk '{if (NR>2) print \$1}' outliers.b.short.txt\` )
awk '{if (NR>2) print \$1}' outliers.b.short.txt \
    > outliers.c.drop.subs.txt
echo ""
echo "=== subjects to drop: \${bad_subs}"
echo ""

# ============================================================================
# generate review table spreadsheet

echo "====== generate review table and label list"
gen_ss_review_table.py                                                       \
    -tablefile  ss_review_table.xls                                          \
    -infiles    \${all_infiles}

# ... and note labels
gen_ss_review_table.py                                                       \
    -showlabs                                                                \
    -infiles   \${all_infiles}                                               \
    >& ss_review_labels.txt

# ============================================================================
# ACF params and average

echo "====== collect and average ACF parameters"

# generate review table spreadsheet
grep -h ACF \${all_infiles}                                                  \
    | awk -F: '{print \$2}'                                                  \
    > out.ACF.vals.1D

grep -h ACF \${all_infiles}                                                  \
    | awk -F: '{print \$2}'                                                  \
    | 3dTstat -mean -prefix - 1D:stdin\\'                                    \
    > out.ACF.means.1D

# ============================================================================
# masks

echo "====== making intersection, mean and 70% masks"

set all_mask = ( \${dir_ap}/sub*/s*.results/mask_epi_anat*.HEAD )

echo "++ Found \${#all_mask} mask_epi_anat*.HEAD dsets"

3dTstat                                                                      \
    -mean                                                                    \
    -prefix  mask.mean.nii.gz                                                \
    "\${all_mask}"

3dmask_tool                                                                  \
    -prefix  group_mask.7.nii.gz                                             \
    -frac    0.7                                                             \
    -input   \${all_mask}

3dmask_tool                                                                  \
    -prefix  group_mask.inter.nii.gz                                         \
    -frac    1.0                                                             \
    -input   \${all_mask}

set group_mask = group_mask.inter.nii.gz

# ============================================================================
# get anats and EPI for registration comparison

echo "====== making mean and TCAT anat and EPI dsets"

set all_epi_vr     = ( \${dir_ap}/sub*/s*.results/final_epi_vr*.HEAD )
set all_anat_final = ( \${dir_ap}/sub*/s*.results/anat_final*.HEAD )

echo "++ Found \${#all_epi_vr} final_epi_vr*.HEAD dsets"
echo "++ Found \${#all_anat_final} anat_final*.HEAD"

# TR opt just to quiet warnings
3dTcat                                                                       \
    -tr      1                                                               \
    -prefix  all.EPI.vr.tcat                                                 \
    \${all_epi_vr}

3dTcat                                                                       \
    -tr      1                                                               \
    -prefix  all.anat.final.tcat                                             \
    \${all_anat_final}

3dTstat                                                                      \
    -mean                                                                    \
    -prefix  all.EPI.mean                                                    \
    "\${all_epi_vr}"

3dTstat                                                                      \
    -mean                                                                    \
    -prefix  all.anat.mean                                                   \
    "\${all_anat_final}"


# might make a probability map of FS ROIs, but do it in another script

# ============================================================================
# clustsim?  Naybe not in the case of ETAC no blur

# *** not including here at the moment ***


echo "====== done here"

exit 0

EOF

if ( ${status} ) then
    set ecode = 1
    goto COPY_AND_EXIT
endif

cd ${dir_grpqc}

# execute AP command to make processing script
tcsh -ef ${gssrt_cmd} |& tee log_gssrt_cmd.txt

if ( ${status} ) then
    set ecode = 1
    goto COPY_AND_EXIT
endif

# make lists of subj IDs per group, after applying drop criteria

foreach grp ( ${all_grp} )

    # create list of all subj in this group
    grep --color=never "${grp}" ${part_file} \
        | awk '{print $1}'                   \
        > list_grp_${grp}_all.txt

    # create list of remainder after applying drop rules
    set f1 = outliers.c.drop.subs.txt
    set f2 = list_grp_${grp}_all.txt
    bash -c "comm -13  <(sort ${f1})  <(sort ${f2})"     \
        > list_grp_${grp}_final.txt

    set nsubj_all = `cat list_grp_${grp}_all.txt   | wc -l`
    set nsubj_fin = `cat list_grp_${grp}_final.txt | wc -l`
    echo "++ Final ${grp} list has ${nsubj_fin} in it (from init ${nsubj_all})"
end


if ( ${status} ) then
    echo "++ FAILED QC: ${ap_label}"
    set ecode = 1
    goto COPY_AND_EXIT
else
    echo "++ FINISHED QC: ${ap_label}"
endif

# ---------------------------------------------------------------------------

COPY_AND_EXIT:

# ----------------------------- biowulf-cmd --------------------------------
# copy back from /lscratch to "real" location
if( ${usetemp} && -d ${dir_grpqc} ) then
    echo "++ Used /lscratch"
    echo "++ Copy from: ${dir_grpqc}"
    echo "          to: ${sdir_BW}"
    \mkdir -p ${sdir_BW}
    \cp -pr   ${dir_grpqc}/* ${sdir_BW}/.

    # reset group permission
    chgrp -R ${grp_own} ${sdir_BW}
    chmod -R g+w ${sdir_BW}
endif
# ---------------------------------------------------------------------------

if ( ${ecode} ) then
    echo "++ BAD FINISH: QC (ecode = ${ecode})"
else
    echo "++ GOOD FINISH: QC"
endif

exit ${ecode}

