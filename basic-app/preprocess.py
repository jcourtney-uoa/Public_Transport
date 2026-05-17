"""
preprocess.py — run once before starting the app
Run: python preprocess.py

Outputs (saved to data/processed/):
  routes_uni.gpkg     — full routes passing university stops
  stops_markers.gpkg  — marker point (centroid of uni stops)
"""
from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, MultiLineString, LineString, GeometryCollection

HERE = Path(__file__).parent
RAW  = HERE.parent / "data" / "raw"
OUT  = HERE.parent / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

print("Loading raw data...")
bus_routes = gpd.read_file(RAW / "bus_routes.gpkg")
bus_stops  = gpd.read_file(RAW / "bus_stops.gpkg")
bus_routes["ROUTENUMBER"] = bus_routes["ROUTENUMBER"].astype(str).str.strip()
print(f"  routes: {len(bus_routes)} rows, CRS={bus_routes.crs}")
print(f"  stops:  {len(bus_stops)} rows,  CRS={bus_stops.crs}")

UNI_STOP_NAMES = [
    "Stop B Auckland Universities",
    "Stop C Auckland Universities",
    "Stop D Auckland Universities",
    "Stop E Auckland Universities",
    "University of Auckland",
    "AUT City Campus",
]

def to_multiline(geom):
    if isinstance(geom, LineString):
        return MultiLineString([geom])
    if isinstance(geom, MultiLineString):
        return geom
    if isinstance(geom, GeometryCollection):
        lines = [g for g in geom.geoms if isinstance(g, (LineString, MultiLineString))]
        parts = []
        for g in lines:
            parts.extend(g.geoms if isinstance(g, MultiLineString) else [g])
        return MultiLineString(parts) if parts else geom
    return geom

print("\nFinding university routes...")
uni_stops = bus_stops[bus_stops["STOPNAME"].isin(UNI_STOP_NAMES)]
print(f"  Matched {len(uni_stops)} stops")

buf = uni_stops.to_crs(2193).copy()
buf["geometry"] = buf.geometry.buffer(50)
ix  = gpd.overlay(bus_routes, buf, how="intersection")
ids = ix["ROUTENUMBER"].unique()
result = bus_routes[bus_routes["ROUTENUMBER"].isin(ids)].copy()
print(f"  {result['ROUTENUMBER'].nunique()} unique routes, {len(result)} rows")

# Dissolve to one row per route
names     = result.groupby("ROUTENUMBER")["ROUTENAME"].first()
dissolved = result.dissolve(by="ROUTENUMBER", as_index=False)[["ROUTENUMBER","geometry"]]
dissolved["ROUTENAME"] = dissolved["ROUTENUMBER"].map(names)
dissolved["geometry"]  = dissolved["geometry"].apply(to_multiline)
dissolved = dissolved.to_crs(epsg=4326)
print(f"  After dissolve: {len(dissolved)} rows (one per route)")

dissolved.to_file(OUT / "routes_uni.gpkg", driver="GPKG")
print("  Saved routes_uni.gpkg")

# Marker point
uni_lat = uni_stops["STOPLAT"].astype(float).mean()
uni_lon = uni_stops["STOPLON"].astype(float).mean()
markers = gpd.GeoDataFrame(
    {"name": ["Auckland Universities"], "lat": [uni_lat], "lon": [uni_lon]},
    geometry=[Point(uni_lon, uni_lat)],
    crs="EPSG:4326",
)
markers.to_file(OUT / "stops_markers.gpkg", driver="GPKG")
print(f"\nMarker: {uni_lat:.5f}, {uni_lon:.5f}")
print(f"\nAll done. Files written to {OUT}")
