from scapy.all import ARP, Ether, srp
import bluetooth
import time
import requests

# Replace with your phone's MAC addresses
PHONE_WIFI_MAC = "AA:BB:CC:DD:EE:FF"
PHONE_BT_MAC = "11:22:33:44:55:66"

# Replace with your automation system's API endpoint and token
AUTOMATION_API_URL = "http://your-automation-system/api/device/Lab%20lights%20-%20Lab"
API_TOKEN = "YOUR_API_TOKEN"

# Wi-Fi detection function
def detect_wifi(target_mac):
    ip_range = "192.168.1.1/24"  # Adjust to your network
    arp = ARP(pdst=ip_range)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether/arp
    result = srp(packet, timeout=3, verbose=False)[0]

    for sent, received in result:
        if received.hwsrc.lower() == target_mac.lower():
            return True
    return False

# Bluetooth detection function
def detect_bluetooth(target_mac):
    nearby_devices = bluetooth.discover_devices(duration=5, lookup_names=True)
    for addr, name in nearby_devices:
        if addr.lower() == target_mac.lower():
            return True
    return False

# Trigger lab lights ON
def turn_on_lab_lights():
    payload = {"on": True}
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    response = requests.post(AUTOMATION_API_URL, json=payload, headers=headers)
    if response.status_code == 200:
        print("💡 Lab lights turned ON")
    else:
        print(f"⚠️ Failed to turn on lights: {response.status_code}")

# Main loop
while True:
    wifi_found = detect_wifi(PHONE_WIFI_MAC)
    bt_found = detect_bluetooth(PHONE_BT_MAC)

    if wifi_found or bt_found:
        print("📱 Phone detected! Triggering lab lights...")
        turn_on_lab_lights()
    else:
        print("❌ Phone not detected.")

    time.sleep(10)  # Check every 10 seconds
