#!/bin/tcsh


set dset_mask = ~/REF_TEMPLATES/MNI152_mask_222.nii.gz

set all_num = `seq 1 1 9`

foreach num ( ${all_num} )
    echo "++++++++++++++++++++++++ num: ${num} ++++++++++++++++++++++++++++"

    set dir_hyp = res222_narps_hyp${num}
    set grp_dset = ( ${dir_hyp}/DSET*nii* )

    3dpc                                                              \
        -overwrite                                                    \
        -mask    ${dset_mask}                                         \
        -pcsave  5                                                    \
        -prefix  ${dir_hyp}/PC_hyp${num}                              \
        ${grp_dset}

    # ==============================================================
    # get ref dset to check sign of [0]th PC

    set ref_dset = `ls -1 BLARG_TEST_DSET*/*hyp*${num}*unthr*.nii*`
    if ( "${#ref_dset}" != "1" ) then
        echo "** ERROR: found too many ref dsets, or not enough: ${#ref_dset}"
        exit
    else
        3dresample \
            -overwrite \
            -prefix tmp_REF_DSET.nii.gz     \
            -master ${dset_mask}            \
            -input "${ref_dset}"
    endif

    # which is inset and which is refset matters here, solely because
    # of the file we parse later
    3dMatch -echo_edu                                                 \
        -overwrite                                                    \
        -mask    ${dset_mask}                                         \
        -refset  ${dir_hyp}/PC_hyp${num}+tlrc                         \
        -inset   tmp_REF_DSET.nii.gz                                  \
        -prefix  tmp_MATCHED

    if ( $status ) then
        echo "** ERROR: crash here"
        exit 1
    endif

    # get the corr value, and see if it is pos or neg
    set vals   = `cat tmp_MATCHED_REF*.vals`
    set vvv    = "${vals[3]}"
    set signum = `echo "(-1)^(1+ (${vvv} > 0))" | bc`
    echo "++ signum is: '${signum}'"
    # ... and flip the sign of the PC dset, if necessary
    3dcalc   -echo_edu                                                \
        -overwrite                                                    \
        -a      ${dir_hyp}/PC_hyp${num}+tlrc                          \
        -expr   "${signum}*a"                                         \
        -prefix ${dir_hyp}/PC_hyp${num}_sign0.nii.gz

end
