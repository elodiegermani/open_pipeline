#!/bin/tcsh -e
set echo
# just change montage dims

set dset_ref   = extra_dsets/MNI152_2009_template_SSW.nii.gz
set dir_data   = group_analysis.ttest.1grp.equalRange.gain
set dir_data_C = group_analysis.CSIM.1grp.equalRange.gain
set lab_dat    = "equalRange.g_mean"  # SetA_mean
set lab_stat   = "equalRange.g_Tstat" # SetA_Zscr

set atl_ref    = MNI_Glasser_HCP_v1.0

# dset params
set nn         = 2
set sided      = bisided
set all_blur   = ( 4.0 )        # could be a list of many (e.g., from ETAC)

# stat thr choices
set pthr       = "0.001"
set alpha      = "0.05" 
set pthr_alt   = "0.01"
set clsize_alt = "5"            # clean up tiniest stuff

set func_ran_eff  = 0.005
set func_ran_stat = 5
set opacity    = 9 
set cbar       = Reds_and_Blues_Inv

set ulay_ran   = ( 0% 98% )
set coords     = ( 0  32 29 )
set slices     = ( 19 21 13 )
set subbb      = ( 0 0 1 )

set odir       = images_vox_TTEST
mkdir -p ${odir}

# =========================================================================

foreach blur ( ${all_blur} )
    echo ""
    echo "++ Proc blur: ${blur}"
    echo ""

    # string of parameters used to select existing, and to name new, files
    set fstr = "NN${nn}_${sided}"

    # get nifti dataset
    set dset_ttest = ( ${dir_data}/ttest_equalRange.gain.nii.gz )
    set thelist    = ( ${dset_ttest} )
    set nlist      = ${#thelist}
    if ( "${nlist}" != "1" ) then
        echo "** ERROR: found incorrect number of dsets: not 1, but ${nlist}:"
        echo "   ${thelist}"
        exit 1
    endif

    # get cluster info file
    set file_1D   = ( ${dir_data_C}/*${fstr}.1D )  # from csim dir
    set thelist   = ( ${file_1D} )
    set nlist     = ${#thelist}
    if ( "${nlist}" != "1" ) then
        echo "** ERROR: found incorrect number of dsets: not 1, but ${nlist}:"
        echo "   ${thelist}"
        exit 1
    endif

    # extract cluster size
    set clsize = `1d_tool.py                                                 \
                      -verb        0                                         \
                      -csim_pthr   ${pthr}                                   \
                      -csim_alpha  ${alpha}                                  \
                      -infile      ${file_1D}`

    # run this verbose version just to report in terminal
    1d_tool.py                                                               \
        -csim_pthr   ${pthr}                                                 \
        -csim_alpha  ${alpha}                                                \
        -infile      ${file_1D}

    # bog standard equivalent from many papers: opaque thr, only stat for 
    # both olay and thr
    set opref = ${odir}/img_02_only_thr_clust_opa_${fstr}
    @chauffeur_afni                                                       \
        -ulay              "${dset_ref}"                                  \
        -olay              ${dset_ttest}                                  \
        -cbar              ${cbar}                                        \
        -ulay_range        ${ulay_ran}                                    \
        -func_range        ${func_ran_stat}                               \
        -set_subbricks     0 "${lab_stat}"  "${lab_stat}"                 \
        -set_dicom_xyz     ${coords}                                      \
        -delta_slices      ${slices}                                      \
        -clusterize        "-NN ${nn} -clust_nvox ${clsize}"              \
        -clusterize_wami   "${atl_ref}"                                   \
        -thr_olay_p2stat   ${pthr}                                        \
        -thr_olay_pside    ${sided}                                       \
        -olay_alpha        No                                             \
        -olay_boxed        No                                             \
        -opacity           ${opacity}                                     \
        -prefix            ${opref}                                       \
        -set_xhairs        OFF                                            \
        -montx 6 -monty 1                                                 \
        -label_mode 1 -label_size 4

    # from:  https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/tutorials/auto_image/auto_%40chauffeur_afni.html#ex-6-overlay-beta-coefs-threshold-with-stats-and-clusterize
    set opref = ${odir}/img_03_beta_thr_clust_opa_${fstr}
    @chauffeur_afni                                                       \
        -ulay              "${dset_ref}"                                  \
        -olay              ${dset_ttest}                                  \
        -cbar              ${cbar}                                        \
        -ulay_range        ${ulay_ran}                                    \
        -func_range        ${func_ran_eff}                                \
        -set_subbricks     0 "${lab_dat}"  "${lab_stat}"                  \
        -set_dicom_xyz     ${coords}                                      \
        -delta_slices      ${slices}                                      \
        -clusterize        "-NN ${nn} -clust_nvox ${clsize}"              \
        -clusterize_wami   "${atl_ref}"                                   \
        -thr_olay_p2stat   ${pthr}                                        \
        -thr_olay_pside    ${sided}                                       \
        -olay_alpha        No                                             \
        -olay_boxed        No                                             \
        -opacity           ${opacity}                                     \
        -prefix            ${opref}                                       \
        -set_xhairs        OFF                                            \
        -montx 6 -monty 1                                                 \
        -label_mode 1 -label_size 4

    # from:  https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/tutorials/auto_image/auto_%40chauffeur_afni.html#ex-7-overlay-beta-coefs-threshold-clusterize-translucently
    set opref = ${odir}/img_04_beta_thr_clust_tr_${fstr}
    @chauffeur_afni                                                       \
        -ulay              "${dset_ref}"                                  \
        -olay              ${dset_ttest}                                  \
        -cbar              ${cbar}                                        \
        -ulay_range        ${ulay_ran}                                    \
        -func_range        ${func_ran_eff}                                \
        -set_subbricks     0 "${lab_dat}"  "${lab_stat}"                  \
        -set_dicom_xyz     ${coords}                                      \
        -delta_slices      ${slices}                                      \
        -clusterize        "-NN ${nn} -clust_nvox ${clsize}"              \
        -clusterize_wami   "${atl_ref}"                                   \
        -thr_olay_p2stat   ${pthr}                                        \
        -thr_olay_pside    ${sided}                                       \
        -olay_alpha        Yes                                            \
        -olay_boxed        Yes                                            \
        -opacity           ${opacity}                                     \
        -prefix            ${opref}                                       \
        -set_xhairs        OFF                                            \
        -montx 6 -monty 1                                                 \
        -label_mode 1 -label_size 4

    set opref = ${odir}/img_05_beta_thr_noclust_p01_tr_${fstr}
    @chauffeur_afni                                                       \
        -ulay              "${dset_ref}"                                  \
        -olay              ${dset_ttest}                                  \
        -cbar              ${cbar}                                        \
        -ulay_range        ${ulay_ran}                                    \
        -func_range        ${func_ran_eff}                                \
        -set_subbricks     0 "${lab_dat}"  "${lab_stat}"                  \
        -set_dicom_xyz     ${coords}                                      \
        -delta_slices      ${slices}                                      \
        -clusterize        "-NN ${nn} -clust_nvox ${clsize_alt}"          \
        -thr_olay_p2stat   ${pthr_alt}                                    \
        -thr_olay_pside    ${sided}                                       \
        -olay_alpha        Yes                                            \
        -olay_boxed        Yes                                            \
        -opacity           ${opacity}                                     \
        -prefix            ${opref}                                       \
        -set_xhairs        OFF                                            \
        -montx 6 -monty 1                                                 \
        -label_mode 1 -label_size 4

end

echo "++ DONE"

exit 0
