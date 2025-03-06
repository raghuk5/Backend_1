# Code for Email Processor:

import pika
import json
import os
import psycopg2 # Example: PostgreSQL
from psycopg2 import OperationalError

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST") or "localhost"
QUEUE_NAME = "email_queue"
DB_HOST = os.environ.get("DB_HOST") or "localhost"
DB_NAME = os.environ.get("DB_NAME") or "postgres"

DB_USER = os.environ.get("DB_USER") or "postgres"
DB_PASSWORD = os.environ.get("DB_PASSWORD") or "******"

def connect_to_db():
    try:
        print(f"Connecting to: host={DB_HOST}, db={DB_NAME}, user={DB_USER}") #added print statement.
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
        return conn
    except OperationalError as e:
        print(f"Database connection error: {e}")
        return None

def process_email(ch, method, properties, body):
    try:
        email_data = json.loads(body)
        conn = connect_to_db()
        if conn:
            with conn.cursor() as cur:
                
                cur.execute("""
                    INSERT INTO emails (message_id, sender, subject, body, date, to_email, html_body)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (message_id) DO UPDATE SET
                        sender = EXCLUDED.sender,
                        subject = EXCLUDED.subject,
                        body = EXCLUDED.body,
                        date = EXCLUDED.date,
                        to_email = EXCLUDED.to_email,
                        html_body = EXCLUDED.html_body;
                """, (email_data["message_id"], email_data["from"], email_data["subject"], email_data.get("body", ""), email_data["date"], email_data["to"], email_data.get("html_body", ""))) #Get body and html_body safely
                conn.commit()
            conn.close()
            print(f"Processed and stored email: {email_data['subject']}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            print("Failed to connect to the database. Requeuing message.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True) 
    except json.JSONDecodeError as e:
        print(f"Invalid JSON received: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)  
    except Exception as e:
        print(f"Error processing email: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)  
        channel.basic_qos(prefetch_count=1) 

        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_email)

        print('Email processor started. Waiting for messages...')
        channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as e:
        print(f"RabbitMQ connection error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'connection' in locals() and connection.is_open():
            connection.close()


if __name__ == "__main__":
    main()
