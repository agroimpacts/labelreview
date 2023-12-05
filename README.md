## labelreview

Tools for tracking progress and reviewing the results of labelling work done on a [`labeller`](https://github.com/agroimpacts/labeller) instance, including checks of individual labeller's work against imagery. Tools for creating a `docker` image that installs the necessary packages for launching a `jupyter` notebook (in `jupyter lab`) are provided, including instructions for running a `docker` container locally, as well as instructions for converting the image for use with `singularity` so that it can be used in an HPC environment. 

## Local use
### Clone this repository

Run the following command from a terminal prompt (if you are on Windows, we strongly recommend installing `git bash` first). 

```bash
git clone https://github.com/agroimpacts/labelreview.git
```

Then change your directory into the cloned repository:

```bash
cd /path/you/cloned/repository/into/labelreview
```

### Setup docker image

1. Install [`docker`](https://docs.docker.com/get-docker/) on your computer

2. Create a docker image

    ```bash
    docker build . -t agroimpacts/labelreview
    ```

    Note: replace "agroimpacts" with your user profile on docker hub (see next section).

3. After that installs, run the image:

    ```bash
    docker run -it -p 8888:8888 -v $(pwd):/home/workdir agroimpacts/labelreview
    ```

    For Windows-based use (thanks to this [post](https://stackoverflow.com/questions/41485217/mount-current-directory-as-a-volume-in-docker-on-windows-10)) for answers) if you are running the container from a Git Bash terminal emulator, the command will be:

    ```bash
    winpty docker run -it -v "/$(pwd -W):/home/workdir" agroimpacts/labelreview
    ```

    From Windows command line:

    ```bash
    docker run -it -v %cd%:/home/workdir agroimpacts/labelreview
    ```

    And from Powershell:

    ```bash
    docker run -it -v ${PWD}:/home/workdir agroimpacts/labelreview
    ```

    Note that this connects the directory you cloned the repo into it to the directory in the running docker container. That means that changes in the docker container will get picked up in the labelreview directory, and vice versa, so work you do in the container will be saved when the container is removed. 

4. Then copy and paste into your browser address bar the line with the URL and token in it that looks like this:

    ```bash
    http://127.0.0.1:8888/lab?token=<a long token hash>
    ```

   That will launch a jupyter lab session, and then you can open the `review_labellers.ipynb` notebook. 

5. To run the notebook, you will need to make a copy of `config-db-template.yaml`, which you can call `config-db.yaml`. Copy the credentials shared with you into that file. 

6. Run the notebook

7. When you are finished, you can stop the stop the container, using:

    ```bash
    docker ps -a
    ```

    That will list the containers. Copy the container id and then run:

    ```bash
    docker stop <container id>
    ```

    You can also remove the container, which you probably should do after re-running several times:

    ```bash
    docker rm <container id>
    ```

8. Run it again:

    ```bash
    docker run -it -p 8888:8888 -v $(pwd):/home/workdir agroimpacts/labelreview 
    ```

For other helpful resources on using docker, please see [here](https://hamedalemo.github.io/advanced-geo-python/lectures/docker.html#what-is-docker).

### Running on an HPC
These instructions were developed by @Rahebe22 for running on Clark University's HPC, but should translate to similar systems. 

To run on the HPC, do the following: 

1. Take the image you built previously (e.g. agroimpacts/labelreview) and push it to [docker hub](https://hub.docker.com/). This requires you first set up an account there. Once established, from your local terminal run:

    ```bash
    docker login
    ```

    And log in, and then:

    ```bash
    docker push agroimpacts/labelreview
    ```

    Replace "agroimpacts" with your docker hub profile name

2. `ssh` into the cluster

    ```bash
    ssh <your cluster user name>@hpc.clarku.edu
    ```

3. Make sure you clone this repo into your cluster home directory

    ```bash
    git clone https://github.com/agroimpacts/labelreview.git
    ```

4. Pull the image from docker hub, converting it to a singularity container

    ```bash
    cd labelreview
    singularity pull docker://agroimpacts/labelreview
    ```

    The command above will pull the public docker image from agroimpacts, creating the image `labelreview_latest.sif`. If you created one under your own profile, replace "agroimpacts" in the command above with your profile name. 

5. Launch an interactive slurm session, e.g. 

    ```bash
    srun --wait=0 --pty \
        --partition=<PART> \
        --cpus-per-task=<CPUS> \
        --gres=<GPUS> \
        -t <TIME> \
        --ntasks=1 \
        --pty bash
    ```

    Here <PART> should be replaced with the name of the cluster partition you want to run on, <CPUS> with the number of CPUs you want to run on (1 is fine for this application), <GPUS> is the name and number of the GPUs you want to run with (we don't need one here, so gpu:0 is the best entry), and <TIME> is the number of hours you want your job to run, specified as HR:MM:SS, or 01:00:00 for one hour. 

6. Once that is running, from within your cluster `labelreview` folder (which is where the singularity image should be), run the session:

    ```bash
    singularity run --bind $(pwd):/home/workdir labelreview_latest.sif
    ```

    That will launch a `jupyter lab` session. Collect the url, e.g. 

    ```
    http://127.0.0.1:8888/lab
    ```

    or 

    ```bash
    http://127.0.0.1:8888/lab?token=<a long token hash>
    ```

7. Establish an `ssh` connection to the HPC from your local terminal mapped to 8888.

    Open a new terminal tab, and run:

    ```bash
    ssh -NL 8888:gpu5:8888 <your cluster user name>@hpc.clarku.edu
    ```

    Once that is connected, paste the lab url from step 6 into your browser, and then you will be in a jupyter lab session that is running in the singularity container on the cluster. 

## Review labels

Once the container is running and you have launched `jupyter lab`, open up and worth through [review_labellers.ipynb](review_labellers.ipynb). 