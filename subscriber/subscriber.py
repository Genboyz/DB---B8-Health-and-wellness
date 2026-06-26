import json
import os
import time

import mysql.connector
import paho.mqtt.client as mqtt
from neo4j import GraphDatabase
from pymongo import MongoClient

MQTT_HOST      = os.getenv("MQTT_HOST",      "localhost")
MQTT_PORT      = int(os.getenv("MQTT_PORT",  1883))
MYSQL_HOST     = os.getenv("MYSQL_HOST",     "localhost")
MYSQL_USER     = os.getenv("MYSQL_USER",     "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "vitalpulse")
MYSQL_DB       = os.getenv("MYSQL_DB",       "vitalpulse")
MONGO_URI      = os.getenv("MONGO_URI",      "mongodb://localhost:27017")
NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "vitalpulse")

MYSQL_METRICS = {"heart_rate", "spo2", "steps"}


def connect_mysql():
    while True:
        try:
            conn = mysql.connector.connect(
                host=MYSQL_HOST, user=MYSQL_USER,
                password=MYSQL_PASSWORD, database=MYSQL_DB,
                autocommit=True,
            )
            print("[MySQL] Connected")
            return conn
        except Exception as e:
            print(f"[MySQL] Not ready ({e}), retrying in 3s ...")
            time.sleep(3)


def connect_mongo():
    client = MongoClient(MONGO_URI)
    db = client["vitalpulse"]
    print("[MongoDB] Connected")
    return db


def connect_neo4j():
    while True:
        try:
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            driver.verify_connectivity()
            print("[Neo4j] Connected")
            return driver
        except Exception as e:
            print(f"[Neo4j] Not ready ({e}), retrying in 5s ...")
            time.sleep(5)


def handle_vital(mysql_conn, device_id: str, metric: str, payload: dict):
    cursor = mysql_conn.cursor()
    cursor.execute(
        "INSERT INTO vitals (device_id, metric, value, unit) VALUES (%s, %s, %s, %s)",
        (device_id, metric, payload["value"], payload["unit"]),
    )
    cursor.close()
    print(f"[MySQL] {device_id} {metric}={payload['value']} {payload['unit']}")


def handle_telemetry(mongo_db, payload: dict):
    mongo_db["raw_telemetry"].insert_one(payload)
    print(f"[MongoDB] raw_telemetry <- {payload['device_id']}")


def handle_activity(mongo_db, payload: dict):
    mongo_db["activity_sessions"].insert_one(payload)
    print(f"[MongoDB] activity_session <- {payload['device_id']} ({payload['session_type']})")


def handle_network(neo4j_driver, payload: dict):
    cypher = """
    MERGE (ua:User {name: $user_a})
    MERGE (da:Device {id: $device_a})
    MERGE (ua)-[:WEARS]->(da)

    MERGE (ub:User {name: $user_b})
    MERGE (db:Device {id: $device_b})
    MERGE (ub)-[:WEARS]->(db)

    CREATE (da)-[:PROXIMITY_EVENT {
        timestamp:  $timestamp,
        distance_m: $distance_m
    }]->(db)
    """
    with neo4j_driver.session() as session:
        session.run(cypher, **payload)
    print(f"[Neo4j] proximity {payload['device_a']} <-> {payload['device_b']} ({payload['distance_m']}m)")


def make_on_message(mysql_conn, mongo_db, neo4j_driver):
    def on_message(client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            print(f"[WARN] Bad JSON on {topic}")
            return

        parts = topic.split("/")

        if topic == "vitalpulse/network":
            handle_network(neo4j_driver, payload)
            return

        if len(parts) < 3:
            return

        _, device_id, subtopic = parts[0], parts[1], parts[2]

        if subtopic in MYSQL_METRICS:
            handle_vital(mysql_conn, device_id, subtopic, payload)
        elif subtopic == "telemetry":
            handle_telemetry(mongo_db, payload)
        elif subtopic == "activity":
            handle_activity(mongo_db, payload)

    return on_message


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe("vitalpulse/#", qos=1)
        print("[MQTT] Subscribed to vitalpulse/#")
    else:
        print(f"[MQTT] Connection failed: {rc}")


def main():
    print("[VitalPulse] Subscriber starting ...")
    mysql_conn   = connect_mysql()
    mongo_db     = connect_mongo()
    neo4j_driver = connect_neo4j()

    client = mqtt.Client(client_id="vitalpulse-subscriber")
    client.on_connect = on_connect
    client.on_message = make_on_message(mysql_conn, mongo_db, neo4j_driver)

    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            break
        except Exception as e:
            print(f"[MQTT] Broker not ready ({e}), retrying in 3s ...")
            time.sleep(3)

    print("[VitalPulse] Listening ...")
    client.loop_forever()


if __name__ == "__main__":
    main()
