import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pika

from services.outbox_store import claim_outbox, mark_sent, mark_failed

RABBITMQ_HOST = os.getenv("SKUA_RABBITMQ_HOST", "172.18.0.21")
RABBITMQ_PORT = int(os.getenv("SKUA_RABBITMQ_PORT", "5672"))
RABBITMQ_VHOST = os.getenv("SKUA_RABBITMQ_VHOST", "/skua")
RABBITMQ_USER = os.getenv("SKUA_RABBITMQ_USER", "skua")
RABBITMQ_PASSWORD = os.getenv("SKUA_RABBITMQ_PASSWORD", "skua_dev_password")

QUEUE_NAME = os.getenv("SKUA_RABBITMQ_QUEUE", "skua.events")


def connect_rabbit():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            virtual_host=RABBITMQ_VHOST,
            credentials=credentials,
        )
    )

    channel = connection.channel()

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
    )

    return connection, channel


def publish_event(record):
    payload = json.loads(record["payload"])

    event = {
        "event_id": record["event_id"],
        "event_type": record["event_type"],
        "routing_key": record["routing_key"] or QUEUE_NAME,
        "payload": payload,
        "producer": "skua-core",
    }

    connection, channel = connect_rabbit()

    try:
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(event),
            properties=pika.BasicProperties(
                message_id=record["event_id"],
                content_type="application/json",
                delivery_mode=2,
            ),
            mandatory=False,
        )
    finally:
        connection.close()


def publish_next_pending(worker_id="rabbit-publisher", lease_ttl_ms=300000):
    record = claim_outbox(worker_id, lease_ttl_ms=lease_ttl_ms)

    if not record:
        print("[RABBIT] published=0")
        return False

    try:
        publish_event(record)
        ok = mark_sent(record["id"], worker_id, record["lease_token"])
        print(f"[RABBIT] published=1 event_id={record['event_id']} marked_sent={ok}")
        return ok
    except Exception as exc:
        mark_failed(
            record["id"],
            worker_id,
            record["lease_token"],
            error=str(exc),
            backoff_ms=5000,
        )
        print(f"[RABBIT] published=0 event_id={record['event_id']} error={type(exc).__name__}")
        raise


def publish_pending_events(limit=100):
    published = 0

    for _ in range(limit):
        ok = publish_next_pending()
        if not ok:
            break
        published += 1

    print(f"[RABBIT] loop_published={published}")
    return published


if __name__ == "__main__":
    publish_pending_events()
