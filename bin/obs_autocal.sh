#! /bin/bash

#set -x

usage()
{
echo "obs_autocal.sh [-d dep] [-a account] [-t] obsnum
  -p project : project, no default
  -a account : computing account, default pawsey0272
  -d dep     : job number for dependency (afterok)
  -i iono    : run the ionospheric metric tests (default = True)
  -t         : test. Don't submit job, just make the batch file
               and then return the submission command
  obsnum     : the obsid to process, or a text file of obsids (newline separated). 
               A job-array task will be submitted to process the collection of obsids. " 1>&2;
exit 1;
}

pipeuser=$(whoami)

dep=
tst=
ion=

# parse args and set options
while getopts ':tia:d:p:' OPTION
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
	i)
	    ion=1
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

# if obsid or project are empty then just print help
if [[ -z ${obsnum} || -z ${project} ]]
then
    usage
fi

if [[ -z ${account} ]]
then
    account=pawsey0272
fi

# Supercomputer options
if [[ "${HOST:0:4}" == "zeus" ]]
then
    computer="zeus"
    standardq="workq"
    ncpus=28
    taskline="#SBATCH --ntasks=${ncpus}"
#    absmem=60
#    standardq="gpuq"
elif [[ "${HOST:0:4}" == "magn" ]]
then
    computer="magnus"
    standardq="workq"
    ncpus=48
    taskline=""
#    absmem=60
elif [[ "${HOST:0:4}" == "athe" ]]
then
    computer="athena"
    standardq="gpuq"
    ncpus=40
    taskline=""
#    absmem=30 # Check this
fi

# Establish job array options
if [[ -f ${obsnum} ]]
then
    echo "${obsnum} is a file that exists, proceeding with job-array set up"
    numfiles=$(wc -l ${obsnum} | awk '{print $1}')
    arrayline="#SBATCH --array=1-${numfiles}"
    echo "Number of obsids to process: ${numfiles}"
else
    numfiles=1
    arrayline=''
fi

dbdir="/group/mwasci/$pipeuser/GLEAM-X-pipeline/"
codedir="/group/mwasci/$pipeuser/GLEAM-X-pipeline/"
queue="-p $standardq"
datadir=/astro/mwasci/$pipeuser/$project

# set dependency
if [[ ! -z ${dep} ]]
then
    depend="--dependency=afterok:${dep}"
fi

script="${codedir}queue/autocal_${obsnum}.sh"

cat ${codedir}bin/autocal.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                     -e "s:DATADIR:${datadir}:g" \
                                     -e "s:HOST:${computer}:g" \
                                     -e "s:TASKLINE:${taskline}:g" \
                                     -e "s:STANDARDQ:${standardq}:g" \
                                     -e "s:IONOTEST:${ion}:g" \
                                     -e "s:ACCOUNT:${account}:g" \
                                     -e "s:PIPEUSER:${pipeuser}:g" \
                                     -e "s:ARRAYLINE:${arrayline}:g" > ${script}


output="${codedir}queue/logs/autocal_${obsnum}.o%A"
error="${codedir}queue/logs/autocal_${obsnum}.e%A"

if [[ -f ${obsnum} ]]
then
   output="${output}_%a"
   error="${error}_%a"
fi

sub="sbatch -M $computer --output=${output} --error=${error} ${depend} ${queue} ${script}"

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
    python ${dbdir}/bin/track_task.py queue --jobid=${jobid} --taskid=${taskid} --task='calibrate' --submission_time=`date +%s` --batch_file=${script} \
                        --obs_id=${obs} --stderr=${obserror} --stdout=${obsoutput}

    echo $obsoutput
    echo $obserror
done
