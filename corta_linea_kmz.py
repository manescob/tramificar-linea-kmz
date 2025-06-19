import zipfile
from shapely.geometry import LineString, Point
from shapely.ops import split
from fastkml import kml
from pyproj import Transformer
import simplekml
import os

def extract_kml_from_kmz(kmz_path):
    with zipfile.ZipFile(kmz_path, 'r') as z:
        for name in z.namelist():
            if name.endswith('.kml'):
                return z.read(name).decode('utf-8')
    raise FileNotFoundError("No se encontró un archivo KML en el KMZ")

def parse_line_from_kml(kml_content):
    k = kml.KML()
    k.from_string(kml_content.encode('utf-8'))
    features = list(k.features())
    placemarks = list(features[0].features())
    for placemark in placemarks:
        geom = placemark.geometry
        if isinstance(geom, LineString):
            return geom
    raise ValueError("No se encontró una línea en el archivo KML")

def parse_points_from_kml(kml_content):
    k = kml.KML()
    k.from_string(kml_content.encode('utf-8'))
    features = list(k.features())
    placemarks = list(features[0].features())
    points = []
    for placemark in placemarks:
        geom = placemark.geometry
        if isinstance(geom, Point):
            points.append(geom)
    return points

def create_segmented_kml(original_line, points, output_path):
    # Convertir a UTM usando un transformer (asumimos WGS84 a UTM 19S por ejemplo)
    transformer = Transformer.from_crs("epsg:4326", "epsg:32719", always_xy=True)
    inverse_transformer = Transformer.from_crs("epsg:32719", "epsg:4326", always_xy=True)

    line_utm = LineString([transformer.transform(*coord) for coord in original_line.coords])
    projected_points = [line_utm.interpolate(line_utm.project(Point(transformer.transform(*p.coords[0])))) for p in points]

    for pt in projected_points:
        line_utm = split(line_utm, pt)

    kml_out = simplekml.Kml()
    for segment in line_utm.geoms:
        coords = [inverse_transformer.transform(*pt) for pt in segment.coords]
        kml_out.newlinestring(coords=coords)

    kml_out.savekmz(output_path)

# Uso
kmz_linea = "camino.kmz"
kmz_puntos = "marcadores.kmz"
salida_kmz = "tramos_resultado.kmz"

kml_linea = extract_kml_from_kmz(kmz_linea)
kml_puntos = extract_kml_from_kmz(kmz_puntos)

linea = parse_line_from_kml(kml_linea)
puntos = parse_points_from_kml(kml_puntos)

create_segmented_kml(linea, puntos, salida_kmz)
