#!/bin/tcsh

# make masks of data within MNI-reference mask for cases of:
# + where data is nonzero
# + where data is >thr
# + where data is <-thr
# + where data is > |thr|

# make corr mats and images

set dset_grid      = ~/REF_TEMPLATES/MNI152_mask_222.nii.gz
set dset_grid_zoom = narps_mni_amyg_vmpfc_vstriatum_FS_resample_to_res_INFL1_res222_mskd.nii.gz # inflated version of Hyp #1&3 ROIs, res to 2x2x2 and mskd in WB mask

set thrval    = 3

set all_num = `seq 1 1 9`

foreach num ( ${all_num} )

    # get the list of dsets, ordered, from *this* file
    set all_dset = `cat list_match_${num}_sort.txt | awk '{print $2}'`
    set odir     = res222_narps_hyp${num}

    echo "++ Hyp number : ${num}"
    echo "++ N all_dset : ${#all_dset}"
    echo "++   all_dset : ${all_dset}"

    # parse names, one by one; accumulate files in order, too
    set all_iid = ()
    set all_dset_res = ()
    set all_dset_m0  = ()
    set all_dset_m1  = ()
    set all_dset_m2  = ()
    set all_dset_m3  = ()
    foreach nn ( `seq 1 1 ${#all_dset}` )
        set nnn     = `printf "%03d" $nn`
        set ff      = "${all_dset[$nn]}"

        # base name of vol, and make a list of all prefixes for later
        set ibase   = `3dinfo -prefix_noext "${ff}"`
        set idir    = `dirname "${ff}"`
        set iid     = `printf "${idir}" | tail -c 4`

        # each is a useful input dset here
        set dset_res = "${odir}/dset_${iid}_${idir}__${ibase}.nii.gz"
        set dset_m0 = "${odir}/mask_00_${iid}_wbbool.nii.gz"
        set dset_m1 = "${odir}/mask_01_${iid}_posthr.nii.gz"
        set dset_m2 = "${odir}/mask_02_${iid}_negthr.nii.gz"
        set dset_m3 = "${odir}/mask_03_${iid}_allthr.nii.gz"

        # the accumulating lists
        set all_iid      = ( ${all_iid} ${iid} )
        set all_dset_res = ( ${all_dset_res} ${dset_res} )
        set all_dset_m0  = ( ${all_dset_m0}  ${dset_m0} )
        set all_dset_m1  = ( ${all_dset_m1}  ${dset_m1} )
        set all_dset_m2  = ( ${all_dset_m2}  ${dset_m2} )
        set all_dset_m3  = ( ${all_dset_m3}  ${dset_m3} )
    end

    # ======================================================================
    # create *.netcc file: for Dice coef, both WB and zoomed region
    
    set onetcc = ${odir}/matrix_dice_hyp${num}.netcc

    printf "" > ${onetcc}

    # header
    printf "# %d  # Number of network ROIs\n"   "${#all_dset}"  >> ${onetcc}
    printf "# %d  # Number of netcc matrices\n" "6"             >> ${onetcc}
    printf "# WITH_ROI_LABELS\n"                                >> ${onetcc}

    # 'ROI' (=dset) labels, numbers
    printf "   ${all_iid}\n"                 >> ${onetcc}
    echo   "   `seq 1 1 ${#all_dset}`"       >> ${onetcc}

    printf "# Dice_pos\n"
    printf "# Dice_pos\n"                    >> ${onetcc}
    3ddot -full -dodice ${all_dset_m1}       >> ${onetcc}

    printf "# Dice_pos, VMPFC and VST\n"
    printf "# Dice_pos, VMPFC and VST\n"     >> ${onetcc}
    3ddot -full -dodice -mask ${dset_grid_zoom} \
        ${all_dset_m1}                       >> ${onetcc}

    printf "# Dice_neg\n"
    printf "# Dice_neg\n"                    >> ${onetcc}
    3ddot -full -dodice ${all_dset_m2}       >> ${onetcc}

    printf "# Dice_neg\n"
    printf "# Dice_neg, VMPFC and VST\n"     >> ${onetcc}
    3ddot -full -dodice -mask ${dset_grid_zoom} \
        ${all_dset_m2}                       >> ${onetcc}

    printf "# Dice_all\n"
    printf "# Dice_all\n"                    >> ${onetcc}
    3ddot -full -dodice ${all_dset_m3}       >> ${onetcc}

    printf "# Dice_all\n"
    printf "# Dice_all, VMPFC and VST\n"     >> ${onetcc}
    3ddot -full -dodice -mask ${dset_grid_zoom} \
        ${all_dset_m3}                       >> ${onetcc}

    fat_mat2d_plot.py                         \
        -input   ${onetcc}                    \
        -ftype   svg                          \
        -cbar    Reds                         \
        -vmin    0                            \
        -vmax    1
    fat_mat2d_plot.py                         \
        -input   ${onetcc}                    \
        -ftype   tif                          \
        -cbar    Reds                         \
        -vmin    0                            \
        -vmax    1

    # ======================================================================
    # create *.netcc file: for Continuous, both WB and zoomed region
    
    set onetcc = ${odir}/matrix_cont_hyp${num}.netcc
    printf "" > ${onetcc}

    # header
    printf "# %d  # Number of network ROIs\n"   "${#all_dset}"  >> ${onetcc}
    printf "# %d  # Number of netcc matrices\n" "2"             >> ${onetcc}
    printf "# WITH_ROI_LABELS\n"                                >> ${onetcc}

    # 'ROI' (=dset) labels, numbers
    printf "   ${all_iid}\n"                 >> ${onetcc}
    echo   "   `seq 1 1 ${#all_dset}`"       >> ${onetcc}

    printf "# Corr_coef\n"
    printf "# Corr_coef\n"                   >> ${onetcc}
    3ddot -full -docor -mask ${dset_grid} \
        ${all_dset_res}                      >> ${onetcc}

    printf "# Corr_coef\n"
    printf "# Corr_coef, VMPFC and VST\n"    >> ${onetcc}
    3ddot -full -docor -mask ${dset_grid_zoom} \
        ${all_dset_res}                      >> ${onetcc}

    fat_mat2d_plot.py                         \
        -input   ${onetcc}                    \
        -ftype   svg                          \
        -cbar    seismic                      \
        -vmin    -1                           \
        -vmax     1
    fat_mat2d_plot.py                         \
        -input   ${onetcc}                    \
        -ftype   tif                          \
        -cbar    seismic                      \
        -vmin    -1                           \
        -vmax     1
end



echo "++ DONE"

exit 0
