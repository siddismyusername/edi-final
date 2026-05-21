"""Quick integration test: sends interleaved IMU + frame data to trigger the full fusion pipeline."""

import time
import json
import base64
import requests
import sys

BASE = "http://localhost:8000"

def main():
    print("=== ETA-Sync Pipeline Test ===")

    # 1. Health check
    r = requests.get(f"{BASE}/health")
    print(f"Health: {r.json()}")

    # 2. Create session
    r = requests.post(f"{BASE}/session/create", json={
        "device_id": "test-device-001",
        "mode": "sync",
        "notes": "Integration test"
    })
    print(f"Session: {r.json()}")
    session_id = r.json()["session_id"]

    # 3. Send interleaved IMU + camera data over 3 seconds
    # IMU at ~25Hz, Camera at ~5FPS — interleaved to fill the window properly
    print(f"\nSending interleaved sensor data...")
    base_ts = time.time()
    fake_jpeg = base64.b64encode(b'\xff\xd8\xff' + b'\x00' * 100 + b'\xff\xd9').decode()

    imu_sent = 0
    frame_sent = 0
    frame_interval = 0.2  # 5 FPS
    imu_interval = 0.04   # 25 Hz
    total_duration = 3.0   # 3 seconds of data

    current = 0.0
    next_imu = 0.0
    next_frame = 0.0

    while current <= total_duration:
        # Send IMU if due
        if current >= next_imu:
            ts = base_ts + current
            r = requests.post(f"{BASE}/imu", json={
                "timestamp": ts,
                "ax": 0.1 + (imu_sent % 5) * 0.2,
                "ay": 0.4 + (imu_sent % 3) * 0.1,
                "az": 9.81,
                "gx": 0.01 * (imu_sent % 4),
                "gy": 0.04 * (imu_sent % 3),
                "gz": 0.07,
                "mode": "sync",
            })
            if r.status_code != 200:
                print(f"  IMU FAIL: {r.status_code} {r.text}")
                return
            imu_sent += 1
            next_imu += imu_interval

        # Send frame if due
        if current >= next_frame:
            ts = base_ts + current
            r = requests.post(f"{BASE}/frame", json={
                "timestamp": ts,
                "frame_id": frame_sent,
                "resolution": "640x480",
                "data": fake_jpeg,
                "mode": "sync",
            })
            if r.status_code != 200:
                print(f"  Frame FAIL: {r.status_code} {r.text}")
                return
            frame_sent += 1
            next_frame += frame_interval

        current = min(next_imu, next_frame)

    print(f"  Sent {imu_sent} IMU + {frame_sent} frames (interleaved)")

    # 4. Check session status
    time.sleep(0.5)  # Wait for any async processing
    r = requests.get(f"{BASE}/session/list")
    sessions = r.json()
    print(f"\nActive sessions:")
    for s in sessions:
        print(f"  {s['session_id']}: IMU={s['imu_packet_count']}, "
              f"Frames={s['frame_count']}, State={s['state']}")
        if 'windows_processed' in s:
            print(f"    Windows processed: {s['windows_processed']}")

    # 5. Close session
    r = requests.post(f"{BASE}/session/close?session_id={session_id}")
    print(f"\nClose: {r.json()}")

    # 6. Check exported data
    r = requests.get(f"{BASE}/session/export/{session_id}")
    export = r.json()
    print(f"Export: {json.dumps(export, indent=2)}")

    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
