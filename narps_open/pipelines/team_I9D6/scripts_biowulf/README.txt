This directory contains the main processing scripts for analyzing the
raw NARPS data (task FMRI on two groups of 54 subj each).  These
scripts include preliminary checks, full single subject processing
through regression modeling, and a couple different forms of group
level modeling.

These scripts were run on the NIH's Biowulf computing cluster, hence
there are considerations for batch processing with the slurm system.
Each processing step is divided into a pair of associated scripts:

+ **do_SOMETHING.tcsh**: a script that mostly contains the processing
  options and commands for a single subject, with subject ID and any
  other relevant information passed in as a command line argument when
  using it.  Most of the lines at the top of the file set up the
  processing, directory structure (most every step generates a new
  filetree called `data_SOMETHING/`), and usage of a scratch disk for
  intermediate outputs.  At some point, actual processing commands are
  run, and then there is a bit of checking, copying from the scratch
  disk and verifying permissions, and then exiting.

+ **run_SOMETHING.tcsh**: mostly manage the group-level aspects of
  things, to set up processing over all subjects of interest and start
  a swarm job running on the cluster.

---------------------------------------------------------------------------
The enumeration in script names is to help to organize the order of
processing (kind of a Dewey Decimal-esque system).  Gaps between
numbers are fine---they just leave space for other processing steps to
have been inserted, as might be necessary.  Loosely, each "decade" of
enumeration corresponds to a different stage of processing:

+ the 00s are preliminary checks
+ the 10s are preliminary processing steps (parcellation,
  skullstripping and nonlinear alignment for the anatomical)
+ the 20s are afni_proc.py processing of the FMRI data
+ the 50s are running some automatic quality control (QC) with
  gen_ss_review_table.py
+ the 60s run voxelwise processing with ETAC (used in previous work,
  not here, but included for fun) and 3dttest++
+ the 70s contain region-based processing, setting up for and
  eventually running RBA.

---------------------------------------------------------------------------

The script details (recall: just listing the do_* scripts, since the
run_* ones just correspond to a swarming that step):

+ do_01_gtkyd.tcsh
  "Getting To Know Your Data" step, getting preliminary info about
  voxel size, number of time points, and other fun properties;
  consistency checks

+ do_02_deob.tcsh
  Deoblique the anatomical volumes (so FS output matches with later
  outputs)

+ do_12_fs.tcsh
  Run FreeSurfer for anatomical parcellations

+ do_13_ssw.tcsh
  Run AFNI's @SSwarper (SSW) for skullstripping (ss) and nonlinear
  alignment (warping) to MNI template space

+ do_15_events.tcsh
  Stimulus timing file creation

+ do_22_ap_task.tcsh
  Run AFNI's afni_proc.py (AP) for full processing of the FMRI data,
  through single subject regression modeling (here, without blurring,
  to be used for ROI-based analyses); uses results of earlier stages;
  also produces QC HTML

+ do_23_ap_task_b.tcsh
  Run AFNI's afni_proc.py (AP) for full processing of the FMRI data,
  through single subject regression modeling (here, with blurring, to
  be used for voxelwise analyses); uses results of earlier stages;
  also produces QC HTML

+ do_52_ap_qc.tcsh 
  Run some automatic QC criteria selections on the "22_ap_task" output
  with AFNI's gen_ss_review_table.py

+ do_53_ap_qc.tcsh
  Run some automatic QC criteria selections on the "23_ap_task_b"
  output with AFNI's gen_ss_review_table.py

+ do_61_etac_1grp.tcsh
  Run ETAC for group level analysis on the "22_ap_task" output (not
  used here; from a previous study, but script included); this applies
  to the single-group hypotheses

+ do_62_etac_2grp.tcsh
  Run ETAC for group level analysis on the "22_ap_task" output (not
  used here; from a previous study, but script included); this applies
  to the group contrast hypothesis

+ do_63_ttest_1grp.tcsh
  Run 3dttest++ for group level analysis on the "23_ap_task_b" output,
  for simple voxelwise analysis; this applies to the single-group
  hypotheses

+ do_64_csim_1grp.tcsh
  Run "3dttest++ -Clustsim ..." for getting standard cluster threshold
  size for the t-test results

+ do_71a_rba_prep.tcsh
  Prepare to run AFNI's RBA on the "22_ap_task" output, dumping
  average effect estimate information for each ROI (for both of the
  atlases used)

+ do_71b_rba_comb.tcsh
  Prepare to run AFNI's RBA on the "22_ap_task" output, combining ROI
  information across the group into a datatable (for both of the
  atlases used)

+ do_71c_rba.tcsh 
  Run AFNI's RBA on the "22_ap_task" output, using the created
  datatable (for both of the atlases used)
