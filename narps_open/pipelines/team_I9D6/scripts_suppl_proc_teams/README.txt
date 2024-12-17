Some supplementary scripts for combining NARPS Teams' results and
generating images.  

This assumes all the NARPS Teams' results have been downloaded and
unpacked and cleaned up *a lot* for names/formatting: dirs to have
names like NARPS-????; to have all MNI-standard space NIFTI's have
[qs]form_code = 4; to remove not contain non-ASCII characters from
file/dir names; to have straightforward/unambiguous/nonoverlapping
names of files.

Most scripts loop over each Hypothesis.

---------------------------------------------------------------------------

+ do_00_qsform_codes.tcsh

  A preliminary code used to fix [sq]form_code values, as necessary;
  this one was copied into a Team's directory of data to use.

+ do_01a_proc_sign_flip.tcsh

  Apply rules for which datasets needed to have signs flipped,
  according to their submitted information about what a "positive"
  stat value meant.

+ do_01b_resam_same_grid.tcsh

  Resample datasets to a 2x2x2 mm**3 grid, for visualization and
  correlation purposes.

+ do_02_pc_with_sign0.tcsh

  Do PCA across teams results, with the first PC used to order
  datasets for a given hypothesis, for visualization purposes.

+ do_03_sort_by_sim2pc.tcsh

  Apply ordering based on similarity to first PC.

+ do_04_make_imgs_?.tcsh

  Make the montage of images of a hypothesis across all Teams (for
  both transparent and opaque thresholding).

+ do_10_within_brain_masks.tcsh

  Make masks of varying varieties: where data is nonzero; where data
  is >thr; where data is <-thr; where data is > |thr|.  To be used in
  next step (Dice calcs, in particular).

+ do_11_dice_pearson_coeffs.tcsh

  Do Dice and Pearson calcs, and generate similarity matrices (both
  for whole-brain and zoomed-in results).
