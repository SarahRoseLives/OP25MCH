from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.core.text import LabelBase
from random import random
import time
import re

import updater
# Import the OP25Client class
from updater import OP25Client

# Local imports
from resources.config import configure

config = configure.Configure('resources/config/config.ini')

TIME24 = config.get_bool(section='RCH', option='TIME24')
darkmode_checkbox = config.get_bool(section='RCH', option='darkmode_checkbox')
GLOBAL_OP25SERVER = config.get(section='RCH', option='OP25_SERVER')

class MainApp(MDApp):
    time_text = StringProperty()
    signal_icon = StringProperty()
    op25_server_address = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.op25client = OP25Client(GLOBAL_OP25SERVER, self.process_latest_values)
        self.is_active = False  # Flag to control data fetching

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Purple"
        root = Builder.load_file("main.kv")
        LabelBase.register("digital", "resources/fonts/digital.ttf")
        LabelBase.register("material", "resources/fonts/material.ttf")
        self.system_county_label = root.ids.system_county

        Clock.schedule_once(self.initialize_settings, 0.1)
        Clock.schedule_once(self.delayed_theme_application)
        Clock.schedule_interval(self.update_time, 1)
        Clock.schedule_interval(self.check_status_and_update, 5)

        self.start_thread()

        return root

    def delayed_theme_application(self, dt):
        self.set_dark_theme()

    def update_config(self):
        config.set('RCH', 'TIME24', str(self.root.ids.time24_checkbox.active))
        config.set('RCH', 'OP25_SERVER', self.root.ids.op25_server_textbox.text)
        config.set('RCH', 'darkmode_checkbox', str(self.root.ids.time24_checkbox.active))



    def update_op25_settings(self):
        cc_list = self.root.ids.op25_config_controlchannels.text
        sysname = self.root.ids.op25_config_sysname.text
        tglist = self.root.ids.op25_config_talkgroup_list.text
        self.op25client.send_cmd_to_op25(command=f"WRITE_CONFIG;Control Channel List: {cc_list}, Sysname: {sysname}, Talkgroup List Name: {tglist}")


    def read_op25_settings(self):
        response = self.op25client.send_cmd_to_op25(command="GET_CONFIG")
        pattern = r"Control Channel List: (.*?), Sysname: (.*?), Talkgroup List Name: (.*)"
        match = re.search(pattern, response)
        print(response)

        if match:
            controlchannel = match.group(1)
            sysname = match.group(2)
            tglist = match.group(3)
            print(f"Control Channel: {controlchannel}")
            self.root.ids.op25_config_controlchannels.text = controlchannel
            self.root.ids.op25_config_sysname.text = sysname
            self.root.ids.op25_config_talkgroup_list.text = tglist
            print(f"Sysname: {sysname}")
            print(f"Talkgroup List Name: {tglist}")
        else:
            print("No match found")

    def start_thread(self):
        if not self.op25client.is_running():
            self.op25client.start()
            self.is_active = True

    def stop_thread(self):
        if self.op25client.is_running():
            self.op25client.stop()
            self.is_active = False

    def initialize_settings(self, *args):
        self.root.ids.op25_server_textbox.text = config.get(section='RCH', option='OP25_SERVER')
        self.root.ids.time24_checkbox.active = config.get_bool(section='RCH', option='TIME24')
        self.root.ids.darkmode_checkbox.text = config.get(section='RCH', option='darkmode_checkbox')

    def set_dark_theme(self, *args):
        self.theme_cls.theme_style = "Dark"

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
        new_label = Label(text=stamped_text, font_size='20sp', size_hint_y=None, height=self.calculate_text_height(stamped_text))
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


if __name__ == '__main__':
    app = MainApp()
    app.run()