## Remote Control Head
An Android app that turns OP25 into a full blown mobile scanner.

## The History
This is easiy my biggest and most ambitiously complicated project I've ever worked on.
The original application was written in TKinter with python and supported night mode, scanning select talkgroups in a simple mannor, automatic
gps switching, radio reference importing and so much more.

It did this by running a server that manipulates the OP25 instance and it's configuration files.
However this application didn't translate well to Android. You can find it here: https://github.com/KR0SIV/op25mobileControlHead

Then I tried to port it over to Kivy and get it working on Android, it managed to get as far as a log and a basic display.
It wasn't all that mobile friendly imo. You can find it here: https://github.com/KR0SIV/Pi25MCH_Kivy

As I learn more about Kivy I've been wanting to re-write the application and re-implement all the best features of the original.

## Current Freatures Implemented

* Basic display with talkgroup and system name details
* Garbage signals icon based on tsbks (don't pay it any mind... it's crap)
* Basic config options for OP25 Instance and Clock Options (Restart to Take Effect)
* Some mock up crap

## Future Features

* Automatic system switching
* Radio Reference Importing
* Automatic Site Switching Within a System
* "ScanGrid" Allowing you to set channels to scan specifically on the fly
* A docker server instance to handle op25 and custom commands to implement above features