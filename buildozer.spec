[app]

#pre-splace screen
presplash.filename = resources/images/splash.png

#app icon
icon.filename = resources/images/icon.png

# (str) Title of your application
title = OP25MCH

# (str) Package name
package.name = OP25MCH

# (str) Package domain (needed for android/ios packaging)
package.domain = org.signalseverywhere

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,conf,ttf,ini,csv

# (list) List of inclusions using pattern matching
#source.include_patterns = assets/*,images/*.png

# (list) Source files to exclude (let empty to not exclude anything)
#source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, test_scripts

android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, WAKE_LOCK, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION
android.wakelock = True

# (list) List of exclusions using pattern matching
#source.exclude_patterns = license,images/*/*.jpg

# (str) Application versioning (method 1)
version = 0.0.1

# (str) Application versioning (method 2)
# version.regex = __version__ = ['"](.*)['"]
# version.filename = %(source.dir)s/main.py

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3, kivy==2.2.0, https://files.pythonhosted.org/packages/20/81/0b1154f5e581d5910702d9fadb3217f56cb186f72c8b36de0271e7ff9b5c/kivymd-1.2.0.tar.gz, materialyoucolor, exceptiongroup, asyncgui, asynckivy, requests, plyer, android, zeep, attrs, requests_file, lxml==5.1.0, isodate, pytz, requests_toolbelt, platformdirs, sqlite3
p4a.branch = develop
#kivy==2.3.0
# (str) Custom source folders for requirements
# Sets custom source for any requirements with recipes
# requirements.source.kivy = ../../kivy

# (list) Garden requirements
#garden_requirements =

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = landscape

# (list) List of service to declare
#services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1