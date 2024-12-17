#!/bin/tcsh

# this is a semi-slow process, so divide up into three batches

set here  = $PWD                        # for path; trivial, could be changed
set ref   = ~/REF_TEMPLATES/MNI152_T1_2009c+tlrc.HEAD

# loop over all hypotheses
foreach num ( `seq 1 1 3` ) 
    set hyp   = "hypo${num}"
    set ilist = `cat list_match_${num}_sort.txt | awk '{print $2}'` 
                        # better than `\ls */*hyp*${num}_unthresh*nii*`

    set lcol  = ( 255 255 255 )             # RGB line color bt image panels
    set odir  = ${here}/QC_${hyp}           # output dir for images

    \mkdir ${odir}

    # =========================================================================

    set allbase = ()
    set allid   = ()
    set allfile = ()

    if ( 1 ) then
    foreach nn ( `seq 1 1 ${#ilist}` )
        set nnn     = `printf "%03d" $nn`
        set ff      = "${ilist[$nn]}"
        # base name of vol, and make a list of all prefixes for later
        set ibase   = `3dinfo -prefix_noext "${ff}"`
        set idir    = `dirname "${ff}"`
        set iid     = `printf "${idir}" | tail -c 4`

        set allbase = ( ${allbase} ${ibase} )
        set allid   = ( ${allid}   ${iid} )
        set allfile = ( ${allfile} ${ff} )

        echo "++ iid = '${iid}'; ibase = '${ibase}'; idir = '${idir}'"

        if ( 1 ) then
        ### Make a montage of the zeroth brick of each image.
        # Some fun-ness here: part of each file's name is added to the
        # label string shown in each panel.
        # Note: these olay datasets are unclustered and unmasked.
        @chauffeur_afni                                                    \
            -ulay        ${ref}                                            \
            -ulay_range  "2%" "110%"                                       \
            -olay        ${ff}                                             \
            -set_subbricks -1 0 0                                          \
            -func_range  5                                                 \
            -thr_olay    3                                                 \
            -cbar        Reds_and_Blues_Inv                                \
            -olay_alpha  Linear                                            \
            -olay_boxed  Yes                                               \
            -opacity     7                                                 \
            -prefix      ${odir}/img_${nnn}_alpha_${iid}                   \
            -montx 1 -monty 1                                              \
            -set_dicom_xyz  5 18 18                                        \
            -set_xhairs     OFF                                            \
            -label_string "::${iid}"                                       \
            -label_mode 1 -label_size 3                                    \
            -do_clean

        @chauffeur_afni                                                    \
            -ulay        ${ref}                                            \
            -ulay_range  "2%" "110%"                                       \
            -olay        ${ff}                                             \
            -set_subbricks -1 0 0                                          \
            -func_range  5                                                 \
            -thr_olay    3                                                 \
            -cbar        Reds_and_Blues_Inv                                \
            -olay_alpha  No                                                \
            -olay_boxed  No                                                \
            -opacity     7                                                 \
            -prefix      ${odir}/img_${nnn}_psi_${iid}                     \
            -montx 1 -monty 1                                              \
            -set_dicom_xyz  5 18 18                                        \
            -set_xhairs     OFF                                            \
            -label_string "::${iid}"                                       \
            -label_mode 1 -label_size 3                                    \
            -do_clean
        endif
    end
    endif

    # =========================================================================

    # get a good number of rows/cols for this input

    set nallbase = ${#allbase}
    adjunct_calc_mont_dims.py ${nallbase} __tmp_${hyp}
    set dims = `tail -n 1 __tmp_${hyp}`

    # =========================================================================

    # output subj list

    set file_subj = "${odir}/list_of_all_subj.txt"
    printf "" > ${file_subj}
    foreach ii ( `seq 1 1 ${nallbase}` )
        printf "%4s  %30s\n" ${allid[$ii]} ${allfile[$ii]} >> ${file_subj}
    end

    # ========================================================================

    foreach ss ( "sag" "cor" "axi" )
        # Combine alpha-thresholded images
        2dcat                                                             \
            -echo_edu                                                     \
            -gap 5                                                        \
            -gap_col ${lcol}                                              \
            -ny ${dims[4]}                                                \
            -nx ${dims[3]}                                                \
            -zero_wrap                                                    \
            -prefix ${odir}/ALL_alpha_${hyp}_sview_${ss}.jpg              \
            ${odir}/img_*_alpha*${ss}*

        # Combine non-alpha-thresholded images
        2dcat                                                             \
            -echo_edu                                                     \
            -gap 5                                                        \
            -gap_col ${lcol}                                              \
            -ny ${dims[4]}                                                \
            -nx ${dims[3]}                                                \
            -zero_wrap                                                    \
            -prefix ${odir}/ALL_psi_${hyp}_sview_${ss}.jpg                \
            ${odir}/img_*_psi*${ss}*

    end

end


