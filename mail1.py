# Code for IMAP Clients:


import imaplib
import email
import json
import pika
import time
import threading
import os  # For environment variables


# Configuration (from environment variables)
MAIL_SERVER = os.environ.get("MAIL_SERVER") or "imap.gmail.com"  # Default if not set
MAIL_USER = os.environ.get("MAIL_USER") or "huskiie.523@gmail.com"
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD") or "*** **** **** ****"
MAILBOX = os.environ.get("MAILBOX") or "INBOX"
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST") or "localhost"
QUEUE_NAME = "email_queue"

def fetch_and_publish_emails(mail, channel):
    mail.select(MAILBOX)
    _, data = mail.search(None, 'ALL') # Or 'UNSEEN' for new emails only
    for num in data[0].split():
        _, data = mail.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])

        email_dict = {  # More complete email data
            "from": msg["From"],
            "to": msg["To"],
            "subject": msg["Subject"],
            "date": msg["Date"],
            "body": "",  # Initialize body
            "message_id": msg["Message-ID"],  
            
        }

        for part in msg.walk():  # Handle multipart emails
            if part.get_content_type() == "text/plain":
                email_dict["body"] += part.get_payload(decode=True).decode(errors='ignore') #Handle encoding issues
            elif part.get_content_type() == "text/html": #If you also want to save the html part
                email_dict["html_body"] = part.get_payload(decode=True).decode(errors='ignore')


        try:
            channel.basic_publish(exchange='', routing_key=QUEUE_NAME, body=json.dumps(email_dict))
            print(f"Published email: {email_dict['subject']}")
        except pika.exceptions.AMQPConnectionError as e:
            print(f"RabbitMQ connection error: {e}")
          
            time.sleep(5)  
            

def check_for_new_emails(mail, channel):
    while True:

        try:
            mail.noop() # Keep alive
            _, data = mail.search(None, 'UNSEEN') # Check for new emails
            new_emails = data[0].split()
            if new_emails:
                fetch_and_publish_emails(mail, channel)
                    
        except imaplib.IMAP4.error as e:
            print(f"IMAP error: {e}")
            
            
        except Exception as e:
            print(f"General error: {e}")
            time.sleep(60)  

def main():
    try:
        
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
       
        mail.login('huskiie.523@gmail.com', 'yrlz dsoq york eedx')
       
        mail.select('inbox')
        

        

       
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)  

        # Initial fetch (optional - you might only want new emails)
        # fetch_and_publish_emails(mail, channel)

        thread = threading.Thread(target=check_for_new_emails, args=(mail,channel))
        thread.daemon = True
        thread.start()

        print("IMAP client started. Checking for new emails...")

        while True: # Keep the main thread alive
            time.sleep(1)

    except imaplib.IMAP4.error as e:
        print(f"IMAP login error: {e}")
    except OSError as e:
        print(f"OS error: {e}")    
    except pika.exceptions.AMQPConnectionError as e:
        print(f"RabbitMQ connection error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        try: 
          

          
        
              
          if 'connection' in locals() and connection.is_open:
            connection.close()
        except Exception as close_error:
            print(f"Error during close/logout:{close_error}")    

if __name__ == "__main__":
    main()


