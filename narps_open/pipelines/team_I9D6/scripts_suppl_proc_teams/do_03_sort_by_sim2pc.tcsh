#!/bin/tcsh

set dset_grid = ~/REF_TEMPLATES/MNI152_mask_222.nii.gz

set all_num = `seq 1 1 9`

foreach num ( ${all_num} )
    
    set ref_dset = `ls -1 res222_narps_hyp${num}/PC_hyp${num}_sign0.nii.gz`

    if ( "${#ref_dset}" != "1" ) then
        echo "** ERROR: found too many ref dsets, or not enough: ${#ref_dset}"
        exit
    endif

    # now we make (sorted) lists of both the original dsets...
    set ofile  = "list_match_${num}.txt"
    set ofile2 = "list_match_${num}_sort.txt"
    printf "" > ${ofile}
    # ... and the resampled ones
    set rfile  = "list_match_${num}_RES.txt"
    set rfile2 = "list_match_${num}_RES_sort.txt"
    printf "" > ${rfile}

    set all_dset = ( res222_narps_hyp${num}/dset* )

    foreach nn ( `seq 1 1 ${#all_dset}` )
        set nnn     = `printf "%03d" $nn`
        set ff      = "${all_dset[$nn]}"
        # base name of vol, from which we extract 4char ID
        set ibase   = `3dinfo -prefix_noext "${ff}"`
        set iid     = `printf "${ibase}" | head -c 9 | tail -c 4`

        3dMatch  -echo_edu                \
           -overwrite                     \
           -inset    "${ff}"              \
           -refset   ${ref_dset}          \
           -mask     ${dset_grid}         \
           -prefix   tmp_MATCHED 

        if ( $status ) then
            echo "** ERROR: crash here"
            exit 1
        endif

        set vals = `cat tmp_MATCHED_REF*.vals`
        set vvv  = "${vals[3]}"

        set orig_dset = `\ls -1 NARPS-${iid}/*hyp*${num}*unthr*.nii*`

        printf "%0.3f     %s\n"  ${vvv} "${orig_dset}"  >> ${ofile}
        printf "%0.3f     %s\n"  ${vvv} "${ff}"         >> ${rfile}

    end

    sort -nr < ${ofile} > ${ofile2}
    sort -nr < ${rfile} > ${rfile2}

end





