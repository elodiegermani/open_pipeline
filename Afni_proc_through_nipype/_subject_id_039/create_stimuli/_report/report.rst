Node: create_stimuli (utility)
==============================


 Hierarchy : Afni_proc_through_nipype.create_stimuli
 Exec ID : create_stimuli.a066


Original Inputs
---------------


* data_dir : /home/jlefortb/narps_open_pipelines/data/original/ds001734/
* function_str : def create_stimuli_file(subject, data_dir):
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

* subject : 039


Execution Inputs
----------------


* data_dir : /home/jlefortb/narps_open_pipelines/data/original/ds001734/
* function_str : def create_stimuli_file(subject, data_dir):
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

* subject : 039


Execution Outputs
-----------------


* Stimuli : None


Runtime info
------------


* duration : 0.01236
* hostname : ptb-03230001.irisa.fr
* prev_wd : /home/jlefortb/narps_open_pipelines
* working_dir : /home/jlefortb/narps_open_pipelines/Afni_proc_through_nipype/_subject_id_039/create_stimuli


Environment
~~~~~~~~~~~


* COLORTERM : truecolor
* DBUS_SESSION_BUS_ADDRESS : unix:path=/run/user/670967/bus
* DEBUGINFOD_URLS : https://debuginfod.fedoraproject.org/ 
* DESKTOP_SESSION : gnome
* DISPLAY : :0
* EDITOR : /usr/bin/nano
* FSLDIR : /usr/local/fsl
* FSLGECUDAQ : cuda.q
* FSLMULTIFILEQUIT : TRUE
* FSLOUTPUTTYPE : NIFTI_GZ
* FSLTCLSH : /usr/local/fsl/bin/fsltclsh
* FSLWISH : /usr/local/fsl/bin/fslwish
* FSL_LOAD_NIFTI_EXTENSIONS : 0
* FSL_SKIP_GLOBAL : 0
* GDMSESSION : gnome
* GDM_LANG : en_US.UTF-8
* GNOME_SETUP_DISPLAY : :1
* GNOME_TERMINAL_SCREEN : /org/gnome/Terminal/screen/3627c221_9f8a_4ca7_a192_68617ea35d25
* GNOME_TERMINAL_SERVICE : :1.180
* GUESTFISH_INIT : \e[1;34m
* GUESTFISH_OUTPUT : \e[0m
* GUESTFISH_PS1 : \[\e[1;32m\]><fs>\[\e[0;31m\] 
* GUESTFISH_RESTORE : \e[0m
* HISTCONTROL : ignoredups
* HISTSIZE : 1000
* HOME : /home/jlefortb
* HOSTNAME : ptb-03230001.irisa.fr
* KDEDIRS : /usr
* LANG : en_US.UTF-8
* LESSOPEN : ||/usr/bin/lesspipe.sh %s
* LOGNAME : jlefortb
* LS_COLORS : rs=0:di=01;34:ln=01;36:mh=00:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:mi=01;37;41:su=37;41:sg=30;43:ca=00:tw=30;42:ow=34;42:st=37;44:ex=01;32:*.tar=01;31:*.tgz=01;31:*.arc=01;31:*.arj=01;31:*.taz=01;31:*.lha=01;31:*.lz4=01;31:*.lzh=01;31:*.lzma=01;31:*.tlz=01;31:*.txz=01;31:*.tzo=01;31:*.t7z=01;31:*.zip=01;31:*.z=01;31:*.dz=01;31:*.gz=01;31:*.lrz=01;31:*.lz=01;31:*.lzo=01;31:*.xz=01;31:*.zst=01;31:*.tzst=01;31:*.bz2=01;31:*.bz=01;31:*.tbz=01;31:*.tbz2=01;31:*.tz=01;31:*.deb=01;31:*.rpm=01;31:*.jar=01;31:*.war=01;31:*.ear=01;31:*.sar=01;31:*.rar=01;31:*.alz=01;31:*.ace=01;31:*.zoo=01;31:*.cpio=01;31:*.7z=01;31:*.rz=01;31:*.cab=01;31:*.wim=01;31:*.swm=01;31:*.dwm=01;31:*.esd=01;31:*.avif=01;35:*.jpg=01;35:*.jpeg=01;35:*.mjpg=01;35:*.mjpeg=01;35:*.gif=01;35:*.bmp=01;35:*.pbm=01;35:*.pgm=01;35:*.ppm=01;35:*.tga=01;35:*.xbm=01;35:*.xpm=01;35:*.tif=01;35:*.tiff=01;35:*.png=01;35:*.svg=01;35:*.svgz=01;35:*.mng=01;35:*.pcx=01;35:*.mov=01;35:*.mpg=01;35:*.mpeg=01;35:*.m2v=01;35:*.mkv=01;35:*.webm=01;35:*.webp=01;35:*.ogm=01;35:*.mp4=01;35:*.m4v=01;35:*.mp4v=01;35:*.vob=01;35:*.qt=01;35:*.nuv=01;35:*.wmv=01;35:*.asf=01;35:*.rm=01;35:*.rmvb=01;35:*.flc=01;35:*.avi=01;35:*.fli=01;35:*.flv=01;35:*.gl=01;35:*.dl=01;35:*.xcf=01;35:*.xwd=01;35:*.yuv=01;35:*.cgm=01;35:*.emf=01;35:*.ogv=01;35:*.ogx=01;35:*.aac=01;36:*.au=01;36:*.flac=01;36:*.m4a=01;36:*.mid=01;36:*.midi=01;36:*.mka=01;36:*.mp3=01;36:*.mpc=01;36:*.ogg=01;36:*.ra=01;36:*.wav=01;36:*.oga=01;36:*.opus=01;36:*.spx=01;36:*.xspf=01;36:*~=00;90:*#=00;90:*.bak=00;90:*.old=00;90:*.orig=00;90:*.part=00;90:*.rej=00;90:*.swp=00;90:*.tmp=00;90:*.dpkg-dist=00;90:*.dpkg-old=00;90:*.ucf-dist=00;90:*.ucf-new=00;90:*.ucf-old=00;90:*.rpmnew=00;90:*.rpmorig=00;90:*.rpmsave=00;90:
* MAIL : /var/spool/mail/jlefortb
* MOZ_GMP_PATH : /usr/lib64/mozilla/plugins/gmp-gmpopenh264/system-installed
* PATH : /home/jlefortb/reproduction/bin:/usr/local/fsl/share/fsl/bin:/usr/local/fsl/share/fsl/bin:/usr/local/fsl/share/fsl/bin:/usr/local/fsl/share/fsl/bin:/home/jlefortb/reproduction/bin:/usr/local/fsl/share/fsl/bin:/usr/local/fsl/share/fsl/bin:/home/jlefortb/.local/bin:/home/jlefortb/bin:/usr/lib64/qt-3.3/bin:/usr/lib64/ccache:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/home/jlefortb/abin:/home/jlefortb/abin
* PS1 : (reproduction) [\u@\h (Fedora 37) \W]$ 
* PWD : /home/jlefortb
* QTDIR : /usr/lib64/qt-3.3
* QTINC : /usr/lib64/qt-3.3/include
* QTLIB : /usr/lib64/qt-3.3/lib
* QT_IM_MODULE : ibus
* R_LIBS : /home/jlefortb/R
* SESSION_MANAGER : local/unix:@/tmp/.ICE-unix/12471,unix/unix:/tmp/.ICE-unix/12471
* SHELL : /bin/bash
* SHLVL : 1
* SSH_AUTH_SOCK : /run/user/670967/keyring/ssh
* SYSTEMD_EXEC_PID : 12526
* TERM : xterm-256color
* USER : jlefortb
* USERNAME : jlefortb
* VIRTUAL_ENV : /home/jlefortb/reproduction
* VIRTUAL_ENV_PROMPT : (reproduction) 
* VTE_VERSION : 7006
* WAYLAND_DISPLAY : wayland-0
* XAUTHORITY : /run/user/670967/.mutter-Xwaylandauth.LIAOF2
* XDG_CURRENT_DESKTOP : GNOME
* XDG_DATA_DIRS : /home/jlefortb/.local/share/flatpak/exports/share:/var/lib/flatpak/exports/share:/usr/local/share/:/usr/share/
* XDG_MENU_PREFIX : gnome-
* XDG_RUNTIME_DIR : /run/user/670967
* XDG_SESSION_CLASS : user
* XDG_SESSION_DESKTOP : gnome
* XDG_SESSION_TYPE : wayland
* XMODIFIERS : @im=ibus
* _ : /home/jlefortb/reproduction/bin/ipython

