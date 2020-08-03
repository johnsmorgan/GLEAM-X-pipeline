echo "loading profile"

module load pawseytools

# Change ssh title
echo -ne "\033]0;${HOSTNAME}\007"

if [[ ! -z "$SLURM_CLUSTER_NAME" ]]
then
  # we are on a worker node
  cluster=$SLURM_CLUSTER_NAME
else
  # we are on a login node
  cluster=$PAWSEY_CLUSTER
fi


if [[ "${cluster}" == "galaxy" ]]
then
    echo "Galaxy!"
    module use /group/mwa/software/modulefiles
    module load MWA_Tools/mwa-sci 
    module load manta-ray-client
    module load pigz

elif [[ "${cluster}" == "zeus" ]]
then
    echo "Zeus!"
    module use /group/mwa/software/modulefiles
    module load manta-ray-client
    module load pigz
    module load MWA_Tools/mwa-sci_test
    module load wsclean/master
    module load wcstools/3.8.7
elif [[ "${cluster}" == "magnus" ]]
then
    echo "Magnus!"
    module use /group/mwa/software/modulefiles
    module load MWA_Tools/mwa-sci 
    module load pigz
    module load wsclean/master
    module load wcstools/3.8.7
else
    echo "Where am i?"
fi

export CLUSTER=$cluster
export DBFILE=/group/mwasci/$USER/GLEAM-X-pipeline/db/GLEAM-X.sqlite
export PATH=${PATH}:/group/mwasci/$USER/bin/:/group/mwasci/$USER/GLEAM-X-pipeline/bin
export PYTHONPATH=$PYTHONPATH:/group/mwasci/$USER/lib/python2.7/site-packages/:~/lib/:/group/mwasci/$USER/bin/

# Add your MWA_ASVO_API_KEY here
export MWA_ASVO_API_KEY=feeba2d6-3fe4-4f5c-9c47-3cdb47c0e31a

# Init. the SQLite database here for user
if [[ ! -s $DBFILE ]];
then
    echo 'User sqlite database not found. Creating now. '
    /group/mwasci/$USER/GLEAM-X-pipeline/db/make_db.py
    /group/mwasci/$USER/GLEAM-X-pipeline/db/populate_sources_table.py
fi

