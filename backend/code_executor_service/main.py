import pika
import json
import subprocess
import os
import time

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

def parse_test_code(test_code: str):
    """Парсит 'магические' комментарии из кода теста."""
    test_type = "unit"  # По умолчанию - юнит-тесты
    expected_output = None
    lines = test_code.strip().split('\n')
    for line in lines:
        if line.strip().startswith("# test_type:"):
            test_type = line.split(":", 1)[1].strip()
        if line.strip().startswith("# expected_output:"):
            expected_output = line.split(":", 1)[1].strip()
    return test_type, expected_output

def run_stdout_test(code: str, expected_output: str):
    """Выполняет код и сравнивает его вывод с ожидаемым."""
    try:
        # Используем '-c' для прямой передачи кода, это проще и безопаснее
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8' # Важно для русского языка
        )
        
        actual_output = result.stdout.strip()

        if result.returncode != 0:
            return {"status": "error", "output": f"Ошибка выполнения:\n\n{result.stderr}"}

        if actual_output == expected_output:
            return {"status": "success", "output": f"Все верно!\n\nВывод вашей программы:\n{actual_output}"}
        else:
            return {
                "status": "error",
                "output": f"Тест не пройден.\n\nОжидалось: '{expected_output}'\nПолучено:   '{actual_output}'"
            }
    except subprocess.TimeoutExpired:
        return {"status": "error", "output": "Выполнение программы превысило лимит времени!"}
    except Exception as e:
        return {"status": "error", "output": f"Произошла внутренняя ошибка: {str(e)}"}

def run_unit_tests(code: str, test_code: str):
    """Запускает pytest для проверки кода (старая логика)."""
    solution_filename = "solution.py"
    test_filename = "test_solution.py"
    
    try:
        with open(solution_filename, "w", encoding="utf-8") as f:
            f.write(code)

        # Pytest требует, чтобы тестовый файл импортировал решение,
        # поэтому мы добавляем import solution в начало, если его нет.
        # Это делает тесты более читаемыми.
        full_test_code = test_code
        if "import solution" not in test_code:
             full_test_code = "import solution\n" + test_code

        with open(test_filename, "w", encoding="utf-8") as f:
            f.write(full_test_code)

        env = os.environ.copy()
        env["PYTHONPATH"] = "."

        result = subprocess.run(
            ["pytest", "--tb=short", "-q", test_filename],
            capture_output=True,
            text=True,
            timeout=10,
            cwd="/app",
            env=env,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            return {"status": "success", "output": "Все тесты пройдены успешно!\n\n" + result.stdout}
        else:
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
    result = {}

    if not test_code:
        result = {"status": "error", "output": "Для этого урока не найдены тесты."}
    else:
        test_type, expected_output = parse_test_code(test_code)
        
        if test_type == "stdout":
            print(f"--- Running STDOUT test for {submission_id} ---", flush=True)
            if expected_output is None:
                result = {"status": "error", "output": "Ошибка в настройке теста: не указан expected_output."}
            else:
                result = run_stdout_test(user_code, expected_output)
        elif test_type == "unit":
            print(f"--- Running UNIT test for {submission_id} ---", flush=True)
            result = run_unit_tests(user_code, test_code)
        else:
            result = {"status": "error", "output": f"Неизвестный тип теста: {test_type}"}

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
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL)) # Упрощенный вариант, верните retry если нужно
    print("Code Executor Service: Connected to RabbitMQ successfully!", flush=True)
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