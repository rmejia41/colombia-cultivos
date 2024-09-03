from sodapy import Socrata
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
from dash import Dash, dcc, html, Input, Output  # Correct import
import plotly.express as px
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import json
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Get the Socrata app token from the environment variable
app_token = os.getenv('SOCRATA_APP_TOKEN')

# Socrata client initialization and data fetching
data_url = 'www.datos.gov.co'
data_set = 'v3rx-q7t3'
client = Socrata(data_url, app_token)
client.timeout = 90

try:
    results = client.get(data_set, limit=1500000)
    df = pd.DataFrame.from_records(results)
except Exception as e:
    print(f"Error fetching data: {e}")
    raise

# Convert 'the_geom' column from GeoJSON-like dictionaries to Shapely geometries
df['geometry'] = df['the_geom'].apply(lambda x: shape(x))
gdf = gpd.GeoDataFrame(df, geometry='geometry')

# Standardize the year columns (remove trailing spaces and normalize)
gdf.columns = gdf.columns.str.strip()

# Prepare data for the bubble chart
years = list(range(2001, 2023))
bubble_data = pd.DataFrame({'year': years})

# Correct column names to match the dataframe
year_col_map = {
    2001: 'areacoca_2001',
    2002: 'areacoca_2002',
    2003: 'areacoca_2003',
    2004: 'areacoca2004',
    2005: 'areacoca_2005',
    2006: 'areacoca_2006',
    2007: 'areacoca_2007',
    2008: 'areacoca_2008',
    2009: 'areacoca_2009',
    2010: 'areacoca_2010',
    2011: 'areacoca_2011',
    2012: 'areacoca_2012',
    2013: 'areacoca_2013',
    2014: 'areacoca_2014',
    2015: 'areacoca_2015',
    2016: 'areacoca_2016',
    2017: 'areacoca_2017',
    2018: 'areacoca_2018',
    2019: 'areacoca_2019',
    2020: 'areacoca_2020',
    2021: 'areacoca_2021',
    2022: 'coca2022_'
}

# Calculate total coca density per year, convert to numeric, then scale it down for visualization
for year in years:
    column_name = year_col_map[year]
    total_density = pd.to_numeric(gdf[column_name], errors='coerce').sum()
    bubble_data.loc[bubble_data['year'] == year, 'total_density'] = total_density

# Convert 'total_density' to numeric before further calculations
bubble_data['total_density'] = pd.to_numeric(bubble_data['total_density'], errors='coerce')

# Scale down densities to ensure bubbles are visible
bubble_data['scaled_density'] = bubble_data['total_density'] / bubble_data['total_density'].max() * 20

# Initialize Dash app
app = Dash(__name__)
server = app.server

# Define the layout with a framed and stylish title
app.layout = html.Div(
    style={'backgroundColor': '#f9f9f9', 'padding': '20px', 'fontFamily': 'Arial, sans-serif'},  # Modern font
    children=[
        html.Div(
            html.H1(
                "Coca Density Trends in Colombia (2001-2022)",
                style={
                    'textAlign': 'center',
                    'color': '#2c3e50',  # Darker modern color
                    'fontFamily': 'Montserrat, sans-serif',  # Modern font for title
                    'fontWeight': 'bold',
                    'fontSize': '32px',
                    'margin': '0',  # Remove default margin
                }
            ),
            style={
                'border': '2px solid #2c3e50',  # Dark border
                'padding': '20px',  # Space inside the border
                'borderRadius': '10px',  # Rounded corners
                'backgroundColor': '#ecf0f1',  # Light background color
                'boxShadow': '0 4px 8px rgba(0, 0, 0, 0.1)',  # Subtle shadow for depth
                'marginBottom': '20px'  # Space below the title
            }
        ),
        html.Div(
            style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'marginBottom': '20px'},
            children=[
                html.Label(
                    "Select Year:",
                    style={
                        'marginRight': '10px',
                        'fontWeight': 'bold',
                        'fontFamily': 'Montserrat, sans-serif',  # Modern font for label
                        'color': '#2c3e50'
                    }
                ),
                dcc.Dropdown(
                    id='year-dropdown',
                    options=[{'label': str(year), 'value': year} for year in years],
                    value=2001,
                    clearable=False,
                    style={
                        'width': '120px',
                        'fontFamily': 'Montserrat, sans-serif',  # Modern font for dropdown
                        'color': '#2c3e50',  # Text color
                        'backgroundColor': '#ecf0f1',  # Light modern background
                        'border': '1px solid #bdc3c7',  # Subtle border color
                        'borderRadius': '5px'
                    }
                ),
            ]
        ),
        html.Div(
            style={'display': 'flex', 'justifyContent': 'space-between'},
            children=[
                dcc.Graph(id='density-map', style={'width': '48%', 'height': '700px'}),
                dcc.Graph(id='bubble-chart', style={'width': '48%', 'height': '700px'})  # Matching height for both
            ]
        ),
        html.Div(
            style={'textAlign': 'center', 'marginTop': '20px'},
            children=[
                html.A(
                    "Densidad de Cultivos de Coca - Subdirección Estratégica y de Análisis - Ministerio de Justicia y del Derecho",
                    href="https://www.datos.gov.co/en/Justicia-y-Derecho/Densidad-de-Cultivos-de-Coca-Subdirecci-n-Estrat-g/v3rx-q7t3/about_data",
                    target="_blank",
                    style={
                        'color': '#007bff',
                        'textDecoration': 'none',
                        'fontWeight': 'bold',
                        'fontSize': '12px',  # Smaller font size for the link
                        'marginTop': '10px'  # Adjust margin for spacing
                    }
                )
            ]
        )
    ]
)

