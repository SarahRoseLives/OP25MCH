'''### NOTES ###

radioreference.py requires zeep which requires lxml which requires
sudo apt-get install libxml2-dev libxslt-dev
in your build environment

buildozer requires
sudo apt install cython buildozer


#############'''

import configparser
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.properties import StringProperty
from kivy.clock import Clock, mainthread
from kivy.core.text import LabelBase
from kivy.uix.spinner import Spinner
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivy.utils import platform
from threading import Thread
from plyer import gps
import sqlite3
import time
import re
import os

from kivy.uix.screenmanager import Screen
import csv
from math import radians, sin, cos, sqrt, atan2

import updater
# Local Imports
from updater import OP25Client
from resources.config import configure
from radioreference import GetSystems

# Load config file
config = configure.Configure('resources/config/config.ini')

TIME24 = config.get_bool(section='RCH', option='TIME24')
darkmode_checkbox = config.get_bool(section='RCH', option='darkmode_checkbox')

# Define global variables
GLOBAL_lat = None
GLOBAL_lon = None
GLOBAL_nearest_zip = None
GLOBAL_OP25IP = config.get(section='RCH', option='op25_ip')
GLOBAL_OP25PORT = config.get(section='RCH', option='op25_port')
GLOBAL_TAGS_ENABLED = False

# Screen Classes

# Our Main Screen
class Main(Screen):
    pass

class SettingsLocalConfig(Screen):
    pass

class SettingsOP25Config(Screen):
    pass

class SettingsScanGridConfig(Screen):
    pass

# Our Credentials screen for settings
class SettingsRRCredentials(Screen):
    # Stuff to do when entering this screen
    def on_enter(self):
        self.load_rr_credentials()

    # Load our credentials into the screen
    def load_rr_credentials(self):
        config_path = 'resources/config/rr_credentials.ini'

        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            config.read(config_path)

            if config.has_section('RadioReference'):
                username = config.get('RadioReference', 'username', fallback='')
                password = config.get('RadioReference', 'password', fallback='')

                self.ids.username.text = username
                self.ids.password.text = password
            else:
                print("Section 'RadioReference' not found in the config file.")
        else:
            print("Config file not found.")

class SettingsRRImport(Screen):
    pass

class SettingsRRSelect(Screen):
    pass

