#!/bin/tcsh -e

# focus on the ROIs for this hypothesis, only

# -------------------------------------------------------------------------
# driving stuff, AFNI and SUMA environments

setenv AFNI_ENVIRON_WARNINGS          NO
setenv SUMA_DriveSumaMaxCloseWait     6
setenv SUMA_DriveSumaMaxWait          6
setenv AFNI_SUMA_LINECOLOR_001        black #limegreen #black
setenv AFNI_SUMA_LINECOLOR_002        black #limegreen #black
setenv AFNI_SUMA_LINESIZE             2
setenv AFNI_SUMA_BOXSIZE              3
setenv AFNI_IMAGE_LABEL_MODE          1
setenv AFNI_IMAGE_LABEL_SIZE          4
setenv AFNI_IMAGE_LABEL_COLOR         yellow
setenv AFNI_IMAGE_LABEL_SETBACK       0.01
setenv AFNI_DEFAULT_IMSAVE            png

set dset_ref   = extra_dsets/MNI152_2009_template_SSW_ROIZOOMmed.nii.gz
set ivol       = ( extra_dsets/narps_mni_amyg_vmpfc_vstriatum_FS_res*.nii.gz )
set dir_data   = group_analysis.CSIM.1grp.equalRange.gain
set lab_dat    = "equalRange.g_mean" # # SetA_mean
set lab_stat   = "equalRange.g_Zscr" # SetA_Zscr

set pref_surf  = "SURF"

# dset params
set nn         = 2
set sided      = bisided
set all_blur   = ( 4.0 )        # could be a list of many (e.g., from ETAC)

# stat thr choices
set pthr       = "0.001"
set alpha      = "0.05" 

set portnum    = `afni -available_npb_quiet`
set OW         = "OPEN_WINDOW"
set opac       = 9                     # opacity
set mx         = 5                     # montage dims
set my         = 1
set ftype      = PNG
set bufac      = "4"                   # blowup factor
set frange     = 0.005                 # olay range
set cbar       = "Reds_and_Blues_Inv"  # cbar
set gapord     = ( 10 7 6 )            # delta slices
set mgap       = 2
set mcolor     = black 
set coor_type  = "SET_DICOM_XYZ"
set coors      = ( 1  -29  -15  )
set ifrac      = 1 #0.8
set olay_alpha = Yes
set olay_boxed = Yes
set subbb      = ( 0  0 1 )

set odir       = images_vox_CSIM
mkdir -p ${odir}

# =========================================================================
# make ROI surfs

if ( 1 ) then 
IsoSurface                     \
    -overwrite                 \
    -isorois+dsets             \
    -input    ${ivol}          \
    -o_gii    cc_${pref_surf}  \
    -Tsmooth  0 0              \
    -remesh   1
endif

# =========================================================================

foreach blur ( ${all_blur} )
    echo ""
    echo "++ Proc blur: ${blur}"
    echo ""

    # string of parameters used to select existing, and to name new, files
    set fstr = "NN${nn}_${sided}"

    # get nifti dataset
    set dset_ttest = ( ${dir_data}/ttest++_result+tlrc.HEAD )
    set thelist    = ( ${dset_ttest} )
    set nlist      = ${#thelist}
    if ( "${nlist}" != "1" ) then
        echo "** ERROR: found incorrect number of dsets: not 1, but ${nlist}:"
        echo "   ${thelist}"
        exit 1
    endif

    # get cluster info file
    set file_1D   = ( ${dir_data}/*${fstr}.1D )
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

    set thr = `p2dsetstat                             \
                    -quiet                            \
                    -${sided}                         \
                    -inset ${dset_ttest}"[${lab_stat}]" \
                    -pval "${pthr}"`


    afni -npb $portnum -niml -yesplugouts                  \
        ${dset_ref} ${dset_ttest} &
    plugout_drive -echo_edu                                                \
        -npb $portnum                                                      \
        -com "SWITCH_UNDERLAY ${dset_ref:t}"                                 \
        -com "SWITCH_OVERLAY  ${dset_ttest:t}"                               \
        -com "SET_XHAIRS  OFF"                                             \
        -com "SET_SUBBRICKS      ${subbb}"                                 \
        -com "SET_PBAR_ALL -99 1.0 ${cbar}"                                \
        -com "SET_FUNC_ALPHA  ${olay_alpha}"                               \
        -com "SET_FUNC_BOXED  ${olay_boxed}"                               \
        -com "$coor_type $coors"                                           \
        -com "SET_THRESHNEW ${thr}"                                        \
        -com "SET_FUNC_VISIBLE +"                                          \
        -com "SET_FUNC_RANGE  $frange"                                     \
        -com "$OW sagittalimage ifrac=${ifrac} opacity=${opac}             \
                    mont=${mx}x${my}:${gapord[1]}:${mgap}:${mcolor}"       \
        -com "$OW coronalimage  ifrac=${ifrac} opacity=${opac}             \
                    mont=${mx}x${my}:${gapord[2]}:${mgap}:${mcolor}"       \
        -com "$OW axialimage    ifrac=${ifrac} opacity=${opac}             \
                    mont=${mx}x${my}:${gapord[3]}:${mgap}:${mcolor}" &


    suma -echo_edu              \
        -npb $portnum           \
        -onestate -niml         \
        -i        cc*.k*.gii    \
        -vol ${dset_ref}        \
        -sv  ${dset_ref} &

    echo "\n\nNAP 1/4...\n\n"
    sleep 3

    DriveSuma                                              \
        -npb $portnum                                      \
        -com viewer_cont -key "t" -key "."  &



cat <<EOF

----------------------------------------------
TO ADD VIA THE GUI:

+ Colorize the surface lines :  rbgyr20_03 and limegreen
+ Set the LineWidth          :  6
+ And clustersize            :  ${clsize}

... and then snapshot (for best results)
----------------------------------------------
EOF

end


exit
