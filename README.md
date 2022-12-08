# paramsurvey-tooling

## Install

```
pip install paramsurvey-tooling
```

## paramsurvey usage on clusters with batch queues

Make 3 batch scripts: head, driver, and child. They all have a similar header:

```
#FOO batch header lines

. ~/setup-my-software-environment.sh
```

The script to set up your environment should activate your Conda environment, or
load modules or whatever.

Then each of these scripts gets one of the following commands:

* `pstool start head`
* `pstool start driver ./my-script.py foo bar baz`
* `pstool start child`

Finally, submit the head job, then the driver, and finally a bunch of children.

Instead of using a driver batch script, you can also run the driver on a head
node:

```
pstool submit ./my-script.py foo bar baz  # NOT YET WORKING
```

## Containers and paramsurvey

Many compute clusters do not support Docker containers, for security reasons.
These clusters often do support Singularity containers, and it's not hard to
turn an arbitrary Docker container into a Singularity container. Build
the Docker container on a machine that does have docker installed, and
then export it to a file:

```
docker save IMAGE_ID | gzip > my_docker_image.tar.gz
```

Transfer that file to a host with `paramsurvey-tooling` and `singularity`
installed, and do:

```
pstool build my_docker_image.tar.gz
```

## Documentation

Installing code in an environment:
* Conda
* OS packages
* modules

Containerized environments:
* Docker
* Singularity

Execution environment:
* [Laptop or a single server](Execution-Laptop.md)
* [Cluster with batch queue:](Execution-Cluster.md)
  * Philosophy
  * Details
    * slurm -- Harvard cluster
    * PBSPro -- ASIAA cluster
    * Grid Engine -- Smithsonian Hydra cluster
  * Tearing down
* Cloud-native:
  * Philosophy
  * Open Science Grid
    * https://bhpire.arizona.edu/2022/09/12/new-webinar-performing-large-scale-parameter-surveys-with-osg-services/
  * Ray Cluster on AWS or GCE
  * Ray Cluster over Kubernetes






