import json
import uuid
import sqlite3
from pathlib import Path

import pika

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "skua_persistence.db"

RABBITMQ_HOST = "172.18.0.21"
QUEUE_NAME = "skua.events"


def connect_db():
    return sqlite3.connect(DB_PATH)


def connect_rabbit():
    credentials = pika.PlainCredentials("skua", "skua_dev_password")

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=5672,
            virtual_host="/skua",
            credentials=credentials
        )
    )

    channel = connection.channel()

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True
    )

    return connection, channel

def publish_event(event):
    connection, channel = connect_rabbit()

    body = json.dumps(event)

    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=body,
        properties=pika.BasicProperties(
            message_id=event["event_id"],
            delivery_mode=2
        )
    )

    connection.close()


def publish_pending_events():
    conn = connect_db()
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    rows = cur.execute("""
        SELECT id, event_type, payload
        FROM outbox
        WHERE status='pending'
        ORDER BY id ASC
        LIMIT 100
    """).fetchall()

    count = 0

    for row in rows:
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": row["event_type"],
            "payload": json.loads(row["payload"]),
            "producer": "skua-core"
        }

        publish_event(event)

        cur.execute("""
            UPDATE outbox
            SET status='sent'
            WHERE id=?
        """, (row["id"],))

        count += 1

    conn.commit()
    conn.close()

    print(f"[RABBIT] published={count}")


if __name__ == "__main__":
    publish_pending_events()
