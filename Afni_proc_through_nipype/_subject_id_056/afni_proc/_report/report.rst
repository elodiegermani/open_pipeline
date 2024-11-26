Node: afni_proc (utility)
=========================


 Hierarchy : Afni_proc_through_nipype.afni_proc
 Exec ID : afni_proc.a058


Original Inputs
---------------


* command : /home/jlefortb/narps_open_pipelines/narps_open/pipelines/team_6VV2.firstlevel
* data_dir : /home/jlefortb/narps_open_pipelines/data/original/ds001734/
* function_str : def run(command, results_dir, subject, data_dir):
    import subprocess
    subject= "sub-{}".format(subject)
    subprocess.run([command, results_dir, subject, data_dir])
    print("Done")

* results_dir : /home/jlefortb/narps_open_pipelines/data/results/derived/team_6VV2_afni/firstlevel/
* subject : 056

