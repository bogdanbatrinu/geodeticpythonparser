# Geodetic Data Processor and Visualizer

This script processes geodetic data from a CSV file to filter points within a specified radius of a central location and generates an interactive HTML map of these points.

## Purpose

The program is a practical tool for anyone needing to process and visualize geographic data. For example, it can be used to:

*   Analyze nearby resources or facilities.
*   Plan routes or study accessibility.
*   Gain spatial insights for urban planning, geodesy, or environmental studies.

By automating calculations, filtering, and map creation, the program saves time and enhances decision-making with a user-friendly visual output.

## Features

*   **Data Loading:** Loads geodetic data from a CSV file.
*   **Data Validation:** Checks if the input file exists. If not, it generates a sample `geodetic_data.csv` to demonstrate functionality. It also validates that the CSV contains the required 'latitude' and 'longitude' columns.
*   **Proximity Filtering:** Filters geodetic points based on their distance from a defined central location (default: Konakovo, Russia) and within a specified radius (default: 5 km).
*   **Interactive Map Creation:** Generates an HTML map (`camp_map.html`) displaying the central location and all filtered geodetic points with markers and descriptions.
*   **Output Results:** Saves the filtered geodetic data to a new CSV file (`filtered_geodetic_data.csv`).

## Setup and Installation

1.  **Clone the repository (or download the script `geodetic_processor.py`).**
2.  **Install dependencies:**
    The script attempts to install missing dependencies (pandas, geopy, folium) automatically using pip. However, it's recommended to create a virtual environment and install them manually using the provided `requirements.txt` file:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

## Usage

1.  **Prepare your input data:**
    Create a CSV file (e.g., `geodetic_data.csv` in the same directory as the script) with at least 'latitude' and 'longitude' columns. An optional 'description' column can be included for point labels on the map.
    Example `geodetic_data.csv`:
    ```csv
    latitude,longitude,description
    56.7110,36.7615,Point A
    56.7130,36.7600,Point B
    56.7150,36.7590,Point C
    55.0000,37.0000,Far Away Point
    ```
    If `geodetic_data.csv` is not found, a sample file will be created automatically.

2.  **Run the script:**
    ```bash
    python geodetic_processor.py
    ```

3.  **Outputs:**
    *   `filtered_geodetic_data.csv`: Contains the data points that fall within the specified radius.
    *   `camp_map.html`: An interactive HTML map that can be opened in any web browser.
    *   Console output: The script will print information about its progress, including data loading, filtering, and file saving.

## Configuration

The following parameters can be modified directly at the top of the `geodetic_processor.py` script:

*   `CAMP_LOCATION`: A tuple `(latitude, longitude)` for the central reference point. Default: `(56.7119, 36.7614)` (Konakovo, Russia).
*   `MAX_DISTANCE_KM`: An integer or float representing the maximum distance in kilometers for filtering points around the `CAMP_LOCATION`. Default: `5`.
*   Input/output file names can also be changed within the `main()` function if needed.

## Running Tests

Unit tests are provided in `test_geodetic_processor.py`. To run them:
```bash
python -m unittest test_geodetic_processor.py
```
