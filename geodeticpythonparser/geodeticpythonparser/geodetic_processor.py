# This script processes geodetic data: loads points from a CSV file,
# filters them based on proximity to a central camp location,
# and generates an HTML map visualizing these points.
# It can dynamically install required packages (pandas, geopy, folium),
# but it is recommended to install them beforehand using the provided
# `requirements.txt` file: pip install -r requirements.txt

import os
import subprocess
import sys

# Function to install missing modules
def install_and_import(package):
    """
    Imports a package if available, or installs it using pip and then imports it.
    Note: It's generally recommended to manage dependencies via `requirements.txt`.
    This function is a fallback for environments where packages might be missing.
    """
    try:
        __import__(package)
    except ImportError:
        print(f"{package} is not installed. Installing now...")
        # It's good practice to use sys.executable to ensure pip is called with the correct Python interpreter.
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    finally:
        globals()[package] = __import__(package)

# Ensure required libraries are installed (fallback if not using requirements.txt)
# For a more standard approach, run: pip install -r requirements.txt
install_and_import("pandas")
install_and_import("geopy")
install_and_import("folium")

import pandas as pd
from geopy.distance import geodesic
import folium

# Define the location of the student camp (Konakovo, Tverskaya Oblast', Russian Federation)
CAMP_LOCATION = (56.7119, 36.7614) # Latitude, Longitude
MAX_DISTANCE_KM = 5 # Default maximum distance in kilometers for filtering points

def create_sample_file(file_path):
    """
    Creates a sample geodetic data CSV file if it doesn't already exist.
    The sample file contains 'latitude', 'longitude', and 'description' columns.

    Args:
        file_path (str): The path where the sample CSV file will be created.
    """
    sample_data = {
        'latitude':    [56.7110, 56.7130, 56.7150],
        'longitude':   [36.7615, 36.7600, 36.7590],
        'description': ['Point A (Near Camp)', 'Point B (Near Camp)', 'Point C (Near Camp)']
    }
    df = pd.DataFrame(sample_data)
    df.to_csv(file_path, index=False)
    print(f"Sample geodetic data file created at {file_path}")

def load_geodetic_data(file_path):
    """
    Loads geodetic data from a specified CSV file.
    The CSV file must contain 'latitude' and 'longitude' columns.
    If the file doesn't exist, it attempts to create a sample file.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        pandas.DataFrame or None: A DataFrame containing the geodetic data,
                                  or None if loading fails.
    """
    if not os.path.exists(file_path):
        print(f"File {file_path} not found. Creating a sample file...")
        create_sample_file(file_path)
    try:
        data = pd.read_csv(file_path)
        if not {'latitude', 'longitude'}.issubset(data.columns):
            # Ensure critical columns are present before further processing
            raise ValueError("The file must contain 'latitude' and 'longitude' columns.")
        return data
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found even after attempting to create a sample.")
        return None
    except pd.errors.EmptyDataError:
        print(f"Error: The file {file_path} is empty.")
        return None
    except ValueError as ve: # Catch specific ValueError from our check
        print(f"Error loading data: {ve}")
        return None
    except Exception as e: # Catch any other unexpected errors during file loading
        print(f"An unexpected error occurred while loading file {file_path}: {e}")
        return None

def filter_by_proximity(data, reference_point, max_distance_km=MAX_DISTANCE_KM):
    """
    Filters geodetic data points to include only those within a specified
    maximum distance (in kilometers) from a given reference point.

    Args:
        data (pandas.DataFrame): DataFrame containing geodetic data with
                                 'latitude' and 'longitude' columns.
        reference_point (tuple): A tuple (latitude, longitude) for the reference location.
        max_distance_km (float): The maximum distance in kilometers for points to be included.

    Returns:
        pandas.DataFrame: A new DataFrame containing only the filtered points and an
                          additional 'distance_km' column. Returns an empty DataFrame
                          if input data is invalid or no points meet the criteria.
    """
    if data is None or data.empty:
        print("No data provided to filter.")
        return pd.DataFrame()

    if not all(col in data.columns for col in ['latitude', 'longitude']):
        print("Error: Data must contain 'latitude' and 'longitude' columns for proximity filtering.")
        return pd.DataFrame()

    def calculate_distance(row):
        """Calculates distance using geodesic formula, handles potential errors."""
        try:
            # Ensure latitude and longitude are valid numbers before calculation
            lat = float(row['latitude'])
            lon = float(row['longitude'])
            return geodesic(reference_point, (lat, lon)).km
        except (ValueError, TypeError) as e: # Catch errors from invalid lat/lon values or types
            print(f"Warning: Could not calculate distance for row: {row}. Error: {e}. Skipping.")
            return float('inf') # Assign infinity to ensure it's filtered out

    # Apply distance calculation
    data = data.copy() # Work on a copy to avoid SettingWithCopyWarning
    data['distance_km'] = data.apply(calculate_distance, axis=1)

    # Filter data based on calculated distance
    filtered_data = data[data['distance_km'] <= max_distance_km].copy() # Use .copy() for the final slice as well
    return filtered_data

