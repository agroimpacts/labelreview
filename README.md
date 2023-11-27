## labelreview

This repository provides the tools for creating a `docker` image that installs the necessary packages for launching a `jupyter` notebook (in `jupyter lab`)  that can be used to track labelling progress on a [`labeller`](https://github.com/agroimpacts/labeller) instance, including checks of individual labeller's work against imagery. 


## Clone this repository

Run the following command from a terminal prompt (if you are on Windows, we strongly recommend installing `git bash` first)

```bash
git clone https://github.com/agroimpacts/labelreview.git
```

Then change your directory into the cloned repository:

```bash
cd /path/you/cloned/repository/into/labelreview
```

## Setup docker image

1. Install [`docker`](https://docs.docker.com/get-docker/) on your computer

2. Create a docker image

    ```bash
    docker build . -t agroimpacts/labelreview
    ```
3. After that installs, run the image:

    ```bash
    docker run -it -p 8888:8888 -v </path/you/cloned/repository/into/labelreview>:/home/workdir agroimpacts/labelreview 
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
    docker run -it -p 8888:8888 -v </path/you/cloned/repository/into/labelreview>:/home/workdir agroimpacts/labelreview 
    ```

For other helpful resources on using docker, please see [here](https://hamedalemo.github.io/advanced-geo-python/lectures/docker.html#what-is-docker).