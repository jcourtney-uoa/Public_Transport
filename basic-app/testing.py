import pandas as pd
import geopandas as gpd
#import openpyxl
import matplotlib.pyplot as plt

# Import the data
df = pd.read_csv("data/clean_patronage.csv")

# Import the geodata for routes and stops
bus_routes = gpd.read_file("data/bus_routes.gpkg")
bus_stops = gpd.read_file("data/bus_stops.gpkg")

uni_stops = [
    "Stop E Auckland Universities",
    "Stop C Auckland Universities",
    "Stop D Auckland Universities",
    "Stop B Auckland Universities",
    "University of Auckland",
    "AUT City Campus"
]

uni_stop_layer = bus_stops[bus_stops["STOPNAME"].isin(uni_stops)]

# Create 10 m buffer
stop_buffer = uni_stop_layer.copy()
stop_buffer["geometry"] = stop_buffer.geometry.buffer(10)

# Find intersections with lines
intersections = gpd.overlay(
    bus_routes,
    stop_buffer,
    how="intersection"
)

# Find unique route IDs from intersections
unique_route_ids = intersections["ROUTENUMBER"].unique()

# Select full routes
intersecting_routes = bus_routes[
    bus_routes["ROUTENUMBER"].isin(unique_route_ids)
]
# Plot
fig, ax = plt.subplots(figsize=(12, 12))

# All routes
bus_routes.plot(
    ax=ax,
    color="lightgrey",
    linewidth=1,
    label="All Routes"
)

# Highlight intersecting routes
intersecting_routes.plot(
    ax=ax,
    color="red",
    linewidth=2,
    label="Intersecting Routes"
)

# Plot buffers
stop_buffer.plot(
    ax=ax,
    color="blue",
    alpha=0.3,
    edgecolor="blue",
    label="10m Buffer"
)

# Plot stops
uni_stop_layer.plot(
    ax=ax,
    color="black",
    markersize=40,
    label="University Stops"
)

plt.legend()
plt.title("Bus Routes Intersecting University Stop Buffers")
plt.axis("equal")
plt.show()