def create_map(data, reference_point, map_file_path='camp_map.html'):
    """
    Creates an HTML map visualizing geodetic points and a reference point using Folium.
    If data is empty, it creates a map with only the reference point.

    Args:
        data (pandas.DataFrame): DataFrame with 'latitude', 'longitude', and optionally
                                 'description' columns for the points to plot.
        reference_point (tuple): A tuple (latitude, longitude) for the central reference marker.
        map_file_path (str): The file path where the HTML map will be saved.

    Returns:
        folium.Map or None: The Folium map object, or None if map creation fails.
    """
    # Determine map center: if data is available, center on mean of points, else on reference_point
    if data is not None and not data.empty and \
       all(col in data.columns for col in ['latitude', 'longitude']) and \
       pd.to_numeric(data['latitude'], errors='coerce').notna().all() and \
       pd.to_numeric(data['longitude'], errors='coerce').notna().all():
        map_center = [data['latitude'].mean(), data['longitude'].mean()]
    else: # Fallback if data is problematic or empty
        map_center = reference_point
        if data is None or data.empty:
            print("No data to plot on map. Map will center on the reference point.")

    camp_map = folium.Map(location=map_center, zoom_start=12)

    # Add a marker for the reference point (camp)
    folium.Marker(
        location=reference_point,
        popup="Student Camp Location",
        tooltip="Student Camp", # Added tooltip for hover
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(camp_map)

    # Add markers for each geodetic point from the filtered data
    if data is not None and not data.empty:
        for _, row in data.iterrows():
            try:
                lat = float(row['latitude'])
                lon = float(row['longitude'])
                folium.Marker(
                    location=(lat, lon),
                    popup=row.get('description', 'Geodetic Point'), # Use .get for safer access to 'description'
                    tooltip=row.get('description', f"Lat: {lat}, Lon: {lon}"), # Added tooltip
                    icon=folium.Icon(color="green", icon="leaf") # Changed icon for points
                ).add_to(camp_map)
            except (ValueError, TypeError) as e:
                print(f"Warning: Could not plot point for row: {row}. Invalid coordinates. Error: {e}")


    # Handle case where data was provided but was empty or invalid for map markers
    if data is not None and data.empty:
         print("Data was empty, so only the reference point is marked on the map.")
    elif data is None: # Explicitly handle if data is None from the start
        # This case is somewhat covered by the initial map_center logic and print,
        # but an explicit marker for "No nearby data" is good if data was expected.
        folium.Marker(
            location=reference_point, # Re-add or ensure reference point marker if map was empty
            popup="Reference Point (No valid data points to display)",
            icon=folium.Icon(color="orange", icon="exclamation-sign")
        ).add_to(camp_map) # This might duplicate if data was None initially. Let's refine.
        # The above logic for empty/None data handling for markers needs to be streamlined.
        # If data is None or empty, the loop for markers won't run.
        # The initial print statement for "No data to plot on map" or "Data was empty" should suffice.
        # The map will be created with just the camp location.

    try:
        camp_map.save(map_file_path)
        print(f"Map saved to {map_file_path}")
        return camp_map
    except Exception as e:
        print(f"Error saving map to {map_file_path}: {e}")
        return None


def main():
    """
    Main function to orchestrate the geodetic data processing workflow.
    It loads data, filters it by proximity to a camp, saves the filtered data,
    and generates a map.
    """
    # Configuration for file paths
    input_csv_file = 'geodetic_data.csv'       # Source data
    filtered_csv_file = 'filtered_geodetic_data.csv' # Output for filtered data
    output_map_file = 'camp_map.html'          # Output for HTML map

    # Load the geodetic data
    geodetic_data = load_geodetic_data(input_csv_file)

    if geodetic_data is None:
        print("Failed to load geodetic data. Cannot proceed with filtering and mapping. Exiting.")
        # Optionally, create a map with only the camp location if data loading fails
        create_map(pd.DataFrame(), CAMP_LOCATION, map_file_path=output_map_file)
        return # Exit if data loading failed

    if geodetic_data.empty:
        print("Geodetic data file was loaded but is empty. No points to filter.")
        # Create a map showing only the camp location
        create_map(geodetic_data, CAMP_LOCATION, map_file_path=output_map_file)
        return # Exit if data is empty

    print("Geodetic data loaded successfully.")

    # Filter data by proximity to the camp
    # MAX_DISTANCE_KM is used by default from global scope
    filtered_data = filter_by_proximity(geodetic_data, CAMP_LOCATION)

    if not filtered_data.empty:
        print(f"Filtered {len(filtered_data)} points within {MAX_DISTANCE_KM} km of the camp.")
        # Save filtered data to a new CSV file
        try:
            filtered_data.to_csv(filtered_csv_file, index=False)
            print(f"Filtered data saved to '{filtered_csv_file}'")
        except Exception as e:
            print(f"Error saving filtered data to {filtered_csv_file}: {e}")
    else:
        print(f"No points found within {MAX_DISTANCE_KM} km of the camp.")

    # Create a map with the (potentially empty) filtered data and camp location
    create_map(filtered_data, CAMP_LOCATION, map_file_path=output_map_file)


if __name__ == "__main__":
    # This ensures main() is called only when the script is executed directly
    main()
