import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

DEVICES = [
    {"id": "device-001", "name": "Alice Romano",  "activity": "running"},
    {"id": "device-002", "name": "Marco Bianchi", "activity": "resting"},
    {"id": "device-003", "name": "Sara Esposito", "activity": "walking"},
]

ACTIVITIES = ["resting", "walking", "running", "cycling", "sleeping"]


def sim_heart_rate(activity: str) -> float:
    base = {"resting": 65, "walking": 85, "running": 145,
            "cycling": 130, "sleeping": 55}
    return round(base.get(activity, 70) + random.uniform(-8, 8), 1)


def sim_spo2() -> float:
    if random.random() < 0.05:
        return round(random.uniform(86, 89), 1)
    return round(random.uniform(96, 99.5), 1)


def sim_steps(activity: str, elapsed_seconds: int) -> int:
    rate = {"resting": 0, "walking": 1.5, "running": 3.0,
            "cycling": 0, "sleeping": 0}
    return int(rate.get(activity, 0) * elapsed_seconds)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT] Connected to broker at {MQTT_HOST}:{MQTT_PORT}")
    else:
        print(f"[MQTT] Connection failed with code {rc}")


def main():
    client = mqtt.Client(client_id="vitalpulse-publisher")
    client.on_connect = on_connect

    print(f"[MQTT] Connecting to {MQTT_HOST}:{MQTT_PORT} ...")
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            break
        except Exception as e:
            print(f"[MQTT] Broker not ready yet ({e}), retrying in 3s ...")
            time.sleep(3)

    client.loop_start()
    start_time = time.time()
    cycle = 0

    while True:
        elapsed = int(time.time() - start_time)
        cycle += 1

        for device in DEVICES:
            did      = device["id"]
            activity = device["activity"]
            ts       = now_iso()

            hr    = sim_heart_rate(activity)
            spo2  = sim_spo2()
            steps = sim_steps(activity, elapsed)

           
            client.publish(f"vitalpulse/{did}/heart_rate",
                json.dumps({"device_id": did, "value": hr, "unit": "bpm", "timestamp": ts}), qos=1)
            client.publish(f"vitalpulse/{did}/spo2",
                json.dumps({"device_id": did, "value": spo2, "unit": "%", "timestamp": ts}), qos=1)
            client.publish(f"vitalpulse/{did}/steps",
                json.dumps({"device_id": did, "value": steps, "unit": "steps", "timestamp": ts}), qos=1)

           
            client.publish(f"vitalpulse/{did}/telemetry",
                json.dumps({
                    "device_id": did, "user": device["name"], "timestamp": ts,
                    "metrics": {
                        "heart_rate": {"value": hr,    "unit": "bpm"},
                        "spo2":       {"value": spo2,  "unit": "%"},
                        "steps":      {"value": steps, "unit": "steps"},
                    },
                    "activity": activity, "firmware": "v2.4.1",
                    "battery":  random.randint(40, 100),
                }), qos=0)

            if cycle % 10 == 0:
                client.publish(f"vitalpulse/{did}/activity",
                    json.dumps({
                        "device_id": did, "user": device["name"], "timestamp": ts,
                        "session_type": activity, "duration_sec": elapsed,
                        "avg_hr": hr, "avg_spo2": spo2, "total_steps": steps,
                    }), qos=1)

            if random.random() < 0.05:
                device["activity"] = random.choice(ACTIVITIES)
                print(f"[SIM] {device['name']} changed activity -> {device['activity']}")

        if cycle % 15 == 0:
            pair = random.sample(DEVICES, 2)
            client.publish("vitalpulse/network",
                json.dumps({
                    "timestamp":  now_iso(), "event": "proximity",
                    "device_a":   pair[0]["id"], "user_a": pair[0]["name"],
                    "device_b":   pair[1]["id"], "user_b": pair[1]["name"],
                    "distance_m": round(random.uniform(1, 15), 1),
                }), qos=1)

        print(f"[PUB] Cycle {cycle} published -- elapsed {elapsed}s")
        time.sleep(5)


if __name__ == "__main__":
    main()
