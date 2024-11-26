'''
created by team 6VV2, reproduced by Narps reproducibility team
creation date: 22 June 2023
needs script "team_6VV2.firstlevel" and "team_6VV2.secondlevel"
the team : AFNI Version 19.0.01 Tiberius
version afni used by the reproducibility team :AFNI Version 23.0.02 Commodus
Participants not included 016, 018, 030, 088, 089, 100
Last update: June 2023
'''

from nipype import Node, Function, Workflow,IdentityInterface
import subprocess
from nipype.interfaces.io import SelectFiles, DataSink
from os.path import abspath
from os.path import join as opj
import os
import pathlib
from glob import glob
from nilearn import plotting
import matplotlib.pyplot as plt
from nilearn import image
import pandas as pd

########################################################################
################## FIRST LEVEL ANALYSIS FOR TEAM 6VV2 ##################
########################################################################

# define environment for first level analysis
data_dir = "/home/jlefortb/narps_open_pipelines/data/original/ds001734/"
results_dir =  "/home/jlefortb/narps_open_pipelines/data/results/derived/team_6VV2_afni/firstlevel/"

path = pathlib.Path(results_dir)
path.mkdir(parents=True, exist_ok=True)



# define subject ids
dir_list = os.listdir(data_dir)
# Subject list (to which we will do the analysis)
subject_list = []
for dirs in dir_list:
    if dirs[0:3] == 'sub':
        subject_list.append(dirs[-3:])




# Infosource Node - To iterate on subjects + get directoris paths
infosource = Node(interface=IdentityInterface(fields = ['subject_id', 'data_dir', 'results_dir'],
                    data_dir = data_dir,
                    results_dir = results_dir),
                  name = 'infosource')

infosource.iterables = [('subject_id', subject_list)]


templates = {'command': abspath('narps_open/pipelines/team_6VV2.firstlevel')}
# Create SelectFiles node
files = Node(SelectFiles(templates),
          name='files')
# Location of the dataset folder
files.inputs.base_directory = '.'

# create stimuli file the afni way
def create_stimuli_file(subject, data_dir):
    # create 1D stimuli file :
    import pandas as pd 
    from os.path import join as opj
    df_run1 = pd.read_csv(opj(data_dir, "sub-{}/func/sub-{}_task-MGT_run-01_events.tsv".format(subject, subject)), sep="\t")
    df_run1 = df_run1[["onset", "gain", "loss"]].T
    df_run2 = pd.read_csv(opj(data_dir, "sub-{}/func/sub-{}_task-MGT_run-02_events.tsv".format(subject, subject)), sep="\t")
    df_run2 = df_run2[["onset", "gain", "loss"]].T
    df_run3 = pd.read_csv(opj(data_dir, "sub-{}/func/sub-{}_task-MGT_run-03_events.tsv".format(subject, subject)), sep="\t")
    df_run3 = df_run3[["onset", "gain", "loss"]].T
    df_run4 = pd.read_csv(opj(data_dir, "sub-{}/func/sub-{}_task-MGT_run-04_events.tsv".format(subject, subject)), sep="\t")
    df_run4 = df_run4[["onset", "gain", "loss"]].T

    df_gain = pd.DataFrame(index=range(0,4), columns=range(0,64))
    df_gain.loc[0] = ["{}*{}".format(df_run1[col].loc['onset'], df_run1[col].loc['gain']) for col in range(0, 64)]
    df_gain.loc[1] = ["{}*{}".format(df_run2[col].loc['onset'], df_run2[col].loc['gain']) for col in range(0, 64)]
    df_gain.loc[2] = ["{}*{}".format(df_run3[col].loc['onset'], df_run3[col].loc['gain']) for col in range(0, 64)]
    df_gain.loc[3] = ["{}*{}".format(df_run4[col].loc['onset'], df_run4[col].loc['gain']) for col in range(0, 64)]
    df_loss = pd.DataFrame(index=range(0,4), columns=range(0,64))
    df_loss.loc[0] = ["{}*{}".format(df_run1[col].loc['onset'], df_run1[col].loc['loss']) for col in range(0, 64)]
    df_loss.loc[1] = ["{}*{}".format(df_run2[col].loc['onset'], df_run2[col].loc['loss']) for col in range(0, 64)]
    df_loss.loc[2] = ["{}*{}".format(df_run3[col].loc['onset'], df_run3[col].loc['loss']) for col in range(0, 64)]
    df_loss.loc[3] = ["{}*{}".format(df_run4[col].loc['onset'], df_run4[col].loc['loss']) for col in range(0, 64)]

    df_gain.to_csv(opj(data_dir, "sub-{}/func/times+gain.1D".format(subject)), 
            sep='\t', index=False, header=False)
    df_loss.to_csv(opj(data_dir, "sub-{}/func/times+loss.1D".format(subject)), 
            sep='\t', index=False, header=False)
    print("Done")

