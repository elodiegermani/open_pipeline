#!/bin/tcsh

# make masks of data within MNI-reference mask for cases of:
# + where data is nonzero
# + where data is >thr
# + where data is <-thr
# + where data is > |thr|

set dset_grid = ~/REF_TEMPLATES/MNI152_mask_222.nii.gz

set thrval    = 3

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

        # the specific input dset, which was created earlier with this
        # recipe
        set dset_res = "${odir}/dset_${iid}_${idir}__${ibase}.nii.gz"

        set dset_m0 = "${odir}/mask_00_${iid}_wbbool.nii.gz"
        set dset_m1 = "${odir}/mask_01_${iid}_posthr.nii.gz"
        set dset_m2 = "${odir}/mask_02_${iid}_negthr.nii.gz"
        set dset_m3 = "${odir}/mask_03_${iid}_allthr.nii.gz"

        echo "++ dset name: '${ff}'"
        echo "++ dset_m0  : '${dset_m0}'"
        3dcalc -echo_edu                           \
            -overwrite                             \
            -a       "${dset_res}"                 \
            -b       "${dset_grid}"                \
            -expr    "bool(a)*step(b)"             \
            -prefix  "${dset_m0}"

        if ( $status ) then
            echo "** ERROR: crash here"
            exit 10
        endif

        echo "++ dset_m1  : '${dset_m1}'"
        3dcalc                                     \
            -overwrite                             \
            -a       "${dset_res}"                 \
            -b       "${dset_grid}"                \
            -expr    "ispositive(a-${thrval})*step(b)"  \
            -prefix  "${dset_m1}"

        if ( $status ) then
            echo "** ERROR: crash here"
            exit 11
        endif

        echo "++ dset_m1  : '${dset_m2}'"
        3dcalc                                     \
            -overwrite                             \
            -a       "${dset_res}"                 \
            -b       "${dset_grid}"                \
            -expr    "isnegative(a+${thrval})*step(b)"  \
            -prefix  "${dset_m2}"

        if ( $status ) then
            echo "** ERROR: crash here"
            exit 12
        endif

        echo "++ dset_m1  : '${dset_m3}'"
        3dcalc                                     \
            -overwrite                             \
            -a       "${dset_res}"                 \
            -b       "${dset_grid}"                \
            -expr    "step(ispositive(a-${thrval})+isnegative(a+${thrval}))*step(b)"  \
            -prefix  "${dset_m3}"

        if ( $status ) then
            echo "** ERROR: crash here"
            exit 13
        endif

    end
end