class MainApp(MDApp):
    time_text = StringProperty()
    signal_icon = StringProperty()
    op25_server_address = StringProperty()

    # GPS Stuff
    gps_location = StringProperty()
    gps_status = StringProperty('Click Start to get GPS location updates')

    zip_code_data = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.op25client = OP25Client(f'http://{GLOBAL_OP25IP}:{GLOBAL_OP25PORT}', self.process_latest_values)
        self.is_active = False  # Flag to control data fetching
        self.sdr_info = "SDR: RTL | LNA: 48 | SR: 2.e6"  # Initialize the property
        self.previous_site_id = None

        # Spinners are the drop down boxes we use
        self.sdr_spinner = Spinner(
            text="Choose an SDR",
            values=["RTL-SDR", "SDRplay", "HackRF", "Other"],
            size_hint_y=None,
            height="40dp"
        )
        self.sdr_spinner.bind(text=self.on_sdr_selection)

        self.sample_rate_spinner = Spinner(
            text="Choose a sample rate",
            values=["1.4msps", "2.6msps"],
            size_hint_y=None,
            height="40dp"
        )
        self.sample_rate_spinner.bind(text=self.on_sample_rate_selection)

        self.gain_spinner = Spinner(
            text="Choose a gain",
            values=[str(i) for i in range(10, 51, 2)],
            size_hint_y=None,
            height="40dp"
        )
        self.gain_spinner.bind(text=self.on_gain_selection)

    def populate_system_selection_spinner(self):
        # Define the path to the directory containing the .db files
        systems_directory = 'resources/systems/'

        # Ensure the directory exists and is accessible
        if not os.path.exists(systems_directory):
            print(f"Directory does not exist: {systems_directory}")
        else:
            try:
                # Get the list of .db files and extract the numeric parts
                system_ids = [
                    os.path.splitext(file)[0]
                    for file in os.listdir(systems_directory)
                    if file.endswith('.db')
                ]

                # Convert to integers for sorting, then back to strings
                system_ids = sorted(system_ids, key=int)

                print("System IDs:", system_ids)

                self.root.get_screen('SettingsRRSelect').ids.systems_spinner.values = system_ids # Update spinner values

            except Exception as e:
                print(f"Error accessing directory: {e}")



    dialog = None
    def build(self):
        #self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Orange"
        root = Builder.load_file("main.kv")


        # Load our fonts
        LabelBase.register("digital", "resources/fonts/digital.ttf")
        LabelBase.register("material", "resources/fonts/material.ttf")

        self.system_county_label = root.get_screen('Main').ids.system_county


        # Update stuff using clocks to prevent UI blcoking
        Clock.schedule_once(self.initialize_settings, 0.1)
        Clock.schedule_once(self.delayed_theme_application)
        Clock.schedule_interval(self.update_time, 1)
        Clock.schedule_interval(self.check_status_and_update, 5)

        Clock.schedule_once(lambda dt: self.populate_system_selection_spinner(), 0.1)




        # This is for our GPS
        try:
            gps.configure(on_location=self.on_location,
                          on_status=self.on_status)
        except NotImplementedError:
            import traceback
            traceback.print_exc()
            self.gps_status = 'GPS is not implemented for your platform'

        if platform == "android":
            print("gps.py: Android detected. Requesting permissions")
            self.request_android_permissions()
            self.load_zip_code_data()


        return root

    def on_start(self):
        # This is the updater thread and it runs constant queries to OP25
        self.start_thread()



        # The dark theme is set after the UI loads and is done once on a clock
    def delayed_theme_application(self, dt):
        self.theme_cls.theme_style = "Dark"
        # Load OP25 Settings with the theme delay
        self.read_op25_settings()
        '''
        if platform == "android":
            # Start GPS Thread
            self.start(1000, 0)
        '''

    # GPS Permissons for android
    def request_android_permissions(self):
        """
        Since API 23, Android requires permission to be requested at runtime.
        This function requests permission and handles the response via a
        callback.

        The request will produce a popup if permissions have not already been
        been granted, otherwise it will do nothing.
        """
        from android.permissions import request_permissions, Permission

        def callback(permissions, results):
            """
            Defines the callback to be fired when runtime permission
            has been granted or denied. This is not strictly required,
            but added for the sake of completeness.
            """
            if all([res for res in results]):
                print("callback. All permissions granted.")
            else:
                print("callback. Some permissions refused.")

        request_permissions([Permission.ACCESS_COARSE_LOCATION,
                             Permission.ACCESS_FINE_LOCATION], callback)


    # Gain spinner / dropdown
    def on_gain_selection(self, spinner, text):
        # Do something when the user selects a gain
        print(f"Selected gain: {text}")

    # Selected System spinner /dropdown

    def on_system_selection(self, spinner, text):
        # Do something when the user selects a gain
        print(f"Selected system: {text}")

    # Samplerate Spinner / Dropdown
    def on_sample_rate_selection(self, spinner, text):
        if text == "1.4msps":
            sample_rate = 1.e4
        elif text == "2.6msps":
            sample_rate = 2.e6
        # Do something with the selected sample rate
        print(f"Selected sample rate: {sample_rate}")

    # SDR Selection Spinner / Dropdown
    def on_sdr_selection(self, spinner, text):
        # Do something when the user selects an SDR option
        print(f"Selected SDR: {text}")

    def test_site_switching(self, system_id):
        # Start the GPS service
        self.start(1000, 0)

    def update_rr_selected_system(self, selected_system):
        config.set('RR', 'selected_system', selected_system)


    def update_rr_import_spinner(self, zipcode):
        # Read the configuration file
        self.config.read('resources/config/rr_credentials.ini')

        # Get the username and password
        username = self.config.get('RadioReference', 'username')
        password = self.config.get('RadioReference', 'password')

        client = GetSystems(username=username, password=password)

        systems = client.get_systems_in_county(zip_code=zipcode)
        print(systems)

        # Update spinner values with system IDs and names
        self.root.get_screen('SettingsRRImport').ids.import_system_spinner.values = [f"System ID: {system['sid']}, Name: {system['sName']}" for system in systems]

        # Make the spinner visible in the UI
        self.root.get_screen('SettingsRRImport').ids.import_system_spinner.opacity = 1

        # Make the download system button visible in UI
        self.root.get_screen('SettingsRRImport').ids.download_system_button.opacity = 1

    def download_rr_system(self, selection):

        if not self.dialog:
            self.dialog = MDDialog(text="SYSTEM CREATION STARTED")
        self.dialog.open()

        def run():
            # Regular expression pattern to extract the system ID
            pattern = r'System ID: (\d+),'

            # Using re.findall to find all matches of the pattern in the input string
            matches = re.findall(pattern, selection)

            # Extract the system ID (assuming there's only one match)
            if matches:
                system_id = matches[0]
                # Read the configuration file
                self.config.read('resources/config/rr_credentials.ini')

                # Get the username and password
                username = self.config.get('RadioReference', 'username')
                password = self.config.get('RadioReference', 'password')

                client = GetSystems(username=username, password=password)

                client.create_system_database(system_id)

                print('Creating System on Pi')
                self.op25client.send_cmd_to_op25(f'CREATE_SYSTEM;{username};{password};{system_id}')

                print(f"System ID extracted: {system_id}")
            else:
                print("System ID not found.")

        # Create a thread for the run function
        thread = Thread(target=run)
        # Start the thread
        thread.start()

    # Update config for local settings
    def update_config(self):
        config.set('RCH', 'TIME24', str(self.root.get_screen('SettingsLocalConfig').ids.time24_checkbox.active))
        config.set('RCH', 'op25_ip', self.root.get_screen('SettingsLocalConfig').ids.op25_ip_textbox.text)
        config.set('RCH', 'op25_port', self.root.get_screen('SettingsLocalConfig').ids.op25_port_textbox.text)
        config.set('RCH', 'mch_port', self.root.get_screen('SettingsLocalConfig').ids.mch_port_textbox.text)
        config.set('RCH', 'darkmode_checkbox', str(self.root.get_screen('SettingsLocalConfig').ids.time24_checkbox.active))


    # Update OP25 Specific settings
    def update_op25_settings(self):
        # Save the SDR Selection to Config.ini
        config.set('SDR', 'sdr', self.root.get_screen('SettingsOP25Config').ids.sdr_spinner.text)
        # Save the SDR Sample Rate to Config.ini
        config.set('SDR', 'samplerate', self.root.get_screen('SettingsOP25Config').ids.sample_rate_spinner.text)
        # Save the SDR gain to Config.ini
        config.set('SDR', 'gain', self.root.get_screen('SettingsOP25Config').ids.gain_spinner.text)
        # Save the manual start on boot option
        is_active = not self.root.get_screen('SettingsOP25Config').ids.manual_on_boot.active
        config.set('SDR', 'manualonboot', is_active)

        sysname = self.root.get_screen('SettingsOP25Config').ids.op25_config_sysname.text
        cclist = self.root.get_screen('SettingsOP25Config').ids.op25_config_controlchannels.text
        tglist = self.root.get_screen('SettingsOP25Config').ids.op25_config_talkgroup_list.text

        # Take data in the trunk settings fields and send them to the server for updating
        self.op25client.send_cmd_to_op25(command=f'WRITE_TRUNK;sysname={sysname};cclist={cclist};tglist={tglist}')





    # Read OP25 specific settings
    def read_op25_settings(self):
        # Update UI With SDR Selection from Config.ini
        self.root.get_screen('SettingsOP25Config').ids.sdr_spinner.text = config.get('SDR', 'sdr')
        # Update UI With SDR Sample Rate from Config.ini
        self.root.get_screen('SettingsOP25Config').ids.sample_rate_spinner.text = config.get('SDR', 'samplerate')
        # Update UI With SDR gain from Config.ini
        self.root.get_screen('SettingsOP25Config').ids.gain_spinner.text = config.get('SDR', 'gain')

        # Update Large Display SDR Details

        # send a command to read trunk file and assign it to variable trunk_data
        trunk_data = self.op25client.send_cmd_to_op25('READ_TRUNK')

        # Regex pattern to extract sysname, cclist, and tglist
        pattern = r"sysname=([^;]*);cclist=([^;]*);tglist=([^;]*)"
        # Perform regex search
        match = re.search(pattern, trunk_data)
        if match:
            sysname = match.group(1)
            cclist = match.group(2)
            tglist = match.group(3)
            if 'tsv' in tglist:
                global GLOBAL_TAGS_ENABLED  # Declare global before assigning
                GLOBAL_TAGS_ENABLED = True
            else:
                GLOBAL_TAGS_ENABLED = False

            # Set trunk details in the UI
            self.root.get_screen('SettingsOP25Config').ids.op25_config_sysname.text = sysname
            self.root.get_screen('SettingsOP25Config').ids.op25_config_controlchannels.text = cclist
            self.root.get_screen('SettingsOP25Config').ids.op25_config_talkgroup_list.text = tglist
        else:
            print("ERROR: Unable to read trunk from server")


    # Save Radio Refernce Credentials
    def save_rr_credentials(self):
        # Retrieve the credentials from the screen
        username = self.root.get_screen('SettingsRRCredentials').ids.username.text
        password = self.root.get_screen('SettingsRRCredentials').ids.password.text

        # Path to the config file
        config_path = 'resources/config/rr_credentials.ini'

        # Ensure the config directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Create a ConfigParser object
        config = configparser.ConfigParser()

        # Read existing config if the file exists
        if os.path.exists(config_path):
            config.read(config_path)

        # Update or set the credentials in the 'RadioReference' section
        if not config.has_section('RadioReference'):
            config.add_section('RadioReference')

        config.set('RadioReference', 'username', username)
        config.set('RadioReference', 'password', password)

        # Write the config to the file
        with open(config_path, 'w') as configfile:
            config.write(configfile)

        # Return to main screen
        self.root.current = 'Main'

    # Increase and decrease volume commands
    def increase_volume(self):
        self.op25client.send_cmd_to_op25(command="INCREASE_VOLUME")
    def decrease_volume(self):
        self.op25client.send_cmd_to_op25(command="DECREASE_VOLUME")

    def start_thread(self):
        if not self.op25client.is_running():
            self.op25client.start()
            self.is_active = True

    def stop_thread(self):
        if self.op25client.is_running():
            self.op25client.stop()
            self.is_active = False


    def initialize_settings(self, *args):
        self.root.get_screen('SettingsLocalConfig').ids.op25_ip_textbox.text = config.get(section='RCH', option='op25_ip')
        self.root.get_screen('SettingsLocalConfig').ids.op25_port_textbox.text = config.get(section='RCH', option='op25_port')
        self.root.get_screen('SettingsLocalConfig').ids.mch_port_textbox.text = config.get(section='RCH', option='mch_port')
        self.root.get_screen('SettingsLocalConfig').ids.time24_checkbox.active = config.get_bool(section='RCH', option='TIME24')
        self.root.get_screen('SettingsLocalConfig').ids.darkmode_checkbox.text = config.get(section='RCH', option='darkmode_checkbox')

        # Get the boolean value
        manual_on_boot_active = config.get_bool('SDR', 'manualonboot')

        # Set the active state of our switch
        self.root.get_screen('SettingsOP25Config').ids.manual_on_boot.active = manual_on_boot_active

        # Start manual op25 if value is true
        if manual_on_boot_active:
            print("Manual on boot is enabled")
            self.op25client.manual_start_op25()

    def update_time(self, *args):
        if TIME24:
            self.time_text = time.strftime("%H:%M:%S")
        else:
            self.time_text = time.strftime("%I:%M:%S %p")

    def check_status_and_update(self, *args):
        if self.is_active and self.op25client.is_running():
            latest_values = self.op25client.get_latest_values()
            self.update_signal_icon(latest_values)
            self.update_large_display(latest_values)
            self.update_connection_status()

    def update_signal_icon(self, latest_values):
        try:
            if latest_values and 'trunk_update' in latest_values:
                tsbks_value = latest_values['trunk_update'].get('tsbks')
                if tsbks_value is None:
                    self.signal_icon = "󰞃"
                else:
                    if int(tsbks_value) < 40:
                        self.signal_icon = "󰞃"
                    elif int(tsbks_value) >= 10000:
                        self.signal_icon = "󰢾"
                    elif int(tsbks_value) >= 2000:
                        self.signal_icon = "󰢽"
                    elif int(tsbks_value) >= 400:
                        self.signal_icon = "󰢼"
                    else:
                        self.signal_icon = "󰞃"
        except Exception as e:
            print(f"Error updating signal icon: {e}")

    def update_large_display(self, latest_values):
        try:
            if GLOBAL_TAGS_ENABLED:
                if latest_values is not None and 'trunk_update' in latest_values:
                    system_name = latest_values['change_freq'].get('system')
                    current_talkgroup = latest_values['change_freq'].get('tag')

                    # Check if current_talkgroup is an empty string
                    if current_talkgroup != "":
                        self.root.get_screen('Main').ids.current_talkgroup.text = str(current_talkgroup)
                        self.add_log_entry(str(current_talkgroup))
                    else:
                        self.root.get_screen('Main').ids.current_talkgroup.text = "No Active Call"

                    if system_name is not None:
                        self.root.get_screen('Main').ids.system_name.text = system_name
                else:
                    self.root.get_screen('Main').ids.current_talkgroup.text = "No Active Call"
            else:
                if latest_values is not None and 'trunk_update' in latest_values:
                    system_name = latest_values['change_freq'].get('system')
                    current_talkgroup = latest_values['change_freq'].get('tgid')

                    active_tgids = []
                    for freq, freq_data in latest_values['trunk_update']['frequency_data'].items():
                        active_tgids.extend(filter(None, freq_data['tgids']))

                    if system_name is not None:
                        self.root.get_screen('Main').ids.system_name.text = system_name
                    if current_talkgroup is not None:
                        if int(current_talkgroup) in active_tgids:
                            self.root.get_screen('Main').ids.current_talkgroup.text = str(current_talkgroup)
                            self.add_log_entry(str(current_talkgroup))
                        else:
                            self.root.get_screen('Main').ids.current_talkgroup.text = "No Active Call"
                else:
                    self.root.get_screen('Main').ids.current_talkgroup.text = "No Active Call"
        except Exception as e:
            print(f"Error updating large display: {e}")

    def update_connection_status(self):
        status = self.root.get_screen('Main').ids.connected_msg.text
        if self.op25client.connection_successful:
            if 'not connected' in status.lower():
                self.root.get_screen('Main').ids.connected_msg.text = 'Connected to: OP25'
                self.add_log_entry('Connected to: OP25')

                # Update the SDR Info on Display
                sdr = config.get(section='SDR', option='sdr')
                gain = str(config.get(section='SDR', option='gain'))
                sr = str(config.get(section='SDR', option='samplerate'))

                self.sdr_info = f"SDR: {sdr} | LNA: {gain} | SR: {sr}"
        else:
            if 'Connected to: OP25' in status:
                self.root.get_screen('Main').ids.connected_msg.text = 'Connecting...'
            if 'Connecting...' in status:
                self.root.get_screen('Main').ids.connected_msg.text = 'Not Connected'
                self.add_log_entry('OP25 Connection Lost')

    def process_latest_values(self, latest_values):
        Clock.schedule_once(lambda dt: self.update_signal_icon(latest_values))
        Clock.schedule_once(lambda dt: self.update_large_display(latest_values))

    def add_log_entry(self, text):
        log_box = self.root.get_screen('Main').ids.log_box
        stamped_text = f'{time.time()}: {text}'
        new_label = Label(text=stamped_text, font_size='20sp', size_hint_y=None,
                          height=self.calculate_text_height(stamped_text))
        log_box.add_widget(new_label)
        # Adjust the height of the log_box to accommodate the new entry
        log_box.height = sum(child.height for child in log_box.children)
        self.root.get_screen('Main').ids.log_scrollview.scroll_y = 1  # Scroll to the top

    @staticmethod
    def calculate_text_height(text):
        # Calculate the height required for the text
        label = Label(text=text)
        label.texture_update()
        return label.texture_size[1]


    def gps_zipcode(self):
        print('DEBUG: You\'re not running android!')
        if platform == "android":
            # Start GPS Thread
            self.start(1000, 0)
            print(f'TEST: {GLOBAL_lon} {GLOBAL_lon} {GLOBAL_nearest_zip}')

        if GLOBAL_lat is not None and GLOBAL_lon is not None:
            nearest_zip = self.find_nearest_zip_code(GLOBAL_lat, GLOBAL_lon)
            self.root.get_screen('SettingsRRImport').ids.zipcode.text = f"{nearest_zip}"

            self.stop()


    def load_zip_code_data(self):
        with open('resources/uszips.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                self.zip_code_data.append({
                    'zip': row['zip'],
                    'lat': float(row['lat']),
                    'lng': float(row['lng'])
                })

    def find_nearest_zip_code(self, lat, lng):
        nearest_zip = None
        min_distance = float('inf')

        for data in self.zip_code_data:
            zip_lat = data['lat']
            zip_lng = data['lng']
            distance = self.calculate_distance(lat, lng, zip_lat, zip_lng)
            if distance < min_distance:
                min_distance = distance
                nearest_zip = data['zip']

        return nearest_zip

    def calculate_distance(self, lat1, lng1, lat2, lng2):
        R = 6371.0  # Radius of the Earth in kilometers

        lat1_rad = radians(lat1)
        lng1_rad = radians(lng1)
        lat2_rad = radians(lat2)
        lng2_rad = radians(lng2)

        dlng = lng2_rad - lng1_rad
        dlat = lat2_rad - lat1_rad

        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c
        return distance

    # Function to calculate the distance between two GPS coordinates using Haversine formula
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        # Radius of Earth in kilometers. Use 3956 for miles
        r = 6371
        return r * c

    # Function to find the nearest site in the SQLite database
    def find_nearest_site(self, current_lat, current_lon):
        system_id = config.get(section='RR', option='selected_system')
        conn = sqlite3.connect(f'resources/systems/{system_id}.db')
        cursor = conn.cursor()
        # Query to get all site details
        cursor.execute("SELECT site_id, latitude, longitude, site_county FROM sites")
        sites = cursor.fetchall()
        nearest_site = None
        min_distance = float('inf')
        for site in sites:
            site_id, site_lat, site_lon, site_county = site
            # Calculate the distance from current location
            distance = self.haversine_distance(current_lat, current_lon, site_lat, site_lon)
            if distance < min_distance:
                min_distance = distance
                nearest_site = site
        conn.close()
        return nearest_site

    # More GPS Functions
    def start(self, minTime, minDistance):
        gps.start(minTime, minDistance)

    def stop(self):
        gps.stop()

    @mainthread
    def on_location(self, **kwargs):
        global GLOBAL_lat, GLOBAL_lon, GLOBAL_nearest_zip

        # Update global variables
        GLOBAL_lat = kwargs.get('lat', None)
        GLOBAL_lon = kwargs.get('lon', None)

        lat = GLOBAL_lat
        lon = GLOBAL_lon
        #lat = kwargs.get('lat', None)
        #lon = kwargs.get('lon', None)
        speed = kwargs.get('speed', None)
        bearing = kwargs.get('bearing', None)
        altitude = kwargs.get('altitude', None)
        accuracy = kwargs.get('accuracy', None)

        self.root.get_screen('Main').ids.lat.text = f"lat: {lat}"
        self.root.get_screen('Main').ids.lon.text = f"lon: {lon}"
        self.root.get_screen('Main').ids.speed.text = f"speed: {speed}"
        self.root.get_screen('Main').ids.bearing.text = f"bearing: {bearing}"
        self.root.get_screen('Main').ids.altitude.text = f"altitude: {altitude}"
        self.root.get_screen('Main').ids.accuracy.text = f"accuracy: {accuracy}"



        if lat is not None and lon is not None:
            nearest_zip = self.find_nearest_zip_code(lat, lon)
            self.root.get_screen('Main').ids.nearest_zip.text = f"Nearest ZIP: {nearest_zip}"
            try:

                system_id = config.get(section='RR', option='selected_system')

                nearest_site_name = self.find_nearest_site(lat, lon)[3]
                nearest_site_id = self.find_nearest_site(lat, lon)[0]

                # Check if the site id has changed
                if nearest_site_id != self.previous_site_id:
                    # Call your function
                    self.op25client.send_cmd_to_op25(f'START_SYSTEM;{nearest_site_id};{system_id}')

                    # Update the previous site id
                    self.previous_site_id = nearest_site_id

                self.root.get_screen('Main').ids.nearest_site.text = f"Nearest Site: {self.find_nearest_site(lat, lon)}"
                self.root.get_screen('Main').ids.system_county.text = nearest_site_name

            except:
                print(f'DEBUG: No database')

    @mainthread
    def on_status(self, stype, status):
        self.gps_status = 'type={}\n{}'.format(stype, status)

    def on_pause(self):
        gps.stop()
        return True

    def on_resume(self):
        gps.start(1000, 0)
        pass

    # Go back to main screen
    def back_to_main(self):
        self.root.current = 'Main'


if __name__ == '__main__':
    app = MainApp()
    app.run()
