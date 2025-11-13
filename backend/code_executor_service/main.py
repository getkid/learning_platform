# backend/code_executor_service/main.py

import pika
import json
import subprocess
import os


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

def execute_code(code: str):
    """
    Безопасно выполняет код в отдельном процессе.
    В реальном проекте здесь был бы вызов Docker-контейнера.
    Для простоты мы используем subprocess.
    """
    try:
        # Создаем временный файл с кодом
        with open("temp_code.py", "w") as f:
            f.write(code)
        
        # Запускаем код и получаем результат
        result = subprocess.run(
            ["python", "temp_code.py"],
            capture_output=True,
            text=True,
            timeout=5 # Ограничение по времени выполнения
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
    """
    Обработчик сообщений из RabbitMQ.
    """
    data = json.loads(body)
    print(f"--> Received submission: {data['submission_id']}", flush=True)
    
    # Выполняем код
    result = execute_code(data['code'])
    
    print(f"<-- Result for {data['submission_id']}: {result['status']}", flush=True)

    # !!! В будущем здесь будет отправка результата обратно в core_service !!!
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