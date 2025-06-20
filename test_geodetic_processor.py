import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import pandas as pd
from pandas.testing import assert_frame_equal
from io import StringIO
import os
import sys

# Assuming geodetic_processor.py is in the same directory or PYTHONPATH is set.
import geodetic_processor

# Define constants that might be used by main() in geodetic_processor
# if they are not explicitly defined at the module level there.
# This makes tests for main() more robust.
DEFAULT_INPUT_CSV_FILE = 'geodetic_data.csv'
DEFAULT_FILTERED_CSV_FILE = 'filtered_geodetic_data.csv'
DEFAULT_OUTPUT_MAP_FILE = 'camp_map.html'


class TestGeodeticProcessor(unittest.TestCase):

    def setUp(self):
        # Common setup for tests
        self.camp_location = geodetic_processor.CAMP_LOCATION # (56.7119, 36.7614)
        self.max_distance = geodetic_processor.MAX_DISTANCE_KM # 5 km
        self.test_csv_file = "test_data.csv" # Used for generic test CSV operations

        # Sample data consistent with geodetic_processor.create_sample_file's structure
        self.sample_data_dict = {
            'latitude':    [56.7110, 56.7130, 56.7150],
            'longitude':   [36.7615, 36.7600, 36.7590],
            'description': ['Point A (Near Camp)', 'Point B (Near Camp)', 'Point C (Near Camp)']
        }
        self.sample_df = pd.DataFrame(self.sample_data_dict)

        # Data for filter_by_proximity tests
        self.proximity_test_data = pd.DataFrame({
            'latitude': [56.7110, 56.7000, 50.0, 56.7120, "invalid_lat", None, 56.710],
            'longitude': [36.7615, 36.7500, 30.0, 36.7600, 36.7800, 36.790, "invalid_lon"],
            'description': ['Point 1 (In)', 'Point 2 (In)', 'Point 3 (Out)', 'Point 4 (In)', 'Point 5 (Invalid Lat)', 'Point 6 (None Lat)', 'Point 7 (Invalid Lon)']
        })


    def tearDown(self):
        # Clean up any files created during tests
        files_to_remove = [
            self.test_csv_file,
            "sample_geodetic_data.csv", # Default name in create_sample_file if path not specific
            DEFAULT_INPUT_CSV_FILE,
            DEFAULT_FILTERED_CSV_FILE,
            DEFAULT_OUTPUT_MAP_FILE,
            "temp_sample_output.csv", # Used in one specific test
            "test_map.html", # Used in create_map tests
            "test_map_with_data.html" # Used in create_map tests
        ]
        for f_path in files_to_remove:
            if os.path.exists(f_path):
                os.remove(f_path)


    # --- Tests for create_sample_file ---
    @patch('pandas.DataFrame.to_csv')
    @patch('builtins.print')
    def test_create_sample_file_calls_to_csv(self, mock_print, mock_to_csv):
        geodetic_processor.create_sample_file(self.test_csv_file)
        # Check that to_csv was called with the correct path and index=False
        mock_to_csv.assert_called_once()
        args, kwargs = mock_to_csv.call_args
        self.assertEqual(args[0], self.test_csv_file) # Path is the first arg to to_csv
        self.assertEqual(kwargs.get('index'), False)

    @patch('builtins.print')
    def test_create_sample_file_actual_creation_and_content(self, mock_print):
        test_file_path = "temp_sample_output.csv"

        geodetic_processor.create_sample_file(test_file_path)
        self.assertTrue(os.path.exists(test_file_path))

        try:
            df = pd.read_csv(test_file_path)
            self.assertFalse(df.empty)
            expected_headers = ['latitude', 'longitude', 'description']
            self.assertListEqual(list(df.columns), expected_headers)
            # Compare with the structure of sample_data_dict used in setUp
            self.assertEqual(len(df), len(self.sample_data_dict['latitude']))
            self.assertEqual(df['description'][0], self.sample_data_dict['description'][0])
        finally:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)

    # --- Tests for load_geodetic_data ---
    @patch('os.path.exists', return_value=True)
    @patch('pandas.read_csv')
    @patch('builtins.print')
    def test_load_valid_data(self, mock_print, mock_read_csv, mock_exists):
        mock_read_csv.return_value = self.sample_df.copy()
        df = geodetic_processor.load_geodetic_data(self.test_csv_file)

        mock_exists.assert_called_once_with(self.test_csv_file)
        mock_read_csv.assert_called_once_with(self.test_csv_file)
        assert_frame_equal(df, self.sample_df)
        relevant_print_calls = [call_args for call_args in mock_print.call_args_list if "Error" in call_args[0][0]]
        self.assertEqual(len(relevant_print_calls), 0)


    @patch('os.path.exists', side_effect=[False, True]) # First call False (by load_geodetic_data), second True (by pd.read_csv after sample created)
    @patch('geodetic_processor.create_sample_file')
    @patch('pandas.read_csv')
    @patch('builtins.print')
    def test_load_data_file_not_found_creates_sample_and_loads(self, mock_print, mock_read_csv, mock_create_sample, mock_exists):
        mock_read_csv.return_value = self.sample_df.copy()

        df = geodetic_processor.load_geodetic_data(self.test_csv_file)

        # os.path.exists is called once by load_geodetic_data.
        # If create_sample_file were the *actual* function, it might call os.path.exists too.
        # However, create_sample_file is mocked.
        # pd.read_csv might internally call os.path.exists too.
        # The side_effect=[False, True] implies we expect two calls *somewhere*.
        # The first call is explicit in load_geodetic_data.
        # The second call would be from pd.read_csv. If it doesn't call os.path.exists, then call_count will be 1.
        # Let's assume for now the original intent was to only count the explicit call in load_geodetic_data.
        # If pd.read_csv *does* call it, and the mock is global, then it would be 2.
        # The previous failure `AssertionError: 1 != 2` means mock_exists.call_count was 1. So, pd.read_csv did not call our mocked os.path.exists
        # or create_sample_file did not.
        self.assertEqual(mock_exists.call_count, 1) # Corrected: only one direct call in the function's logic path for the first check.
        mock_create_sample.assert_called_once_with(self.test_csv_file)
        mock_read_csv.assert_called_once_with(self.test_csv_file) # This is called after create_sample_file
        assert_frame_equal(df, self.sample_df)
        mock_print.assert_any_call(f"File {self.test_csv_file} not found. Creating a sample file...")

    @patch('os.path.exists', return_value=True)
    @patch('pandas.read_csv')
    @patch('builtins.print')
    def test_load_data_missing_columns(self, mock_print, mock_read_csv, mock_exists):
        df_missing_cols = pd.DataFrame({'longitude': [1, 2], 'description': ['A', 'B']})
        mock_read_csv.return_value = df_missing_cols

        result_df = geodetic_processor.load_geodetic_data(self.test_csv_file)

        self.assertIsNone(result_df)
        mock_print.assert_any_call("Error loading data: The file must contain 'latitude' and 'longitude' columns.")

    @patch('os.path.exists', return_value=True)
    @patch('pandas.read_csv', side_effect=pd.errors.EmptyDataError)
    @patch('builtins.print')
    def test_load_data_empty_csv(self, mock_print, mock_read_csv, mock_exists):
        result_df = geodetic_processor.load_geodetic_data(self.test_csv_file)
        self.assertIsNone(result_df)
        mock_print.assert_any_call(f"Error: The file {self.test_csv_file} is empty.")

    @patch('os.path.exists', side_effect=[False, False])
    @patch('geodetic_processor.create_sample_file', MagicMock())
    @patch('pandas.read_csv', side_effect=FileNotFoundError("Mocked FileNotFoundError"))
    @patch('builtins.print')
    def test_load_data_filenotfound_after_sample_creation_attempt(self, mock_print, mock_read_csv, mock_exists):
        result_df = geodetic_processor.load_geodetic_data(self.test_csv_file)
        self.assertIsNone(result_df)
        geodetic_processor.create_sample_file.assert_called_once_with(self.test_csv_file)
        mock_print.assert_any_call(f"Error: The file {self.test_csv_file} was not found even after attempting to create a sample.")

    # --- Tests for filter_by_proximity ---
    def test_filter_points_inside_and_outside_radius(self):
        input_df = self.proximity_test_data.copy()
        input_df_numeric = input_df[
            pd.to_numeric(input_df['latitude'], errors='coerce').notna() &
            pd.to_numeric(input_df['longitude'], errors='coerce').notna()
        ].copy()

        filtered_df = geodetic_processor.filter_by_proximity(input_df_numeric, self.camp_location, self.max_distance)

        self.assertEqual(len(filtered_df), 3)
        self.assertTrue(all(filtered_df['distance_km'] <= self.max_distance))
        expected_descriptions = ['Point 1 (In)', 'Point 2 (In)', 'Point 4 (In)']
        self.assertListEqual(sorted(list(filtered_df['description'])), sorted(expected_descriptions))

    def test_filter_all_points_outside_radius(self):
        far_data = pd.DataFrame({
            'latitude': [10.0, 20.0], 'longitude': [10.0, 20.0], 'description': ['Far A', 'Far B']
        })
        filtered_df = geodetic_processor.filter_by_proximity(far_data, self.camp_location, self.max_distance)
        self.assertTrue(filtered_df.empty)

    def test_filter_all_points_inside_radius(self):
        close_data = pd.DataFrame({
            'latitude': [56.7110, 56.7120], 'longitude': [36.7615, 36.7600], 'description': ['Close A', 'Close B']
        })
        filtered_df = geodetic_processor.filter_by_proximity(close_data.copy(), self.camp_location, self.max_distance)
        self.assertEqual(len(filtered_df), 2)
        assert_frame_equal(filtered_df[['latitude', 'longitude', 'description']].reset_index(drop=True),
                           close_data[['latitude', 'longitude', 'description']].reset_index(drop=True),
                           check_dtype=False)

    def test_filter_empty_input_dataframe(self):
        empty_df = pd.DataFrame(columns=['latitude', 'longitude', 'description'])
        filtered_df = geodetic_processor.filter_by_proximity(empty_df, self.camp_location, self.max_distance)
        self.assertTrue(filtered_df.empty)

    @patch('builtins.print')
    def test_filter_missing_lat_long_columns(self, mock_print):
        df_missing_cols = pd.DataFrame({'description': ['A', 'B']})
        filtered_df = geodetic_processor.filter_by_proximity(df_missing_cols, self.camp_location, self.max_distance)
        self.assertTrue(filtered_df.empty)
        mock_print.assert_any_call("Error: Data must contain 'latitude' and 'longitude' columns for proximity filtering.")

    @patch('builtins.print')
    def test_filter_invalid_coordinate_values_gracefully_handled(self, mock_print):
        input_df = self.proximity_test_data.copy()

        filtered_df = geodetic_processor.filter_by_proximity(input_df, self.camp_location, self.max_distance)

        self.assertEqual(len(filtered_df), 3)
        valid_descriptions = ['Point 1 (In)', 'Point 2 (In)', 'Point 4 (In)']
        self.assertListEqual(sorted(list(filtered_df['description'])), sorted(valid_descriptions))

        printed_output = "".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Warning: Could not calculate distance for row", printed_output)
        self.assertIn("Point 5 (Invalid Lat)", printed_output)
        self.assertIn("Point 6 (None Lat)", printed_output)
        self.assertIn("Point 7 (Invalid Lon)", printed_output)


    # --- Tests for create_map ---
    @patch('folium.Map')
    @patch('folium.Marker')
    @patch('builtins.print')
    def test_create_map_empty_data_creates_map_with_camp_marker(self, mock_print, mock_marker, mock_folium_map):
        mock_map_instance = MagicMock()
        mock_folium_map.return_value = mock_map_instance
        empty_df = pd.DataFrame(columns=['latitude', 'longitude', 'description'])

        geodetic_processor.create_map(empty_df, self.camp_location, "test_map.html")

        mock_folium_map.assert_called_once_with(location=self.camp_location, zoom_start=12)

        camp_marker_found = any(
            call_args.kwargs.get('popup') == "Student Camp Location" and call_args.kwargs.get('location') == self.camp_location
            for call_args in mock_marker.call_args_list
        )
        self.assertTrue(camp_marker_found, "Camp marker not added or details incorrect for empty data map.")

        mock_map_instance.save.assert_called_once_with("test_map.html")


    @patch('folium.Map')
    @patch('folium.Marker')
    @patch('builtins.print')
    def test_create_map_with_data_plots_points_and_camp(self, mock_print, mock_marker, mock_folium_map):
        mock_map_instance = MagicMock()
        mock_folium_map.return_value = mock_map_instance

        data_for_map = self.proximity_test_data[
            self.proximity_test_data['description'].isin(['Point 1 (In)', 'Point 4 (In)'])
        ].copy()
        data_for_map['latitude'] = pd.to_numeric(data_for_map['latitude'])
        data_for_map['longitude'] = pd.to_numeric(data_for_map['longitude'])

        geodetic_processor.create_map(data_for_map, self.camp_location, "test_map_with_data.html")

        expected_map_center = [data_for_map['latitude'].mean(), data_for_map['longitude'].mean()]
        mock_folium_map.assert_called_once_with(location=expected_map_center, zoom_start=12)

        self.assertEqual(mock_marker.call_count, len(data_for_map) + 1)

        camp_marker_found = any(call_args.kwargs.get('popup') == "Student Camp Location" for call_args in mock_marker.call_args_list)
        self.assertTrue(camp_marker_found)

        point_marker_found = any(call_args.kwargs.get('popup') == 'Point 1 (In)' for call_args in mock_marker.call_args_list)
        self.assertTrue(point_marker_found)

        mock_map_instance.save.assert_called_once_with("test_map_with_data.html")

    # --- Test for main function (Integration Style) ---
    @patch('geodetic_processor.load_geodetic_data')
    @patch('geodetic_processor.filter_by_proximity')
    @patch('geodetic_processor.create_map')
    @patch('pandas.DataFrame.to_csv')
    @patch('builtins.print')
    def test_main_function_successful_flow(self, mock_print, mock_to_csv, mock_create_map, mock_filter_by_proximity, mock_load_geodetic_data):
        mock_load_geodetic_data.return_value = self.sample_df.copy()
        filtered_sample_df = self.sample_df.head(1).copy()
        mock_filter_by_proximity.return_value = filtered_sample_df

        geodetic_processor.main()

        mock_load_geodetic_data.assert_called_once_with(DEFAULT_INPUT_CSV_FILE)

        # Corrected assertion for mock_filter_by_proximity
        self.assertEqual(mock_filter_by_proximity.call_count, 1)
        call_args = mock_filter_by_proximity.call_args[0]
        assert_frame_equal(call_args[0], self.sample_df) # Compare DataFrame argument
        self.assertEqual(call_args[1], self.camp_location) # Compare non-DataFrame argument directly

        mock_to_csv.assert_called_once_with(DEFAULT_FILTERED_CSV_FILE, index=False)
        mock_create_map.assert_called_once_with(filtered_sample_df, self.camp_location, map_file_path=DEFAULT_OUTPUT_MAP_FILE)

    @patch('geodetic_processor.load_geodetic_data', return_value=None)
    @patch('geodetic_processor.filter_by_proximity')
    @patch('geodetic_processor.create_map')
    @patch('builtins.print')
    def test_main_function_handles_load_failure(self, mock_print, mock_create_map, mock_filter_by_proximity, mock_load_failure):
        geodetic_processor.main()

        mock_load_failure.assert_called_once_with(DEFAULT_INPUT_CSV_FILE)
        mock_filter_by_proximity.assert_not_called()
        mock_print.assert_any_call("Failed to load geodetic data. Cannot proceed with filtering and mapping. Exiting.")

        mock_create_map.assert_called_once()
        # Check first argument passed to create_map is an empty DataFrame
        self.assertTrue(isinstance(mock_create_map.call_args[0][0], pd.DataFrame))
        self.assertTrue(mock_create_map.call_args[0][0].empty)
        # Check second argument is camp_location
        self.assertEqual(mock_create_map.call_args[0][1], self.camp_location)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
