import zipfile
from shapely.geometry import LineString, Point
from shapely.ops import split
from fastkml import kml
from pyproj import Transformer
import simplekml
import os

# Extrae el contenido KML desde un archivo KMZ
def extract_kml_from_kmz(kmz_path):
    with zipfile.ZipFile(kmz_path, 'r') as z:
        for name in z.namelist():
            if name.endswith('.kml'):
                return z.read(name).decode('utf-8')
    raise FileNotFoundError("No se encontró un archivo KML en el KMZ")

# Parsea la primera línea encontrada desde el contenido KML
def parse_line_from_kml(kml_content):
    k = kml.KML()
    k.from_string(kml_content.encode('utf-8'))
    features = list(k.features)
    placemarks = list(features[0].features)
    for placemark in placemarks:
        geom = placemark.geometry
        if isinstance(geom, LineString):
            return geom
    raise ValueError("No se encontró una línea en el archivo KML")

# Parsea todos los puntos (marcadores de posición) del KML
def parse_points_from_kml(kml_content):
    k = kml.KML()
    k.from_string(kml_content.encode('utf-8'))
    features = list(k.features)
    placemarks = list(features[0].features)
    points = []
    for placemark in placemarks:
        geom = placemark.geometry
        if isinstance(geom, Point):
            points.append(geom)
    return points

# Crea un nuevo KMZ con la línea original segmentada en tramos definidos por los puntos
def create_segmented_kml(original_line, points, output_path):
    # Define la transformación: WGS84 → UTM zona 19 Sur (ajustar según tu zona)
    transformer = Transformer.from_crs("epsg:4326", "epsg:32719", always_xy=True)
    inverse_transformer = Transformer.from_crs("epsg:32719", "epsg:4326", always_xy=True)

    # Convertir la línea a coordenadas UTM
    line_utm = LineString([transformer.transform(*coord) for coord in original_line.coords])

    # Proyectar cada punto sobre la línea
    projected_points = [
        line_utm.interpolate(line_utm.project(Point(transformer.transform(*p.coords[0]))))
        for p in points
    ]

    # Ordenar los puntos proyectados a lo largo de la línea
    projected_points = sorted(projected_points, key=lambda p: line_utm.project(p))

    # Cortar progresivamente
    segments = []
    current_line = line_utm
    for pt in projected_points:
        result = split(current_line, pt)
        if len(result.geoms) >= 2:
            segments.append(result.geoms[0])
            current_line = result.geoms[1]
    segments.append(current_line)  # agregar el último tramo

    # Crear KMZ de salida
    kml_out = simplekml.Kml()
    for i, segment in enumerate(segments):
        coords = [inverse_transformer.transform(*pt) for pt in segment.coords]
        kml_out.newlinestring(name=f"Tramo {i+1}", coords=coords)

    kml_out.savekmz(output_path)
    print(f"Archivo generado: {output_path}")

# ========= USO ========= #
if __name__ == "__main__":
    # Reemplaza estas rutas por tus archivos reales
    kmz_linea = "camino.kmz"
    kmz_puntos = "marcadores.kmz"
    salida_kmz = "tramos_resultado.kmz"

    kml_linea = extract_kml_from_kmz(kmz_linea)
    kml_puntos = extract_kml_from_kmz(kmz_puntos)

    linea = parse_line_from_kml(kml_linea)
    puntos = parse_points_from_kml(kml_puntos)

    create_segmented_kml(linea, puntos, salida_kmz)
