import pika
import json
import subprocess
import os
import time

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

def execute_code_with_tests(code: str, test_code: str):
    solution_filename = "solution.py"
    test_filename = "test_solution.py"

    # --- ДОБАВЛЯЕМ ОТЛАДОЧНЫЕ СООБЩЕНИЯ ---
    print(f"--- Writing code to {solution_filename} ---", flush=True)
    print(code, flush=True)
    print("-----------------------------------------", flush=True)
    
    print(f"--- Writing tests to {test_filename} ---", flush=True)
    print(test_code, flush=True)
    print("-----------------------------------------", flush=True)
    
    try:
        with open(solution_filename, "w", encoding="utf-8") as f:
            f.write(code)

        with open(test_filename, "w", encoding="utf-8") as f:
            f.write(test_code)

        # Проверяем, что файлы действительно создались
        if not os.path.exists(test_filename):
            return {"status": "error", "output": "Internal error: Test file was not created."}

        env = os.environ.copy()
        env["PYTHONPATH"] = "."

        print(f"--- Running pytest on {test_filename} ---", flush=True)
        
        # Запускаем pytest и получаем результат
        result = subprocess.run(
            ["pytest", "--tb=short", "-q", test_filename],
            capture_output=True,
            text=True,
            timeout=10,
            # Указываем рабочую директорию явно, чтобы быть на 100% уверенными
            cwd="/app",
            env=env 
        )
        
        print(f"--- Pytest finished with code {result.returncode} ---", flush=True)
        print("STDOUT:", result.stdout, flush=True)
        print("STDERR:", result.stderr, flush=True)
        print("----------------------------------------------", flush=True)

        if result.returncode == 0:
            return {"status": "success", "output": "Все тесты пройдены успешно!\n\n" + result.stdout}
        else:
            # Код 1 - тесты упали, Код 2 - ошибка использования (как file not found)
            error_message = result.stdout + result.stderr
            return {"status": "error", "output": "Тесты не пройдены:\n\n" + error_message}

    except subprocess.TimeoutExpired:
        return {"status": "error", "output": "Выполнение тестов превысило лимит времени!"}
    except Exception as e:
        return {"status": "error", "output": f"Произошла внутренняя ошибка: {str(e)}"}
    finally:
        if os.path.exists(solution_filename):
            os.remove(solution_filename)
        if os.path.exists(test_filename):
            os.remove(test_filename)


def on_message_received(ch, method, properties, body):
    data = json.loads(body)
    submission_id = data.get('submission_id')
    print(f"--> Received submission: {submission_id}", flush=True)
    
    user_code = data.get("code")
    test_code = data.get("test_code")

    if not test_code:
        result = {"status": "error", "output": "Для этого урока не найдены тесты."}
    else:
        result = execute_code_with_tests(user_code, test_code)

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