#!/bin/tcsh

# NB: this makes a table of whereami results when a Clust_table.1D is
# input.  It rearranges information with some awk-ward fun.
#
# This script is run from a directory with the Clust_mask+tlrc.HEAD
# dataset output by 3dClusterize or the AFNI GUI Clusterize plugin.
# To run, type:
#
#    tcsh do_06_clust_olap.tcsh
#
# Update: Related to a later Message Board question about using a
# FreeSurfer output ROI as an overlap reference, you could take a dset
# (which might be readily be a 'follower ROI dataset' from
# afni_proc.py processing), atlasize it (with @MakeLabelTable) and
# then use it as a ref_atl below.  In detail:
#
#    3dcopy follow_ROI_aaseg+tlrc.HEAD follow_ROI_aaseg_ATLIZE.nii.gz
#    @MakeLabelTable -atlasize_labeled_dset follow_ROI_aaseg_ATLIZE.nii.gz
# 
# ... and then assign 'follow_ROI_aaseg_ATLIZE' to the variabel
# ref_atl below (noting that the filename extension of the atlas
# dataset is not included in the ref_atl variable).
# 
# [PA Taylor (SSCC, NIMH, NIH, USA): June 26, 2023]
# ---------------------------------------------------------------------------

setenv AFNI_WHEREAMI_NO_WARN YES

set ref_atl = MNI_Glasser_HCP_v1.0

set all_type = ( olap )

set min_olap = 10    # minimum percentile for overlap to be included in table

foreach ii ( `seq 1 1 ${#all_type}` )
    set type   = "${all_type[$ii]}"

    echo "++ Make table for: ${type}"

    # start the output file and formatting
    set ofile  = info_table_clust_wami_${type}.txt
    printf "" > ${ofile}
    printf "%5s  %5s   %7s  %s  \n"                       \
            "Clust" "Nvox" "Overlap" "ROI location"     \
        |& tee -a ${ofile}

    set idset  = Clust_mask+tlrc.HEAD            # dumped by GUI-Clusterize
    set nclust = `3dinfo -max "${idset}"`

    set tfile  = __tmp_file_olap.txt

    # go through the dset, int by int, to parse a bit
    foreach nn ( `seq 1 1 ${nclust}` )
        # create zero-based index
        @ mm = $nn - 1

        set nvox = `3dROIstats -nomeanout -quiet -nzvoxels \
                        -mask "${idset}<${nn}>"            \
                        "${idset}"` 

        whereami                                          \
            -omask "${idset}<${nn}>"                      \
            -atlas "${ref_atl}"                           \
            | grep --color=never '% overlap with'         \
            > ${tfile}

        set nrow = `cat ${tfile} | wc -l`

        set NEED_ONE = 1
        foreach rr ( `seq 1 1 ${nrow}` )
            set line = `cat ${tfile} | sed -n ${rr}p`
            set perc = `echo "${line}" | awk '{print $1}'`

            set roi = `echo "${line}"                           \
                        | awk -F'% overlap with' '{print $2}'   \
                        | awk -F, '{print $1}'`


            if ( ${NEED_ONE} ) then
                printf "%5d  %5d  %7.1f%%  %s  \n"             \
                    "${nn}" "${nvox}" "${perc}" "${roi}"       \
                    |& tee -a ${ofile}
                set NEED_ONE = 0
            else if (`echo "${perc} > ${min_olap}" | bc` ) then
                printf "%5s  %5s  %7.1f%%  %s  \n"             \
                    "" "" "${perc}" "${roi}"       \
                    |& tee -a ${ofile}
            endif
        end
    end
end

\rm ${tfile} 

cat <<EOF
------------------------------
DONE.

Check out:
${ofile}

EOF
