from flask import Flask, render_template, request
import folium
from folium.plugins import HeatMap
import requests
from flask_caching import Cache

app = Flask(__name__)

# Configure cache
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 3600  # 1 hour
cache = Cache(app)

# Indicator mapping
INDICATOR_MAP = {
    'school': 'amenity=school',
    'bus_station': 'amenity=bus_station',
    'supermarket': 'shop=supermarket',
    'dentist': 'amenity=dentist',
    'apartments': 'building=residential',
    'park': 'leisure=park',
    'camp_site': 'tourism=camp_site',
    'parking': 'amenity=parking',
    'kindergarten': 'amenity=kindergarten',
    'playground': 'leisure=playground',
    'cabin': 'building=cabin',
    'nature_reserve': 'historic=nature_reserve',
}

# Area coordinates
AREA_IDS = {
    "alesund": [62.4702, 6.1549],  # Central coordinate of Ålesund
    "fjord": [62.2801, 7.1419],    # Central coordinate of Fjord Municipality
    "stranda": [62.3082, 6.9297],  # Central coordinate of Stranda Municipality
}

OVERPASS_URL = "http://overpass-api.de/api/interpreter"

# Function to fetch OpenStreetMap data
def fetch_osm_data(indicator, municipality):
    indicator_tag = INDICATOR_MAP.get(indicator.lower())
    bbox = None

    if municipality == "alesund":
        # Ålesund Municipality (accurate bbox)
        bbox = "(62.37,5.91,62.60,6.43)"
    elif municipality == "fjord":
        # Fjord Municipality (accurate bbox)
        bbox = "(62.10,6.93,62.38,7.56)"
    elif municipality == "stranda":
        # Stranda Municipality (accurate bbox)
        bbox = "(62.10,6.64,62.42,7.43)"
    else:
        return {}
    overpass_query = f"""
    [out:json][timeout:25];
    (
        node[{indicator_tag}]{bbox};
        way[{indicator_tag}]{bbox};
        relation[{indicator_tag}]{bbox};
    );
    out body;
    """
    try:
        response = requests.get(OVERPASS_URL, params={"data": overpass_query})
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}

# Function to extract coordinates from fetched data
def extract_coordinates(data):
    if not data or 'elements' not in data:
        return []

    locations = []
    for element in data['elements']:
        if element['type'] == 'node' and 'lat' in element and 'lon' in element:
            locations.append((element['lat'], element['lon']))
        elif element['type'] == 'way' and 'geometry' in element:
            latitudes = [point['lat'] for point in element['geometry']]
            longitudes = [point['lon'] for point in element['geometry']]
            centroid = (sum(latitudes) / len(latitudes), sum(longitudes) / len(longitudes))
            locations.append(centroid)
    return locations

@app.route('/')
def home():
    return "Welcome to the Liveabiltiy App!"


# Heatmap route
@app.route('/heatmap', methods=['GET'])
def heatmap():
    indicators = request.args.getlist('indicators')
    municipality = request.args.get('municipality', 'alesund').lower()
    radii = {ind: int(request.args.get(f'radius_{ind}', 500)) for ind in indicators}
    colors = {ind: request.args.get(f'color_{ind}', '#ff0000') for ind in indicators}

    # Set map center
    center = AREA_IDS.get(municipality, [62.472, 6.1549])
    m = folium.Map(location=center, zoom_start=9)

    # Add circles for each indicator
    for indicator in indicators:
        data = fetch_osm_data(indicator, municipality)
        locations = extract_coordinates(data)

        for lat, lon in locations:
            radius = radii.get(indicator, 500)
            color = colors.get(indicator, '#ff0000')
           # Add multiple circles with decreasing opacity to create a blur effect
            # for i in range(3, 0, -1):  # Create 3 layers
            #     folium.Circle(
            #         location=(lat, lon),
            #         radius=radius * (1 + (i * 0.2)),  # Slightly larger radius for outer layers
            #         color=color,
            #         fill=True,
            #         fill_color=color,
            #         fill_opacity=0.2 * i,  # Decreasing opacity for outer layers
            #         stroke=False
            #     ).add_to(m)

            # Add a base marker or sharp circle at the center
            folium.Circle(
                location=(lat, lon),
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.2,
                stroke=False
            ).add_to(m)
            # Add marker
            folium.Marker(
                location=(lat, lon),
                popup=f"{indicator.capitalize()}<br>Lat: {lat}, Lon: {lon}",
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(m)


    return render_template(
        'index.html',
        map=m._repr_html_(),
        indicator_map=INDICATOR_MAP,
        selected_indicators=indicators,
        selected_municipality=municipality,
        selected_radii=radii,
        selected_colors=colors,
    )

if __name__ == '__main__':
    app.run(debug=True, host= '0.0.0.0', port=8000)
