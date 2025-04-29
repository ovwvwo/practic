import unittest
import socket
import sys
import threading
import time
import io
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock

# Импортируем серверный и клиентский код
# Предполагается, что код сервера и клиента сохранен в файлы server.py и client.py
# и функции сервера и клиента импортируются следующим образом:

# Если вы используете отдельные файлы, используйте импорты:
# from server import do_something  # Функция обработки данных
# from client import start_client  # Функция клиента

# Для тестирования мы определим функции здесь, чтобы не зависеть от внешних файлов
def do_something(data):
    """Пример функции для обработки данных."""
    return data  # Просто возвращаем данные (эхо-сервер)

class TestTCPServerFunctions(unittest.TestCase):
    """Тесты для функций сервера"""
    
    def test_do_something(self):
        """Тест функции обработки данных do_something"""
        test_data = b"Hello, Server!"
        result = do_something(test_data)
        self.assertEqual(result, test_data, "Функция do_something должна возвращать те же данные, которые получила")
        
        # Проверка на пустые данные
        empty_data = b""
        result = do_something(empty_data)
        self.assertEqual(result, empty_data, "Функция do_something должна корректно обрабатывать пустые данные")
        
        # Проверка на специальные символы
        special_chars = b"\n\t\r\x00\xff"
        result = do_something(special_chars)
        self.assertEqual(result, special_chars, "Функция do_something должна корректно обрабатывать специальные символы")

class MockServer(threading.Thread):
    """Мок-сервер для тестирования клиента"""
    
    def __init__(self, host='127.0.0.1', port=33333):
        super().__init__()
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = False
        self.client_socket = None
        
    def run(self):
        self.running = True
        self.server_socket.settimeout(1)
        
        while self.running:
            try:
                self.client_socket, _ = self.server_socket.accept()
                data = self.client_socket.recv(1024)
                if data:
                    # Эхо-ответ
                    self.client_socket.sendall(data)
                self.client_socket.close()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Ошибка в мок-сервере: {e}")
                break
                
    def stop(self):
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        self.server_socket.close()

class MockClient(threading.Thread):
    """Мок-клиент для тестирования сервера"""
    
    def __init__(self, host='127.0.0.1', port=33333, message="Test message"):
        super().__init__()
        self.host = host
        self.port = port
        self.message = message
        self.response = None
        self.error = None
        
    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.host, self.port))
                sock.sendall(self.message.encode('utf-8'))
                self.response = sock.recv(1024).decode('utf-8')
        except Exception as e:
            self.error = str(e)

class TestTCPServerIntegration(unittest.TestCase):
    """Интеграционные тесты для сервера"""
    
    @classmethod
    def setUpClass(cls):
        # Запускаем сервер в отдельном потоке
        cls.server_thread = threading.Thread(target=cls.run_server)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        # Даем серверу время на запуск
        time.sleep(1)
    
    @classmethod
    def tearDownClass(cls):
        # Освобождаем ресурсы
        pass
    
    @staticmethod
    def run_server():
        """Функция для запуска сервера в отдельном потоке"""
        HOST = ""
        PORT = 33334
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((HOST, PORT))
            srv.listen(5)
            srv.settimeout(1)
            
            while True:
                try:
                    sock, addr = srv.accept()
                    with sock:
                        sock.settimeout(1)
                        data = sock.recv(1024)
                        if data:
                            response = do_something(data)
                            sock.sendall(response)
                except socket.timeout:
                    continue
                except Exception:
                    break
    
    def test_server_echo(self):
        """Тест отправки сообщения на сервер и получения эхо-ответа"""
        client = MockClient(port=33334, message="Hello, Server!")
        client.start()
        client.join(timeout=5)
        
        self.assertIsNone(client.error, f"Клиент должен подключиться без ошибок, но получил: {client.error}")
        self.assertEqual(client.response, "Hello, Server!", "Сервер должен отправить эхо-ответ")
    
    def test_server_multiple_clients(self):
        """Тест обработки нескольких клиентов"""
        clients = []
        messages = ["Client 1", "Client 2", "Client 3"]
        
        for i, message in enumerate(messages):
            client = MockClient(port=33334, message=message)
            client.start()
            clients.append(client)
        
        # Ждем завершения всех клиентов
        for client in clients:
            client.join(timeout=5)
        
        # Проверяем результаты
        for i, client in enumerate(clients):
            self.assertIsNone(client.error, f"Клиент {i+1} должен подключиться без ошибок")
            self.assertEqual(client.response, messages[i], f"Сервер должен отправить правильный эхо-ответ клиенту {i+1}")

class TestTCPClientFunctions(unittest.TestCase):
    """Тесты для функций клиента"""
    
    def setUp(self):
        # Запускаем мок-сервер перед каждым тестом
        self.mock_server = MockServer()
        self.mock_server.start()
        time.sleep(0.5)  # Даем серверу время на запуск
    
    def tearDown(self):
        # Останавливаем мок-сервер после каждого теста
        self.mock_server.stop()
        self.mock_server.join(timeout=5)
    
    @patch('builtins.input', return_value='Test message')
    def test_client_connection(self, mock_input):
        """Тест подключения клиента к серверу"""
        # Перехватываем вывод в консоль
        captured_output = io.StringIO()
        
        # Для тестирования здесь определим функцию клиента, аналогичную той, что в вашем коде
        def start_client():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                try:
                    sock.connect(('127.0.0.1', 33333))
                    print(f"Установлено соединение с сервером 127.0.0.1:33333")
                    
                    message = input("Введите сообщение для отправки серверу: ")
                    print(f"Отправка данных серверу: {message}")
                    
                    sock.sendall(message.encode('utf-8'))
                    
                    data = sock.recv(1024)
                    print(f"Получено от сервера: {data.decode('utf-8')}")
                    
                except socket.error as e:
                    print(f"Ошибка при работе с сокетом: {e}")
                finally:
                    print("Соединение с сервером закрыто")
        
        with redirect_stdout(captured_output):
            start_client()
        
        output = captured_output.getvalue()
        
        # Проверяем, что клиент вывел нужные сообщения
        self.assertIn("Установлено соединение с сервером", output)
        self.assertIn("Отправка данных серверу: Test message", output)
        self.assertIn("Получено от сервера: Test message", output)
        self.assertIn("Соединение с сервером закрыто", output)
    
    @patch('builtins.input', return_value='')
    def test_client_empty_message(self, mock_input):
        """Тест отправки пустого сообщения"""
        captured_output = io.StringIO()
        
        def start_client():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                try:
                    sock.connect(('127.0.0.1', 33333))
                    print(f"Установлено соединение с сервером 127.0.0.1:33333")
                    
                    message = input("Введите сообщение для отправки серверу: ")
                    print(f"Отправка данных серверу: {message}")
                    
                    sock.sendall(message.encode('utf-8'))
                    
                    data = sock.recv(1024)
                    print(f"Получено от сервера: {data.decode('utf-8')}")
                    
                except socket.error as e:
                    print(f"Ошибка при работе с сокетом: {e}")
                finally:
                    print("Соединение с сервером закрыто")
        
        with redirect_stdout(captured_output):
            start_client()
        
        output = captured_output.getvalue()
        
        # Проверяем, что клиент вывел нужные сообщения даже при пустом сообщении
        self.assertIn("Установлено соединение с сервером", output)
        self.assertIn("Отправка данных серверу: ", output)
        self.assertIn("Получено от сервера: ", output)
        self.assertIn("Соединение с сервером закрыто", output)

if __name__ == '__main__':
    unittest.main()
