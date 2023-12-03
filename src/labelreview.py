import pandas as pd
import geopandas as gpd
import rasterio
import numpy as np
import leafmap.leafmap as leafmap
import localtileserver
from ipyleaflet import WMSLayer, projections
from traitlets import Unicode
import psycopg
import yaml
import os
from pathlib import Path
import sqlalchemy as sa
from shapely.geometry import Polygon, box

class SHWMSLayer(WMSLayer):
    """Custom class to enable subsetting of images read from SentinelHub in 
    leafmap/ipyleaflet, provided by Ziga Cernigoj of SentinelHub
    https://forum.sentinel-hub.com/t/\
        select-area-of-byoc-image-using-bbox-geometry-in-iypleaflet/8211/2

    Args:
    ----
    WMSLayer: class
        WMSLayer class from ipyleaflet
    
    """
    time = Unicode('').tag(sync=True, o=True)
    geometry = Unicode('').tag(sync=True, o=True)
    maxcc=Unicode('').tag(sync=True, o=True)

class labelReview:
    """Functionality for extracting and viewing labels and associated quality 
    metrics drawn from a) a running labeller instances, or b) local label files.
    Imagery that labels are compared against can be drawn from SentinelHub or
    from locally stored image tiles. 

    Args:
    -----
    params : str
        Name of configuration yaml file.
    connection_type : str
        "database" if connecting to labeller instance, or "local" if working 
        with local files

    Methods:
    --------
    database_engine : Establish a database connnection engine using sqlalchemy
    get_data : Get data using a query from the postgres data, returning either 
        a pandas DataFrame or geopandas GeoDataFrame
    points_to_gridpoly : Converts a point to polygon using a given radius
    get_labels : Extract labels for a particular labeller and site (defaults to
        random selection of one site from all completed sites)
    set_wms_url : Create the URL needed to make a WMS request to SentinelHub
    plot_labels : Form a leafmap to display labels over SentinelHub imagery
    """


    def __init__(self, config, connection_type="database"):
        
        with open(config, 'r') as yaml_file:
            self.params = yaml.load(yaml_file, Loader=yaml.FullLoader)
        
        if connection_type == "database":
            self.db_engine = self.database_engine()

            query = "SELECT key, value FROM configuration WHERE key"\
                " LIKE 'instance%%'"
            self.tbl_config = self.get_data(query=query)   
        
        elif connection_type == "local": 
            print("Working locally")

    def database_engine(self):
        """Create a postgresql database engine"""

        connection_url = sa.URL.create(
            "postgresql+psycopg",
            username=self.params['labeller']['db_username'],
            password=self.params['labeller']['db_password'],
            host=self.params['labeller']['db_host'],
            database=self.params['labeller']['db_name']
        )
        engine = sa.create_engine(connection_url)
        return engine
    
    def get_data(self, query, method="pd"):
        """Query data from labeller database

        Parameters
        ----------
        query : str
            A postgresql query string
        method : str
            Either pd (pandas) to read into a non-spatial table, or gpd (for 
            one of the spatial tables)

        Returns
        -------
        A DataFrame or GeoDataFrame
        """    
        with self.db_engine.connect() as conn, conn.begin():
            if method=="pd":
                data = pd.read_sql(query, conn)
            elif method=="gpd":
                data = gpd.read_postgis(query, conn, geom_col='geom_clean', 
                                        crs=4326)
        return data

    def points_to_gridpoly(self, points, w, crs="epsg:4326"):
        points['geometry'] = points.apply(
            lambda x: box(x.x-w, x.y-w, x.x+w, x.y+w), axis=1
        )
        points_gdf = gpd.GeoDataFrame(points, crs=crs)
        return points_gdf

    def get_labels(self, assignments, id, type="Q", name="random", 
                   review_file="label_reviews.csv"):
        """Get labels for a particular labeller from a set of labelling 
        assignments

        Parameters
        ----------
        assignments : DataFrame
            Containing assignment data information from labeling tasks
        id : str
            ID of labeller whose work you want to review
        type : str
            What kind of assignment (specify with appropriate code, e.g. "Q" or 
            "F")
        name : str
            A specific site name, otherwise defaults to "random", in which case 
            a random site will be chosen. 
        review_file : str
            Path to file containing at a minimum the name of sites and the id 
            of the labeller who labelled it. When name is set to "random", this
            file, if it exists, will be read and any the names of any sites 
            that have been reviewed will be excluded from the random draw. 
        
        Returns
        -------
        A dictionary with the labeller id, the type of assignment, the point 
        representing the site center, a polygon of the sampling grid, one to 
        limit the scope of the call from SentinelHub, and labels from the 
        labeller and the expert, if each are available.
        """
        
        if name=="random":
            reviewed = pd.read_csv(review_file) if os.path.exists(review_file) \
                else None
            
            if isinstance(reviewed, pd.DataFrame):
                reviewed_names = reviewed.query("labeller.astype('str')==@id")\
                    .name.to_list()
                assignments = assignments\
                    .query("worker_id==@id & ~name.isin(@reviewed_names)")\
                    .reset_index(drop=True)

            site = assignments\
                .query("worker_id == @id & kml_type == @type")\
                .sample(n=1)
            
        else: 
            site = assignments.query("worker_id == @id & name == @name")

        queries = [
            f"select name, x, y, date from master_grid "\
                f"where name='{site.name.iloc[0]}'",
            f"select name, geom_clean from user_maps where assignment_id="\
                f"'{site.assignment_id.iloc[0]}'",
            f"select name, geom_clean from qaqcfields where name="\
                f"'{site.name.iloc[0]}'"
        ]
        point = self.get_data(query=queries[0])

        w1 = 0.005 / 2
        w2 = (0.005 / 2) * 2.56
        poly = self.points_to_gridpoly(points=point, w=w1)
        poly_img = self.points_to_gridpoly(points=point, w=w2)
        
        user_flds = self.get_data(query=queries[1], method="gpd")
        if type=="Q":
            q_flds = self.get_data(query=queries[2], method="gpd")
        else: 
            q_flds = None

        return {
            "id": id, "type": type, "point": point, "poly": poly, 
            "poly_img": poly_img, 
            "user": user_flds if len(user_flds) > 0 else None, 
            "expert": q_flds if isinstance(q_flds, pd.DataFrame) \
                and len(q_flds) > 0 else None
        }

    def set_wms_url(self, labels):
        instance = self.tbl_config.query("key.str.contains(@labels['type'])")\
            .value.iloc[0]
        url = f"https://services.sentinel-hub.com/ogc/wms/{instance}"
        return url

    def min_max(self, tile, bands, clip=None):
        """Calculate the min and max value for a locally stored image, with the 
        option to clip based on percentiles

        Parameters
        ----------
        tile : str
            File path to image
        bands : tuple
            Bands from which to calculate min and max 
        clip : int
            An integer, e.g. 1, specifying the lower tail percentile to clip

        Returns
        -------
        A list of min and list of max values

        """
        assert type(bands) is tuple, "Provide bands as tuple"
        
        with rasterio.open(tile) as src:
            values = src.read(bands)
        
        mins = []
        maxs = []
        
        for i in range(values.shape[0]):
            if clip:
                mins.append(np.nanpercentile(values[i], clip))
                maxs.append(np.nanpercentile(values[i], 100-clip))
            else: 
                mins.append(np.nanmin(values[i]))
                maxs.append(np.nanmax(values[i]))
        
        return mins, maxs

    def plot_labels(self, labels, tile=None, stretch=False):
        """Record a review after assessing a labeller's work

        Parameters
        ----------
        labels : list
            List containing output GeoDataFrames and associated id information
        tile : str
            String containing path to local geotiff tile to display.  Defaults 
            to None, in which case a WMS call be made to SentinelHub to look for 
            imagery
        stretch : bool
            Whether or not to apply a stretch to the local geotiff. If True, 
            a min-max stretch is applied between the 1st and 99th percentile 
            image values

        Returns
        -------
        A leafmap displaying the labels over the imagery on which they were 
        digitized

        Notes
        -----
        For local tiles, this is currently hard-coded to process 4-band images.   
        """


        bb = list(labels['poly_img'].bounds.loc[0])
        d = labels["point"].date[0]
        url = self.set_wms_url(labels)

        m = leafmap.Map(zoom=16, 
            center=labels["point"][["y", "x"]].iloc[0].to_list()
        )
        m.add_basemap("SATELLITE")
        m.add_tile_layer(
            url='https://server.arcgisonline.com/ArcGIS/rest/services/' +\
                'World_Imagery/MapServer/tile/{z}/{y}/{x}',
            name="ESRI",
            attribution="ESRI"
        )

        # target box and labeler and expert labels (if present)
        m.add_gdf(labels["poly"], style={"color": "white", "fillOpacity": 0.0}, 
                  layer_name=labels["point"].name[0])
        if isinstance(labels["user"], pd.DataFrame):
            m.add_gdf(labels["user"], style={"color": "red"}, 
                      layer_name="User labels")
        if isinstance(labels["expert"], pd.DataFrame):
            m.add_gdf(labels["expert"], layer_name="Expert labels")

        # Tile layers
        if not tile:  # SentinelHub
            print("Loading from SHUB")
            sh_wms = []
            for layer in ["TRUE-COLOR", "FALSE-COLOR"]:
                sh_wms.append(
                    SHWMSLayer(
                        url=url,
                        layers=layer,
                        format='image/png',
                        transparent=True,
                        geometry=str(labels['poly_img'].geometry.loc[0]),
                        time=f"{d}/{d}",
                        crs=projections.EPSG4326,
                        maxcc="100",
                        name=layer
                    )
                )
            
            m.add_layer(sh_wms[0])
            m.add_layer(sh_wms[1])

        else: # Local tiles
            print("Local tiles")
            assert os.path.exists(tile), "{tile} does not exist"
            if stretch:
                mins, maxs = self.min_max(self, tile, (1,2,3,4), clip=1)
            else: 
                mins, maxs = None

            m.add_raster(tile, bands=[1,2,3], layer_name='TRUE COLOR', 
                         vmin=mins, vmax=maxs)
            m.add_raster(tile, bands=[2,3,4], layer_name='FALSE COLOR', 
                         vmin=mins, vmax=maxs)

        return m
    
    def record_review(self, sample, id, review_file="label_reviews.csv", 
                      expert_labels=True):
        """Record a review after assessing a labeller's work

        Args:
        -----
        sample : str
            Name of sample site that was just reviewed
        id : str
            ID (as string) of labeller being assessed
        review_file : str
            Name of output csv to capture the reviewed sites. Defaults to 
            "label_reviews.csv" in current directory
        expert_labels : bool
            If True (default) then a second prompt will ask whether there is 
            feedback to give on a set of expert labels associated with the same
            site. 

        Returns:
        --------
        Review of labels (and any expert labels) added to DataFrame recorded to 
        csv
        """

        labeller = input(f"What is your rating/feedback for labeller {id} on "\
                         f"{sample}?: ")
        outlist = {"name": [sample], "labeller": [id], "rating": [labeller]}
        outdata = pd.DataFrame(outlist)
        
        if expert_labels:
            expert = input(f"What is your rating/feedback for the "\
                           f"corresponding expert labels for {sample}?: ")
            outdata.loc[len(outdata)] = [sample, "expert", expert]

        return outdata.to_csv(
            review_file, mode="a", header=not os.path.exists(review_file), 
            index=False
        )