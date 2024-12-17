Some supplementary scripts for generating images, using voxelwise
processing results (and supplementary ROI maps and template).

Mainly provides some examples of running @chauffeur_afni.

---------------------------------------------------------------------------

+ do_22_view_wb_TTEST.tcsh
  
  Used to make the panels in Fig. 2.

+ do_13_view_zoom.tcsh

  Used to setup suma+afni to make panels A and B in Fig. 3 (requires a
  bit of button-pushing to set line colors, as described in comments).

+ do_06_clust_olap.tcsh

  Used to make a cluster table report of ROI overlaps, such as in
  Table 2 of the "Highlight, Don't Hide" paper. This script has been
  updated with a note about using FreeSurfer parcellations for ROI
  overlap reference, too.