# Define the callback to update the map and bubble chart based on the selected year
@app.callback(
    [Output('density-map', 'figure'),
     Output('bubble-chart', 'figure')],
    Input('year-dropdown', 'value')
)
def update_visuals(selected_year):
    # Get the correct column name based on the selected year
    year_col = year_col_map[selected_year]

    # Filter data for the selected year
    gdf_year = gdf[['geometry', year_col]].copy()
    gdf_year = gdf_year.rename(columns={year_col: 'density'})

    # Ensure 'density' is numeric and handle NaN values
    gdf_year['density'] = pd.to_numeric(gdf_year['density'], errors='coerce').fillna(0)

    # Calculate the min and max for density to set the correct range
    min_density = gdf_year['density'].min()
    max_density = gdf_year['density'].max()

    # Adjust the range to make colors more intense (narrow the range)
    adjusted_min = min_density
    adjusted_max = max_density * 0.3  # Further reduce the upper limit for a more intense color scale

    # Create a darker, more intense custom blue color scale
    custom_colorscale = [
        [0.0, "rgb(173, 216, 230)"],  # Lighter blue
        [0.2, "rgb(135, 206, 250)"],  # Sky blue
        [0.4, "rgb(70, 130, 180)"],   # Steel blue
        [0.6, "rgb(30, 144, 255)"],  # Dodger blue
        [0.8, "rgb(0, 0, 205)"],  # Medium blue
        [1.0, "rgb(0, 0, 139)"]  # Dark blue
    ]

    # Convert GeoDataFrame to GeoJSON
    geojson = json.loads(gdf_year.geometry.to_json())

    # Create the choropleth map
    fig_map = go.Figure(go.Choroplethmapbox(
        geojson=geojson,
        locations=gdf_year.index,
        z=gdf_year['density'],
        colorscale=custom_colorscale,
        zmin=adjusted_min,
        zmax=adjusted_max,
        marker_opacity=0.6,
        marker_line_width=0
    ))

    # Update layout for the map
    fig_map.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=5,
        mapbox_center={"lat": 4.5709, "lon": -74.2973},
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar=dict(
            title="Coca Density (Hectares)",
            tickvals=[adjusted_min, adjusted_max],
            ticktext=["Low", "High"]
        )
    )

    # Create the bubble chart with a max legend value of 20 hectares
    fig_bubble = px.scatter(
        bubble_data,
        x='year',
        y='scaled_density',  # Use the scaled density for better visualization
        size='scaled_density',
        size_max=9,  # Control the bubble size for better readability
        color='scaled_density',
        color_continuous_scale=custom_colorscale,
        labels={'scaled_density': 'Scaled Coca Density (Hectares)', 'year': 'Year'},
        title="Coca Density Over Time"
    )
    fig_bubble.update_traces(mode='markers', marker=dict(sizemode='diameter', opacity=0.7))

    # Set x-axis to cover the year range from 2001 to 2022
    fig_bubble.update_layout(
        xaxis=dict(range=[2000, 2025]),  # Set x-axis range to match the data years
        yaxis=dict(range=[0, 30]),  # Set the y-axis to have a maximum value of 30 hectares
        margin={"r": 0, "t": 50, "l": 0, "b": 0}
    )

    return fig_map, fig_bubble

    # Run the app


if __name__ == '__main__':
    app.run_server(debug=False)

