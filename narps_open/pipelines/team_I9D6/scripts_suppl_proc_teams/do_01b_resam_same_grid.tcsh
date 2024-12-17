#!/bin/tcsh

set dset_grid = ~/REF_TEMPLATES/MNI152_mask_222.nii.gz

set all_num = `seq 1 1 9`

foreach num ( ${all_num} )
    set all_dset = `ls -1 NARP*/*hyp*${num}*unthr*.nii*`

    set odir   = res222_narps_hyp${num}
    \mkdir -p ${odir}

    foreach nn ( `seq 1 1 ${#all_dset}` )
        set nnn     = `printf "%03d" $nn`
        set ff      = "${all_dset[$nn]}"

        # base name of vol, and make a list of all prefixes for later
        set ibase   = `3dinfo -prefix_noext "${ff}"`
        set idir    = `dirname "${ff}"`
        set iid     = `printf "${idir}" | tail -c 4`

        set dset_res = "${odir}/dset_${iid}_${idir}__${ibase}.nii.gz"

        echo "++ dset nam: '${ff}'"
        echo "++ dset_res: '${dset_res}'"
        3dresample -echo_edu                \
            -overwrite                      \
            -prefix "${dset_res}"           \
            -master "${dset_grid}"          \
            -input  "${ff}"

        if ( $status ) then
            echo "** ERROR: crash here"
            exit 1
        endif
    end

    # concatenate everything
    cd ${odir}
    3dTcat -prefix DSET_ALL_hyp${num}_222.nii.gz dset_*
    cd -
end





