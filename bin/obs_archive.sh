#! /bin/bash

endpoint='146.118.69.100' #HOST is already used as a keyword in other script
user='ubuntu'
remote='/mnt/dav/GLEAM-X/Archived_Obsids'

usage()
{
echo "obs_archive.sh [-d dep] [-p project] [-a account] [-u user] [-e endpoint] [-r remote_directory] [-t] obsnum

Archives the processed data products onto the data central archive system. By default traffic is routed through a nimbus instance, requiring a public ssh key to first be added to list of authorized keys. Data Central runs ownCloud, and at the moment easiest way through is a davfs2 mount. Consult Natasha or Tim. 

  -d dep      : job number for dependency (afterok)
  -a account  : computing account, default pawsey0272
  -p project  : project, (must be specified, no default)
  -u user     : user name of system to archive to (default: '$user')
  -e endpoint : hostname to copy the archive data to (default: '$endpoint')
  -r remote   : remote directory to copy files to (default: '$remote')
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  obsnum      : the obsid to process, or a text file of obsids (newline separated). 
               A job-array task will be submitted to process the collection of obsids. " 1>&2;
exit 1;
}

pipeuser=$(whoami)

# Supercomputer options
if [[ "${HOST:0:4}" == "zeus" ]]
then
    computer="zeus"
    standardq="workq"
    ncpus=28
#    absmem=60
#    standardq="gpuq"
elif [[ "${HOST:0:4}" == "magn" ]]
then
    computer="magnus"
    standardq="workq"
    ncpus=24
#    absmem=60
elif [[ "${HOST:0:4}" == "athe" ]]
then
    computer="athena"
    standardq="gpuq"
#    absmem=30 # Check this
fi

scratch="/astro"
group="/group"

#initial variables
dep=
tst=

# parse args and set options
while getopts ':td:a:p:u:h:r:' OPTION
do
    case "$OPTION" in
	d)
	    dep=${OPTARG}
	    ;;
    a)
        account=${OPTARG}
        ;;
    p)
        project=${OPTARG}
        ;;
	u)
        user=${OPTARG}
        ;;
    h)
        endpoint=${OPTARG}
        ;;
    r)
        remote=${OPTARG}
        ;;  
    t)
	    tst=1
	    ;;
	? | : | h)
	    usage
	    ;;
  esac
done
# set the obsid to be the first non option
shift  "$(($OPTIND -1))"
obsnum=$1

queue="-p $standardq"
base="$scratch/mwasci/$pipeuser/$project/"
code="$group/mwasci/$pipeuser/GLEAM-X-pipeline/"

# if obsid is empty then just print help

if [[ -z ${obsnum} ]] || [[ -z $project ]] || [[ ! -d ${base} ]]
then
    usage
fi

if [[ ! -z ${dep} ]]
then
    if [[ -f ${obsnum} ]]
    then
        depend="--dependency=aftercorr:${dep}"
    else
        depend="--dependency=afterok:${dep}"
    fi
fi

if [[ -z ${account} ]]
then
    account=pawsey0272
fi

# Establish job array options
if [[ -f ${obsnum} ]]
then
    numfiles=$(wc -l ${obsnum} | awk '{print $1}')
    arrayline="#SBATCH --array=1-${numfiles}%1"
else
    numfiles=1
    arrayline=''
fi

# start the real program
script="${code}queue/archive_${obsnum}.sh"
cat ${code}/bin/archive.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                 -e "s:BASEDIR:${base}:g" \
                                 -e "s:NCPUS:${ncpus}:g" \
                                 -e "s:HOST:${computer}:g" \
                                 -e "s:STANDARDQ:${standardq}:g" \
                                 -e "s:ACCOUNT:${account}:g" \
                                 -e "s:ENDUSER:${user}:g" \
                                 -e "s:ENDPOINT:${endpoint}:g" \
                                 -e "s:REMOTE:${remote}:g" \
                                 -e "s:PIPEUSER:${pipeuser}:g" \
                                 -e "s:ARRAYLINE:${arrayline}:g" > ${script}

output="${code}queue/logs/archive_${obsnum}.o%A"
error="${code}queue/logs/archive_${obsnum}.e%A"

if [[ -f ${obsnum} ]]
then
   output="${output}_%a"
   error="${error}_%a"
fi

sub="sbatch --begin=now+15 --output=${output} --error=${error} ${depend} ${queue} ${script}"
if [[ ! -z ${tst} ]]
then
    echo "script is ${script}"
    echo "submit via:"
    echo "${sub}"
    exit 0
fi
    
# submit job
jobid=($(${sub}))
jobid=${jobid[3]}

echo "Submitted ${script} as ${jobid} . Follow progress here:"

for taskid in $(seq ${numfiles})
    do
    # rename the err/output files as we now know the jobid
    obserror=`echo ${error} | sed -e "s/%A/${jobid}/" -e "s/%a/${taskid}/"`
    obsoutput=`echo ${output} | sed -e "s/%A/${jobid}/" -e "s/%a/${taskid}/"`

    if [[ -f ${obsnum} ]]
    then
        obs=$(sed -n -e ${taskid}p ${obsnum})
    else
        obs=$obsnum
    fi

    # record submission
    track_task.py queue --jobid=${jobid} --taskid=${taskid} --task='archive' --submission_time=`date +%s` --batch_file=${script} \
                        --obs_id=${obs} --stderr=${obserror} --stdout=${obsoutput}

    echo $obsoutput
    echo $obserror
done
