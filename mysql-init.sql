CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    device_id   VARCHAR(50)  NOT NULL UNIQUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vitals (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    device_id   VARCHAR(50)  NOT NULL,
    metric      VARCHAR(50)  NOT NULL,
    value       FLOAT        NOT NULL,
    unit        VARCHAR(20)  NOT NULL,
    recorded_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES users(device_id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    device_id   VARCHAR(50)  NOT NULL,
    metric      VARCHAR(50)  NOT NULL,
    value       FLOAT        NOT NULL,
    reason      VARCHAR(255) NOT NULL,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- Seed users / devices
INSERT IGNORE INTO users (name, device_id) VALUES
    ('Alice Romano',    'device-001'),
    ('Marco Bianchi',   'device-002'),
    ('Sara Esposito',   'device-003');

DELIMITER $$
CREATE TRIGGER trg_vitals_alert
AFTER INSERT ON vitals
FOR EACH ROW
BEGIN
    IF NEW.metric = 'heart_rate' AND (NEW.value < 45 OR NEW.value > 120) THEN
        INSERT INTO alerts (device_id, metric, value, reason)
        VALUES (
            NEW.device_id,
            NEW.metric,
            NEW.value,
            CASE
                WHEN NEW.value < 45 THEN 'Critically low heart rate'
                ELSE 'Critically high heart rate'
            END
        );
    END IF;

    IF NEW.metric = 'spo2' AND NEW.value < 90 THEN
        INSERT INTO alerts (device_id, metric, value, reason)
        VALUES (NEW.device_id, NEW.metric, NEW.value, 'Low blood oxygen saturation');
    END IF;
END$$
DELIMITER ;


CREATE OR REPLACE VIEW v_latest_vitals AS
SELECT
    v.device_id,
    u.name,
    v.metric,
    v.value,
    v.unit,
    v.recorded_at
FROM vitals v
JOIN users u ON v.device_id = u.device_id
WHERE v.recorded_at = (
    SELECT MAX(v2.recorded_at)
    FROM vitals v2
    WHERE v2.device_id = v.device_id
      AND v2.metric    = v.metric
);

DELIMITER $$
CREATE PROCEDURE sp_daily_summary(IN p_device_id VARCHAR(50))
BEGIN
    SELECT
        device_id,
        metric,
        ROUND(AVG(value), 2)  AS avg_value,
        ROUND(MIN(value), 2)  AS min_value,
        ROUND(MAX(value), 2)  AS max_value,
        COUNT(*)              AS reading_count,
        DATE(recorded_at)     AS day
    FROM vitals
    WHERE device_id = p_device_id
      AND recorded_at >= CURDATE()
    GROUP BY device_id, metric, DATE(recorded_at)
    ORDER BY metric;
END$$
DELIMITER ;
