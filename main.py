import os
import pandas as pd
import itertools
import json
import numpy as np
from decimal import *
from shapely.geometry import Point, Polygon, MultiPolygon, LinearRing, LineString, MultiLineString


data_resource_path = 'sources'
data_output_path = 'output-json'
data_pkl_path = 'output-json'


class JsonSafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, np.nan):
            return '"'+str(obj)+'"'
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return round(float(obj), 5)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, MultiPolygon):
            return str(obj.__class__)
        if isinstance(obj, Polygon):
            return str(obj.__class__)
        if isinstance(obj, LineString):
            return str(obj.__class__)
        if isinstance(obj, MultiLineString):
            return str(obj.__class__)
        if isinstance(obj, LinearRing):
            return str(obj.__class__)

        return super(JsonSafeEncoder, self).default(obj)


def read(path):
    return pd.read_pickle(path)


def get_gpd(directory, path):
    import geopandas as gpd
    map_regions = gpd.read_file(os.path.join(directory, path))
    map_regions.to_pickle(os.path.join(data_pkl_path, path+'.pkl'))


def flatten_coords(coords, dec):
    arr = [[round(c[0], dec), round(c[1], dec)] for c in coords]
    return list(itertools.chain(*arr))


def process_geom(coords, name):
    kmax_d = 0.0
    re_coords = []
    for i, p in enumerate(coords):
        if i < len(coords)-1:
            p_nx = coords[i+1]
        else:
            p_nx = coords[0]

        re_coords.append(p)

        k_dst = np.sqrt(np.power(p_nx[0]-p[0], 2) + np.power(p_nx[1]-p[1], 2))
        if k_dst == 0:
            continue

        k_vct = [(p_nx[0]-p[0])/k_dst, (p_nx[1]-p[1])/k_dst]

        if k_dst > kmax_d:
            kmax_d = k_dst

        if k_dst > 1.0:
            s_p = p
            while True:
                s_p = [s_p[0]+k_vct[0], s_p[1]+k_vct[1]]
                re_coords.append(s_p)
                k_dst = np.sqrt(np.power(p_nx[0] - s_p[0], 2) + np.power(p_nx[1] - s_p[1], 2))
                if k_dst < 1.0:
                    break

    print(name, kmax_d, 'added', len(re_coords)-len(coords))

    return re_coords


def geometry_to_coords(geom, decimal_places=4, name=None):
    def getter(element):
        if element.type in ['Polygon']:
            rco = process_geom(element.exterior.coords, name)
            return flatten_coords(rco, decimal_places)
        if element.type in ['LineString']:
            rco = process_geom(element.coords, name)
            return flatten_coords(rco, decimal_places)

    if geom.type == 'MultiPolygon' or geom.type == 'MultiLineString':
        return [getter(element) for element in geom.geoms]
    else:
        return getter(geom)


marine_polys_fields = ['featurecla', 'name', 'label', 'wikidataid', 'scalerank']
region_polys_fields = ['FEATURECLA', 'NAME', 'LABEL', 'WIKIDATAID', 'SCALERANK', 'REGION', 'SUBREGION']
blocks_seams_fields = ['featurecla', 'scalerank']


def print_hi(name):
    f = 'ne_50m_geography_marine_polys.shp'
    d = 'ne_50m_geography_marine_polys'

    get_gpd(os.path.join(data_resource_path, d), f)

    fields = marine_polys_fields
    filename = os.path.join(data_output_path, 'marine_polys_50m.json')
    df = read(os.path.join(data_pkl_path, f+'.pkl'))
    print(df.info())

    json_blob = {'meta': fields, 'data': []}

    for wi, row in df.iterrows():
        print(wi)
        row_properties = {}
        row_geometry = {'type': row.geometry.type, 'coordinates': geometry_to_coords(row.geometry, 4, row['name'])}
        for i in fields:
            row_properties[i] = row[i]

        row_data = dict({'properties': row_properties, 'geometry': row_geometry})
        json_blob['data'].append(row_data)

    with open(filename, "w") as file:
        json.dump(json_blob, file, indent=2, cls=JsonSafeEncoder)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