create_stimuli = Node(Function(input_names=["subject", "data_dir"],
                                    output_names=["Stimuli"],
                                    function=create_stimuli_file),
              name='create_stimuli')


# launch afni bash script
def run(command, results_dir, subject, data_dir):
    import subprocess
    subject= "sub-{}".format(subject)
    subprocess.run([command, results_dir, subject, data_dir])
    print("Done")

afni_proc = Node(Function(input_names=["command", "results_dir", "subject", "data_dir"],
                                    output_names=["Adni_1stLevel"],
                                    function=run),
              name='afni_proc')


####### build workflow
wf_run = Workflow(base_dir = results_dir, name="Afni_proc_through_nipype")
wf_run.base_dir = '.'
wf_run.connect([(infosource, create_stimuli, [('subject_id', 'subject')]),
                (infosource, create_stimuli, [("data_dir", "data_dir")]),
                (infosource, afni_proc, [('subject_id', 'subject')]),
                (infosource, afni_proc, [("results_dir", "results_dir")]),
                (infosource, afni_proc, [("data_dir", "data_dir")]),
                (files, afni_proc, [("command", "command")])
                ])
# wf_run.write_graph()
wf_run.run()

####
# to do: relaunch sub 1 and launch sub 2, then launch part 2 to check which data are mandatory and which we can delete
# because taking a bunch of space (60G)
####

# convert BRIK to nii
command = "3dAFNItoNIFTI"
for Afni_file in glob("/home/jlefortb/narps_open_pipelines/data/results/team_6VV2_afni/firstlevel/sub-001.results.block/*.HEAD"):
    file_name = Afni_file.split('/')[-1]
    nifti_file_name = file_name[:-5]
    results_dir = "/home/jlefortb/narps_open_pipelines/data/results/team_6VV2_afni/firstlevel/sub-001.results.block/results_as_nifti/"
    prefixname = opj(results_dir, nifti_file_name)
    subprocess.run([command, "-prefix", prefixname, Afni_file])

# visualise nifti
for nifi_file in glob("/home/jlefortb/narps_open_pipelines/data/results/team_6VV2_afni/firstlevel/sub-001.results.block/results_as_nifti/*"):
    shape = image.load_img(nifi_file).shape
    print("shape: ", shape)
    if len(shape) > 3:
        plotting.plot_stat_map(image.index_img(nifi_file, 0), annotate=False, title=nifi_file.split('/')[-1] + " ind 0", colorbar=True, cut_coords=(-24, -10, 4, 18, 32, 52, 64), display_mode='z', cmap='coolwarm')
        plotting.plot_stat_map(image.index_img(nifi_file, 30), annotate=False, title=nifi_file.split('/')[-1] + " ind 30", colorbar=True, cut_coords=(-24, -10, 4, 18, 32, 52, 64), display_mode='z', cmap='coolwarm')
        plotting.plot_stat_map(image.index_img(nifi_file, 60), annotate=False, title=nifi_file.split('/')[-1] + " ind 60", colorbar=True, cut_coords=(-24, -10, 4, 18, 32, 52, 64), display_mode='z', cmap='coolwarm')
        plt.show()
    else:
        plotting.plot_stat_map(nifi_file, annotate=False, title=nifi_file.split('/')[-1], colorbar=True, cut_coords=(-24, -10, 4, 18, 32, 52, 64), display_mode='z', cmap='coolwarm')
        plt.show()
        

