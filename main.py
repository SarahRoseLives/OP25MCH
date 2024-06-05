from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.properties import StringProperty
from kivy.clock import Clock, mainthread
from kivy.core.text import LabelBase
from kivy.uix.spinner import Spinner
from kivy.utils import platform
from plyer import gps
import time
import re

# Local Imports
from updater import OP25Client
from resources.config import configure

# Load config file
config = configure.Configure('resources/config/config.ini')

TIME24 = config.get_bool(section='RCH', option='TIME24')
darkmode_checkbox = config.get_bool(section='RCH', option='darkmode_checkbox')
GLOBAL_OP25IP = config.get(section='RCH', option='op25_ip')
GLOBAL_OP25PORT = config.get(section='RCH', option='op25_port')
GLOBAL_TAGS_ENABLED = False


class MainApp(MDApp):
    time_text = StringProperty()
    signal_icon = StringProperty()
    op25_server_address = StringProperty()

    # GPS Stuff
    gps_location = StringProperty()
    gps_status = StringProperty('Click Start to get GPS location updates')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.op25client = OP25Client(f'http://{GLOBAL_OP25IP}:{GLOBAL_OP25PORT}', self.process_latest_values)
        self.is_active = False  # Flag to control data fetching
        self.sdr_info = "SDR: RTL | LNA: 48 | SR: 2.e6"  # Initialize the property

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


    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Purple"
        root = Builder.load_file("main.kv")

        # Load our fonts
        LabelBase.register("digital", "resources/fonts/digital.ttf")
        LabelBase.register("material", "resources/fonts/material.ttf")

        self.system_county_label = root.ids.system_county

        # Update stuff using clocks to prevent UI blcoking
        Clock.schedule_once(self.initialize_settings, 0.1)
        Clock.schedule_once(self.delayed_theme_application)
        Clock.schedule_interval(self.update_time, 1)
        Clock.schedule_interval(self.check_status_and_update, 5)

        # This is the updater thread and it runs constant queries to OP25
        self.start_thread()

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


        return root


    # The dark theme is set after the UI loads and is done once on a clock
    def delayed_theme_application(self, dt):
        self.theme_cls.theme_style = "Dark"
        # Load OP25 Settings with the theme delay
        self.read_op25_settings()


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

    # Update config for local settings
    def update_config(self):
        config.set('RCH', 'TIME24', str(self.root.ids.time24_checkbox.active))
        config.set('RCH', 'op25_ip', self.root.ids.op25_ip_textbox.text)
        config.set('RCH', 'op25_port', self.root.ids.op25_port_textbox.text)
        config.set('RCH', 'mch_port', self.root.ids.mch_port_textbox.text)
        config.set('RCH', 'darkmode_checkbox', str(self.root.ids.time24_checkbox.active))


    # Update OP25 Specific settings
    def update_op25_settings(self):
        # Save the SDR Selection to Config.ini
        config.set('SDR', 'sdr', self.root.ids.sdr_spinner.text)
        # Save the SDR Sample Rate to Config.ini
        config.set('SDR', 'samplerate', self.root.ids.sample_rate_spinner.text)
        # Save the SDR gain to Config.ini
        config.set('SDR', 'gain', self.root.ids.gain_spinner.text)

        sysname = self.root.ids.op25_config_sysname.text
        cclist = self.root.ids.op25_config_controlchannels.text
        tglist = self.root.ids.op25_config_talkgroup_list.text

        # Take data in the trunk settings fields and send them to the server for updating
        self.op25client.send_cmd_to_op25(command=f'WRITE_TRUNK;sysname={sysname};cclist={cclist};tglist={tglist}')


    # Read OP25 specific settings
    def read_op25_settings(self):
        # Update UI With SDR Selection from Config.ini
        self.root.ids.sdr_spinner.text = config.get('SDR', 'sdr')
        # Update UI With SDR Sample Rate from Config.ini
        self.root.ids.sample_rate_spinner.text = config.get('SDR', 'samplerate')
        # Update UI With SDR gain from Config.ini
        self.root.ids.gain_spinner.text = config.get('SDR', 'gain')

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
            self.root.ids.op25_config_sysname.text = sysname
            self.root.ids.op25_config_controlchannels.text = cclist
            self.root.ids.op25_config_talkgroup_list.text = tglist
        else:
            print("ERROR: Unable to read trunk from server")

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
        self.root.ids.op25_ip_textbox.text = config.get(section='RCH', option='op25_ip')
        self.root.ids.op25_port_textbox.text = config.get(section='RCH', option='op25_port')
        self.root.ids.mch_port_textbox.text = config.get(section='RCH', option='mch_port')
        self.root.ids.time24_checkbox.active = config.get_bool(section='RCH', option='TIME24')
        self.root.ids.darkmode_checkbox.text = config.get(section='RCH', option='darkmode_checkbox')



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
                        self.root.ids.current_talkgroup.text = str(current_talkgroup)
                        self.add_log_entry(str(current_talkgroup))
                    else:
                        self.root.ids.current_talkgroup.text = "No Active Call"

                    if system_name is not None:
                        self.root.ids.system_name.text = system_name
                else:
                    self.root.ids.current_talkgroup.text = "No Active Call"
            else:
                if latest_values is not None and 'trunk_update' in latest_values:
                    system_name = latest_values['change_freq'].get('system')
                    current_talkgroup = latest_values['change_freq'].get('tgid')

                    active_tgids = []
                    for freq, freq_data in latest_values['trunk_update']['frequency_data'].items():
                        active_tgids.extend(filter(None, freq_data['tgids']))

                    if system_name is not None:
                        self.root.ids.system_name.text = system_name
                    if current_talkgroup is not None:
                        if int(current_talkgroup) in active_tgids:
                            self.root.ids.current_talkgroup.text = str(current_talkgroup)
                            self.add_log_entry(str(current_talkgroup))
                        else:
                            self.root.ids.current_talkgroup.text = "No Active Call"
                else:
                    self.root.ids.current_talkgroup.text = "No Active Call"
        except Exception as e:
            print(f"Error updating large display: {e}")

    def update_connection_status(self):
        status = self.root.ids.connected_msg.text
        if self.op25client.connection_successful:
            if 'not connected' in status.lower():
                self.root.ids.connected_msg.text = 'Connected to: OP25'
                self.add_log_entry('Connected to: OP25')

                # Update the SDR Info on Display
                sdr = config.get(section='SDR', option='sdr')
                gain = str(config.get(section='SDR', option='gain'))
                sr = str(config.get(section='SDR', option='samplerate'))

                self.sdr_info = f"SDR: {sdr} | LNA: {gain} | SR: {sr}"
        else:
            if 'Connected to: OP25' in status:
                self.root.ids.connected_msg.text = 'Connecting...'
            if 'Connecting...' in status:
                self.root.ids.connected_msg.text = 'Not Connected'
                self.add_log_entry('OP25 Connection Lost')

    def process_latest_values(self, latest_values):
        Clock.schedule_once(lambda dt: self.update_signal_icon(latest_values))
        Clock.schedule_once(lambda dt: self.update_large_display(latest_values))

    def add_log_entry(self, text):
        log_box = self.root.ids.log_box
        stamped_text = f'{time.time()}: {text}'
        new_label = Label(text=stamped_text, font_size='20sp', size_hint_y=None,
                          height=self.calculate_text_height(stamped_text))
        log_box.add_widget(new_label)
        # Adjust the height of the log_box to accommodate the new entry
        log_box.height = sum(child.height for child in log_box.children)
        self.root.ids.log_scrollview.scroll_y = 1  # Scroll to the top

    @staticmethod
    def calculate_text_height(text):
        # Calculate the height required for the text
        label = Label(text=text)
        label.texture_update()
        return label.texture_size[1]

    # More GPS Functions
    def start(self, minTime, minDistance):
        gps.start(minTime, minDistance)

    def stop(self):
        gps.stop()

    @mainthread
    def on_location(self, **kwargs):
        self.gps_location = '\n'.join([
            '{}={}'.format(k, v) for k, v in kwargs.items()])

    @mainthread
    def on_status(self, stype, status):
        self.gps_status = 'type={}\n{}'.format(stype, status)

    def on_pause(self):
        gps.stop()
        return True

    def on_resume(self):
        gps.start(1000, 0)
        pass


if __name__ == '__main__':
    app = MainApp()
    app.run()
