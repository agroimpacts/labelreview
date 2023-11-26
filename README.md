## labelreview

This repository provides the tools for creating a `docker` image that installs the necessary packages for launching a `jupyter` notebook (in `jupyter lab`)  that can be used to track labelling progress on a [`labeller`](https://github.com/agroimpacts/labeller) instance, including checks of individual labeller's work against imagery. 


## Clone this repository

Run the following command from a terminal prompt (if you are on Windows, we strongly recommend installing `git bash` first)

```bash
git clone 
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

4. Then copy and paste into your browser address bar the line with the URL and token in it that looks like this:

    ```bash
    http://127.0.0.1:8888/lab?token=<a long token hash>
    ```

   That will launch a jupyter lab session, and then you can open the `review_labellers.ipynb` notebook. 