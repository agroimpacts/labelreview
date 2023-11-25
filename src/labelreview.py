import pandas as pd
import geopandas as gpd
import leafmap.leafmap as leafmap
from ipyleaflet import WMSLayer, projections
from traitlets import Unicode
import localtileserver
import psycopg
import yaml
import os
from pathlib import Path
import pandas.io.sql as sqlio
import sqlalchemy as sa
from shapely.geometry import Polygon, box

class SHWMSLayer(WMSLayer):
    """Custom class to enable subsetting of images read from SentinelHub in 
    leafmap/ipyleaflet

    Args:
    ----
    WMSLayer: class
        WMSLayer class from ipyleaflet
    
    """
    time = Unicode('').tag(sync=True, o=True)
    geometry = Unicode('').tag(sync=True, o=True)
    maxcc=Unicode('').tag(sync=True, o=True)

class labelReview:
    def __init__(self, config):
        
        with open(config, 'r') as yaml_file:
            self.params = yaml.load(yaml_file, Loader=yaml.FullLoader)
                            
        # self.db_username = self.params['labeller']['db_username']
        # self.db_host = self.params['labeller']['db_host']
        # self.db_password=self.params['labeller']['db_password']
        # self.db_name=self.params['labeller']['db_name']

        self.db_engine = self.database_engine()
        # print(self.db_engine)

        query = "SELECT key, value FROM configuration WHERE key"\
            " LIKE 'instance%%'"
        # print(self.query)
        self.tbl_config = self.get_data(query=query)   

    def __del__(self):
        self.close()

    def database_engine(self):
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
        # print(query)
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

    def get_labels(self, assignments, id, type="Q", name="random"):
        if name=="random":
            site = assignments.query("worker_id == @id & kml_type == @type")\
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
        w2 = (0.005 / 2)*2.56
        poly = self.points_to_gridpoly(points=point, w=w1)
        poly_img = self.points_to_gridpoly(points=point, w=w2)
        
        user_flds = self.get_data(query=queries[1], method="gpd")
        if type=="Q":
            q_flds = self.get_data(query=queries[2], method="gpd")
        else: 
            q_flds = None

        return {"type": type, "point": point, "poly": poly, 
                "poly_img": poly_img, "user": user_flds, "expert": q_flds}

    def row_to_list(self, df_row):
        return df_row.iloc[0].to_list()

    def set_wms_url(self, labels):#, bbox, color="TRUE-COLOR"):
        instance = self.tbl_config.query("key.str.contains(@labels['type'])")\
            .value.loc[0]
        url = f"https://services.sentinel-hub.com/ogc/wms/{instance}"
        return url

    def plot_labels(self, labels):
        bb = list(labels['poly_img'].bounds.loc[0])
        d = labels["point"].date[0]
        url = self.set_wms_url(labels)

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
            
        m = leafmap.Map(zoom=16, 
            center=self.row_to_list(labels["point"][["y", "x"]])
        )
        m.add_basemap("SATELLITE")
        m.add_gdf(labels["poly"], style={"color": "white"}, 
                  layer_name=labels["point"].name[0])
        m.add_gdf(labels["user"], style={"color": "red"}, 
            layer_name="User labels"
        )
        m.add_gdf(labels["expert"], layer_name="Expert labels")
        m.add_layer(sh_wms[0])
        m.add_layer(sh_wms[1])
        return m