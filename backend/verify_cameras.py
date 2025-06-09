#!/usr/bin/env python3
"""
Quick tool to verify which camera feeds correspond to which physical bays.
Run this to check if Camera1->Bay1, Camera2->Bay2, etc. mappings are correct.
"""

# RTSP URLs from app.py
RTSP_URLS = {
    1: 'rtsp://192.168.1.74:7447/VJ1fB8D4d03nIwKF',  # Camera1 -> Bay1?
    2: 'rtsp://192.168.1.74:7447/zfDlcWJLTq10A49M',  # Camera2 -> Bay2?
    3: 'rtsp://192.168.1.74:7447/18JUhav6VfoOMVS0',  # Camera3 -> Bay3?
    4: 'rtsp://192.168.1.74:7447/BSPtMFwAXLncNdx0'   # Camera4 -> Bay4?
}

print("🎥 CURRENT CAMERA ASSIGNMENTS:")
print("================================")
for bay_id, url in RTSP_URLS.items():
    print(f"Bay {bay_id}: {url}")

print("\n📋 VERIFICATION INSTRUCTIONS:")
print("1. Check which physical bays currently have cars")
print("2. Compare with the detection logs showing Bay 3 and Bay 4 as 'inUse'")
print("3. If the mappings are wrong, we need to swap the RTSP URLs")
print("\n🔄 If Bay 1 and Bay 2 have cars but system shows Bay 3 and Bay 4:")
print("   Then Camera3->Bay1, Camera4->Bay2 (cameras shifted by +2)")