########################################################################
################## SECOND LEVEL ANALYSIS FOR TEAM 6VV2 #################
########################################################################

# define environment for second level analysis
data_dir_firstlevel = "/home/jlefortb/narps_open_pipelines/data/results/team_6VV2_afni/firstlevel/"
results_dir_second_level =  "/home/jlefortb/narps_open_pipelines/data/results/team_6VV2_afni/secondlevel/"
path = pathlib.Path(results_dir_second_level)
path.mkdir(parents=True, exist_ok=True)

# Infosource Node - To iterate on subjects + get directoris paths
infosource = Node(interface=IdentityInterface(fields = ['results_dir_second_level'],
                    results_dir_second_level = results_dir_second_level),
                  name = 'infosource')

templates = {'command': abspath('narps_open/pipelines/team_6VV2.secondlevel')}
# Create SelectFiles node
files = Node(SelectFiles(templates),
          name='files')
# Location of the dataset folder
files.inputs.base_directory = '.'


# create datatable for afni_proc.py script
def create_dataTable(data_dir_firstlevel):
    # subject not analyzed by the team, see pipelines information for more details
    not_included = ["016","018","030","088","089","100"]
    df_participant = pd.read_csv("data/original/ds001734/participants.tsv", sep="\t")
    # replace equalRange and equalIndifference with range and indifference
    df_participant["group"] = [i[5:].lower() for i in df_participant["group"].values]
    df_participant["participant_id"] = [i[-3:] for i in df_participant["participant_id"].values]
    df = pd.DataFrame(columns=["Subj", "cond", "group", "InputFile"])
    for sub in df_participant["participant_id"].values:
        if sub in not_included:
            continue
        size_df = len(df)
        sub_group = df_participant["group"][df_participant["participant_id"]==sub].values[0]
        df.loc[size_df] = [sub, "GAIN", sub_group, "{}sub-{}/sub-{}_GAIN.nii".format(data_dir_firstlevel, sub, sub)]
        size_df = len(df)
        df.loc[size_df] = [sub, "LOSS", sub_group, "{}sub-{}/sub-{}_LOSS.nii".format(data_dir_firstlevel, sub, sub)]
    dataTable = df

    """
    Should look like 

    Subj cond group InputFile \
    001 GAIN indiff results/sub-001.results.block/sub-001_GAIN.nii \
    001 LOSS indiff results/sub-001.results.block/sub-001_LOSS.nii \
    …
    124 GAIN range results/sub-124.results.block/sub-124_GAIN.nii \
    124 LOSS range results/sub-124.results.block/sub-124_LOSS.nii 


    """
    return dataTable


# launch afni bash script
def run_secondlevel(command, results_dir_second_level):
    import subprocess
    subprocess.run([command, results_dir_second_level])
    print("Done")

afni_proc = Node(Function(input_names=["command", "results_dir_second_level"],
                                    output_names=["Adni_2ndLevel"],
                                    function=run_secondlevel),
              name='afni_proc')


####### build workflow
wf_run = Workflow(base_dir = results_dir_second_level, name="Afni_proc_2nd_level_through_nipype")
wf_run.base_dir = '.'
wf_run.connect([(infosource, afni_proc, [("results_dir_second_level", "results_dir_second_level")]),
                (files, afni_proc, [("command", "command")])
                ])
# wf_run.write_graph()
wf_run.run()