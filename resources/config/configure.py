# config_parser.py

import configparser
import os

class Configure:
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        """Load the configuration file."""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file '{self.config_file}' not found.")
        self.config.read(self.config_file)

    def get(self, section, option, fallback=None):
        """Get a value from the configuration file."""
        try:
            return self.config.get(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def get_int(self, section, option, fallback=None):
        """Get an integer value from the configuration file."""
        try:
            return self.config.getint(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_float(self, section, option, fallback=None):
        """Get a float value from the configuration file."""
        try:
            return self.config.getfloat(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_bool(self, section, option, fallback=None):
        """Get a boolean value from the configuration file."""
        try:
            return self.config.getboolean(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def set(self, section, option, value):
        """Set a value in the configuration file."""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, str(value))
        self.save_config()

    def save_config(self):
        """Save the configuration to the file."""
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

# End of config_parser.py
