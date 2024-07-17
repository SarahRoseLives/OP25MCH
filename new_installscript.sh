#!/bin/bash

# Ensure the script is run as root, since modifying user groups requires root privileges
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run with sudo IN YOUR HOME DIRECTORY"
   exit 1
fi

# Function to update Pi firmware
update_firmware() {
    echo "Updating Pi firmware..."
    sudo rpi-update
}

# Function to setup Access Point
setup_access_point() {
    echo "Setting up Access Point..."

    sudo apt update
    sudo apt install -y hostapd dnsmasq iptables dhcpcd5 -y

    sudo systemctl unmask hostapd
    sudo systemctl enable hostapd

    sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
    sudo bash -c 'cat > /etc/dnsmasq.conf << EOF
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF'

    sudo bash -c 'cat > /etc/hostapd/hostapd.conf << EOF
interface=wlan0
ssid=OP25MCH
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=MobileControlHead
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF'

    sudo sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

    sudo bash -c 'cat >> /etc/dhcpcd.conf << EOF
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOF'

    sudo sed -i 's|#net.ipv4.ip_forward=1|net.ipv4.ip_forward=1|' /etc/sysctl.conf

    sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
    sudo sh -c "iptables-save > /etc/iptables.ipv4.nat"
    sudo sed -i 's|exit 0|iptables-restore < /etc/iptables.ipv4.nat\nexit 0|' /etc/rc.local

    sudo systemctl restart dhcpcd
    sudo systemctl restart hostapd
    sudo systemctl restart dnsmasq

    add_delay_to_service "hostapd" 10
    add_delay_to_service "dnsmasq" 10
    add_delay_to_service "dhcpcd" 10
    sudo systemctl daemon-reload

    echo "Delay setup complete for hostapd, dnsmasq, and dhcpcd services."

    echo "WiFi Hotspot setup complete. SSID: OP25MCH, Password: MobileControlHead"

}

# Function to add delay to service unit file
add_delay_to_service() {
    local service_name="$1"
    local delay_seconds="$2"
    local service_file="/lib/systemd/system/$service_name.service"

    if [ -f "$service_file" ]; then
        sudo sed -i "/\[Service\]/a ExecStartPre=/bin/sleep $delay_seconds" "$service_file"
        echo "Delay of $delay_seconds added to $service_name service."
    else
        echo "Service file $service_file not found."
    fi
}

# Function to install OP25 and setup the mchserver service
install_op25_and_service() {
    echo "Installing OP25 and setting up the mchserver service..."

    # Set the target directory for the virtual environment
    HOME_DIR=$(eval echo ~$SUDO_USER)
    TARGET_DIR="$HOME_DIR/op25-gr310/op25/gr-op25_repeater/apps"
    VENV_DIR="$TARGET_DIR/venv"

    sudo apt update
    sudo apt install wget unzip screen -y

    sudo -u $SUDO_USER wget https://github.com/SarahRoseLives/op25/archive/refs/heads/gr310.zip -P $HOME_DIR
    sudo -u $SUDO_USER unzip $HOME_DIR/gr310.zip -d $HOME_DIR
    cd $HOME_DIR/op25-gr310

    read -p "Warning: Please ensure that any SDR devices are unplugged before continuing. Press Enter to continue, or Ctrl+C to cancel."

    sudo -u $SUDO_USER ./install.sh

    # Check if python3-venv is installed
    if ! dpkg -s python3-venv >/dev/null 2>&1; then
        echo "python3-venv not found. Installing..."
        sudo apt update
        sudo apt install -y python3-venv
    else
        echo "python3-venv is already installed."
    fi

    # Create the virtual environment
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment in $VENV_DIR"
        sudo -u $SUDO_USER python3 -m venv "$VENV_DIR"
    else
        echo "Virtual environment already exists in $VENV_DIR"
    fi

    # Activate the virtual environment and install zeep
    echo "Activating the virtual environment and installing zeep..."
    sudo -u $SUDO_USER bash -c "source $VENV_DIR/bin/activate && pip install --upgrade pip && pip install zeep"

    echo "Zeep installed successfully in the virtual environment."

    sudo chmod +x $HOME_DIR/op25-gr310/op25/gr-op25_repeater/apps/op25_mchserver.py

    sudo bash -c "cat > /etc/systemd/system/op25_mchserver.service << EOL
[Unit]
Description=Listens for commands and executes them from Op25 mobile app
After=network.target

[Service]
ExecStart=$HOME_DIR/op25-gr310/op25/gr-op25_repeater/apps/venv/bin/python3 $HOME_DIR/op25-gr310/op25/gr-op25_repeater/apps/op25_mchserver.py
WorkingDirectory=$HOME_DIR/op25-gr310/op25/gr-op25_repeater/apps
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$SUDO_USER

[Install]
WantedBy=multi-user.target
EOL"

    sudo systemctl daemon-reload
    sudo systemctl enable op25_mchserver.service
    sudo systemctl start op25_mchserver.service

    sudo reboot
}

# Function to do everything
do_everything() {
    echo "Starting full setup..."
    echo "1. Updating Pi firmware..."
    update_firmware
    echo "2. Setting up Access Point..."
    setup_access_point
    echo "3. Installing OP25 and setting up the mchserver service..."
    install_op25_and_service
    echo "Setup complete. Rebooting..."
}

# Menu loop
while true; do
    echo "Select an option:"
    echo "1) Update Pi Firmware"
    echo "2) Setup Access Point"
    echo "3) Install OP25 and the mchserver service"
    echo "4) Do everything"
    echo "5) Exit"

    read -p "Enter your choice [1-5]: " choice

    case $choice in
        1)
            update_firmware
            ;;
        2)
            setup_access_point
            ;;
        3)
            install_op25_and_service
            ;;
        4)
            do_everything
            ;;
        5)
            echo "Exiting."
            exit 0
            ;;
        *)
            echo "Invalid option. Please try again."
            ;;
    esac

    echo "Returning to the menu..."
    sleep 2
done
