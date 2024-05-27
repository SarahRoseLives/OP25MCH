#!/bin/bash


sudo rpi-update

# Create a user called op25 with the password 'op25'
sudo useradd -m -s /bin/bash op25
echo "op25:op25" | sudo chpasswd
sudo usermod -aG sudo op25

# Update the system
sudo apt update

# Install necessary packages
sudo apt install -y hostapd dnsmasq iptables dhcpcd5 wget unzip screen

# Enable hostapd service
sudo systemctl unmask hostapd
sudo systemctl enable hostapd

# Backup the current dnsmasq configuration
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig

# Create a new dnsmasq configuration file
sudo bash -c 'cat > /etc/dnsmasq.conf << EOF
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF'

# Create the hostapd configuration file
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

# Point hostapd to the configuration file
sudo sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

# Configure the network interface
sudo bash -c 'cat >> /etc/dhcpcd.conf << EOF
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOF'

# Enable IP forwarding
sudo sed -i 's|#net.ipv4.ip_forward=1|net.ipv4.ip_forward=1|' /etc/sysctl.conf

# Configure NAT
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

# Save the iptables rule
sudo sh -c "iptables-save > /etc/iptables.ipv4.nat"

# Ensure iptables rule is loaded on boot
sudo sed -i 's|exit 0|iptables-restore < /etc/iptables.ipv4.nat\nexit 0|' /etc/rc.local

# Restart services
sudo systemctl restart dhcpcd
sudo systemctl restart hostapd
sudo systemctl restart dnsmasq

echo "WiFi Hotspot setup complete. SSID: OP25MCH, Password: MobileControlHead"

# Create the service file
sudo bash -c 'cat > /etc/systemd/system/op25_mchserver.service << EOF
[Unit]
Description=Listens for commands and executes them from Op25 mobile app
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/op25/op25-gr310/op25/gr-op25_repeater/apps/op25_mchserver.py
WorkingDirectory=/home/op25/op25-gr310/op25/gr-op25_repeater/apps
StandardOutput=inherit
StandardError=inherit
Restart=always
User=op25

[Install]
WantedBy=multi-user.target
EOF'

# Reload systemd daemon and enable the service
sudo systemctl daemon-reload
sudo systemctl enable op25_mchserver.service
sudo systemctl start op25_mchserver.service

# Function to add delay to service unit file
add_delay_to_service() {
    local service_name="$1"
    local delay_seconds="$2"
    local service_file="/lib/systemd/system/$service_name.service"

    # Check if service file exists
    if [ -f "$service_file" ]; then
        # Add delay to service file
        sudo sed -i "/\[Service\]/a ExecStartPre=/bin/sleep $delay_seconds" "$service_file"
        echo "Delay of $delay_seconds seconds added to $service_name service."
    else
        echo "Service file $service_file not found."
    fi
}

# Add delays to services
add_delay_to_service "hostapd" 10
add_delay_to_service "dnsmasq" 10
add_delay_to_service "dhcpcd" 10

# Reload systemd daemon
sudo systemctl daemon-reload

echo "Delay setup complete for hostapd, dnsmasq, and dhcpcd services."

# Download the ZIP file
wget https://github.com/SarahRoseLives/op25/archive/refs/heads/gr310.zip

# Unzip the downloaded file
unzip gr310.zip

# Move into the extracted directory
cd op25-gr310

# Prompt user to unplug any SDR before continuing
read -p "Warning: Please ensure that any SDR devices are unplugged before continuing. Press Enter to continue, or Ctrl+C to cancel."

# Run the installation script
./install.sh

# Chmod the op25_mchserver script and reboot
sudo chmod +x /home/op25/op25-gr310/op25/gr-op25_repeater/apps/op25_mchserver.py


sudo reboot
