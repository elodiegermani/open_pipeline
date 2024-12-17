# apaper_highlight_narps
Scripts related to the following paper:

  **Highlight Results, Don't Hide Them: Enhance interpretation, reduce
  biases and improve reproducibility** \
  by Paul A Taylor, Richard C Reynolds, Vince Calhoun, Javier
  Gonzalez-Castillo, Daniel A Handwerker, Peter A Bandettini, Amanda F
  Mejia, Gang Chen (2023) \
  Neuroimage 274:120138. doi: 10.1016/j.neuroimage.2023.120138 \
  https://pubmed.ncbi.nlm.nih.gov/37116766/

---------------------------------------------------------------------------
The input data comes from the NARPS project (Botvinik-Nezer et al., 2020): \
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7771346/ \
This paper uses both the raw, unprocessed data as well as the
participating teams' results, which were uploaded to NeuroVault (see
the same paper for those details).

---------------------------------------------------------------------------
Essentially all scripts here use AFNI; one also uses FreeSurfer.

The `scripts_biowulf` directory contains the main processing scripts,
including:
+ Checking the data
+ Estimating nonlinear alignment to template space and skullstripping
  with `@SSwarper`
+ Full FMRI time series processing through regression modeling and QC
  generation with `afni_proc.py`
+ Group level modeling: both voxelwise (with cluster calcs) and
  ROI-based (using `RBA`, in particular) 

... and more.

The `scripts_suppl_proc_vox` directory contains supplementary scripts
for making images of the above-processed data, mainly for figure
generation.

The `scripts_suppl_proc_teams` directory contains scripts for
processing the group-level results of the original participating Teams
in the NARPS project.  Those public datasets were downloaded from
NeuroVault.  The scripts make a lot of images and perform some simple
similarity analyses.
