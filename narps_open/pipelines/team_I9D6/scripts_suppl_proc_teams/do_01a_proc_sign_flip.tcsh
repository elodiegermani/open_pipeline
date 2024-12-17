#!/bin/tcsh

# the subsets of hyps where signflips were

# each dset that is flipped is for single hypothesis here

# comment out if it needs to be run again:
echo "** should not be run multiple times **"
exit 0



set all_num = ( 5 6 9 )


foreach num ( ${all_num} )
    echo "------------------- hyp = ${num} ---------------------------------"
    
    # flip signs for teams that have a "-1" in these text files
    # (excluding teams that were excluded from unthresholded maps)
    set all_teamid = `cat sign_info_hyp${num}.txt | \
                        grep --color=never "\-1" | \
                        grep --color=never -v "X1Z4" | \
                        grep --color=never -v "1K0E" | \
                        grep --color=never -v "16IN" | \
                        awk '{print $1}'`

    foreach teamid ( ${all_teamid} )
        echo "++ ${teamid}"
        set dir_team = `find ./ -maxdepth 1 -type d -name "NARP*${teamid}" \
                            | cut -b3-`
        set orig_dset = `\ls ${dir_team}/*hyp*${num}*unthr*.nii*`
        echo ${orig_dset}

        set dir_flip = ${dir_team}/store_unflip_HYP-${num}
        echo ${dir_flip}
        \mkdir -p ${dir_flip}
        \mv ${orig_dset} ${dir_flip}/.
        set unflip_dset = `\ls ${dir_flip}/*hyp*${num}*unthr*.nii*`
        
        3dcalc \
            -a ${unflip_dset} \
            -expr '-1*a' \
            -prefix ${orig_dset}
    end

end
