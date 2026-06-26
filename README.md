# VitalPulse
### Real-time Health Monitoring via IoT + MQTT + Multi-Database Routing

---

## Quick Start

```bash
docker compose up --build
```

Then open `dashboard.html` in your browser and click **Connect**.

---

## Folder structure

```
vitalpulse/
├── docker-compose.yml       <- starts everything
├── mosquitto.conf           <- MQTT broker config
├── mysql-init.sql           <- tables, trigger, view, stored procedure
├── dashboard.html           <- open in browser for live view
├── README.md
├── publisher/
│   ├── publisher.py         <- simulates 3 wearable devices
│   ├── Dockerfile
│   └── requirements.txt
└── subscriber/
    ├── subscriber.py        <- routes MQTT messages to databases
    ├── Dockerfile
    └── requirements.txt
```

---

## MQTT Topics

| Topic | Database |
|-------|----------|
| `vitalpulse/{id}/heart_rate` | MySQL |
| `vitalpulse/{id}/spo2` | MySQL |
| `vitalpulse/{id}/steps` | MySQL |
| `vitalpulse/{id}/telemetry` | MongoDB |
| `vitalpulse/{id}/activity` | MongoDB |
| `vitalpulse/network` | Neo4j |

---

## Useful commands

```bash
# MySQL
docker exec -it vitalpulse-mysql mysql -uroot -pvitalpulse vitalpulse
SELECT * FROM v_latest_vitals;
SELECT * FROM alerts;
CALL sp_daily_summary('device-001');

# MongoDB
docker exec -it vitalpulse-mongo mongosh vitalpulse
db.raw_telemetry.find().limit(3)

# Neo4j browser
http://localhost:7474  (neo4j / vitalpulse)
MATCH (u:User)-[:WEARS]->(d:Device) RETURN u, d
```
