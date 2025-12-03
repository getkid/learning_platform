import pika
import json
import subprocess
import os


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

def execute_code(code: str):
    try:

        with open("temp_code.py", "w") as f:
            f.write(code)
        
        result = subprocess.run(
            ["python", "temp_code.py"],
            capture_output=True,
            text=True,
            timeout=5 
        )

        if result.returncode == 0:
            return {"status": "success", "output": result.stdout}
        else:
            return {"status": "error", "output": result.stderr}
    except subprocess.TimeoutExpired:
        return {"status": "error", "output": "Execution timed out!"}
    except Exception as e:
        return {"status": "error", "output": str(e)}
    finally:
        if os.path.exists("temp_code.py"):
            os.remove("temp_code.py")


def on_message_received(ch, method, properties, body):
    data = json.loads(body)
    submission_id = data.get('submission_id')
    print(f"--> Received submission: {submission_id}", flush=True)
    
    result = execute_code(data['code'])
    
    result_message = {
        "submission_id": submission_id,
        "status": result.get('status'),
        "output": result.get('output')
    }
    
    ch.basic_publish(
        exchange='',
        routing_key='result_queue', 
        body=json.dumps(result_message),
        properties=pika.BasicProperties(delivery_mode=2)
    )

    print(f"<-- Result for {submission_id} sent back", flush=True)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    print("Code Executor Service: Connecting to RabbitMQ...", flush=True)
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.queue_declare(queue='submission_queue', durable=True)
    channel.basic_consume(queue='submission_queue', on_message_callback=on_message_received)

    print("Code Executor Service: Waiting for messages. To exit press CTRL+C", flush=True)
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)