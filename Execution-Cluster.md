# Cluster with a batch queue

## Philosophy

Running paramsurvey on a cluster often involves using a batch queue system.
You need to put the commands you want to run into a file along with some
information as to how much resources the job needs, submit this batch
job file to a queue, and when nodes become available, your job runs.

When using traditional HPC software like MPI on a cluster, if your job
requires 10 nodes, then usually you'll run a single batch job that
asks for 10 nodes, and it won't start until it gets all 10.

The `Ray` backend used by paramsurvey is more flexible than this. You
can submit a series of single-node batch jobs, and whenever they
start, they will take part in your computation.

These individual batch jobs need to fill an entire node because of a
quirk that Ray is insecure if other users are logged into the node Ray
is running on. The main bad thing that could happen is that a
mischevious user might cause your job to exit early.

Another quirk of Ray is that Ray needs one node to be the "head" node
of your Ray cluster. It needs to start first, and it will write to
a file in your home directory to tell subsequent Ray jobs how to find
the "head" node.

The final quirk of Ray is that your program, which is called the
"driver" in Ray jargon, needs to run somewhere. On a cluster, that
somewhere should be another batch job. That way it will continue
running even if your login session on the cluster is interrupted.

This leaves us with 3 different batch scripts that need to be run.

The first is the "head" job, which needs to begin first.

The next is the "driver" job, which will begin running the computation on
all of the available nodes, including nodes that join the Ray cluster
after the driver starts.

Finally, there are a bunch of "child" jobs, which provide more compute
resources.

The exact content of these batch scripts depends on which batch queue
system your cluster uses. Also, your batch script will need to set up
your software environment. And finally, if you

### slurm

The following scripts are customized for Harvard's Cannon cluster,
which has nodes with 48 cores and 96 gigs of memory.

#### head.batch

```
#!/bin/bash
#SBATCH -n 48 # Number of cores requested
#SBATCH -N 1 # Number of nodes requested
#SBATCH -t 10000 # Runtime in minutes
#SBATCH -p blackhole,unrestricted,shared # Partition to submit to
#SBATCH --mem-per-cpu=2000 # Memory per cpu in MB
#SBATCH --open-mode=append
#SBATCH -o job_%j.out # Standard out goes to this file
#SBATCH -e job_%j.err # Standard err goes to this filehostname
##SBATCH --constraint="holyhdr" # holyscratch is only reliable with this constraint

. ~/configure-your-software-environment.sh

PORT=6379
REDIS_PASSWORD=thehfhghedhdjfhgfhdhdhdf
echo $(hostname):$PORT $REDIS_PASSWORD > ~/.ray-head-details

# optional, reserve 3 cores for the Ray system itself
let "CPUS = $SLURM_JOB_CPUS_PER_NODE - 3"

ray start --head --block --redis-port=$PORT --redis-password=$REDIS_PASSWORD --num-cpus=$CPUS

echo ray head exiting
```

#### driver.batch

```
# copy the SBATCH lines from above

. ~/configure-your-software-environment.sh

ADDRESS=$(cat ~/.ray-head-details  | cut -d ' ' -f 1)
REDIS_PASSWORD=$(cat ~/.ray-head-details  | cut -d ' ' -f 2)

# optional, reserve 1 core for the driver python process
let "CPUS = $SLURM_JOB_CPUS_PER_NODE - 1"

ray start --address=$ADDRESS --redis-password=$REDIS_PASSWORD --num-cpus=$CPUS

cd $SLURM_SUBMIT_DIR

python ./my-program.py some args > STDOUT 2> STDERR

# very optional, cancel all of your running jobs when the driver is finished
# note that this cancels all jobs for $USER, even ones totally unrelated to
# paramsurvey

#### scancel -u $USER

```

#### child.batch

```
# copy the SBATCH lines from above

. ~/configure-your-software-environment.sh

ADDRESS=$(cat ~/.ray-head-details  | cut -d ' ' -f 1)
REDIS_PASSWORD=$(cat ~/.ray-head-details  | cut -d ' ' -f 2)

ray start --block --address=$ADDRESS --redis-password=$REDIS_PASSWORD --num-cpus=$SLURM_JOB_CPUS_PER_NODE

echo ray child exiting
```

### PBS Pro

### Grid Engine

## Tearing down

The above batch scripts do not exit when your "driver" has finished. You could submit an
additional "driver" job when the first one finishes, or you can have the driver script
cancel all of the batch jobs after the driver finishes.
