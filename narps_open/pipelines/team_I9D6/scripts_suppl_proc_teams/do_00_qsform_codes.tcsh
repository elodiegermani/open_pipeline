#!/bin/tcsh

# correct qform_code and sform_code for these dsets to be 4 (=MNI)

# to use, copy it into the directory holding data

echo "++ gunzip all dsets"
gunzip *.nii.gz

set all_nii = ( *nii )

foreach nii ( ${all_nii} )
    echo "++ Fixing [qs]form_code for dset: ${nii}"
    nifti_tool                                 \
        -mod_hdr -mod_field qform_code 4       \
                 -mod_field sform_code 4       \
        -infiles ${nii}                        \
        -overwrite         
end


echo "++ gzip all dsets"
gzip *nii
