## Remote Control Head
An Android app that turns OP25 into a full blown mobile scanner.

## The History
This is easiy my biggest and most ambitiously complicated project I've ever worked on.
The original application was written in TKinter with python and supported night mode, scanning select talkgroups in a simple mannor, automatic
gps switching, radio reference importing and so much more.

https://youtu.be/LAmJmRco71s

It did this by running a server that manipulates the OP25 instance and it's configuration files.
However this application didn't translate well to Android. You can find it here: https://github.com/KR0SIV/op25mobileControlHead

Then I tried to port it over to Kivy and get it working on Android, it managed to get as far as a log and a basic display.
It wasn't all that mobile friendly imo. You can find it here: https://github.com/KR0SIV/Pi25MCH_Kivy

As I learn more about Kivy I've been wanting to re-write the application and re-implement all the best features of the original.

## How To Use It

1. Setup your raspberry pi, we're testing on Raspbian Lite Bookworm (Latest as of 5/27/2024)
   2. Skip the next step if you use this image instead: https://mega.nz/file/GVdmHCyZ#YEzoUWxMdqsqHO8FFgzyPJzrthHx9cy6uFr6C0GKt7Y
2. Download and run setup_raspberrypi.sh (Backup Your Stuff! Seriously)
   * Note that this will take a LONG LONG time.
   * It creates a new user
   * Creates the OP25 Service
   * Sets up Hotspot to connect app with (Password is: MobileControlHead)
   * Downloads OP25 with my server inside the apps directory
   * Reboots the pi
3. Download and install the app from the releases page

## Current Freatures Implemented

* Basic display with talkgroup and system name details
* Garbage signals icon based on tsbks (don't pay it any mind... it's crap)
* Basic config options for OP25 Instance and Clock Options (Restart to Take Effect)
* Some Moc info

## Future Features

* Automatic system switching
* Radio Reference Importing
* Automatic Site Switching Within a System
* "ScanGrid" Allowing you to set channels to scan specifically on the fly
* A docker server instance to handle op25 and custom commands to implement above features

## Support Me and Development
I'm putting a lot of time into this application, any support would be greatly appreciated.
https://www.patreon.com/SarahRoseLives