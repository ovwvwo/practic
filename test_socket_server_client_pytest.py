import socket
import threading
import time
import pytest
from unittest.mock import patch, MagicMock
import io
from contextlib import redirect_stdout

# Импортируем функции из основных файлов или определяем их здесь для тестирования
def do_something(data):
    """Пример функции для обработки данных."""
    return data  # Просто возвращаем данные (эхо-сервер)

# Мок-сервер для тестирования клиента
class MockServer(threading.Thread):
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

# Мок-клиент для тестирования сервера
class MockClient(threading.Thread):
    def __init__(self, host='127.0.0.1', port=33334, message="Test message"):
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

# Функция для запуска сервера в отдельном потоке
def run_server():
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

# Функция клиента для тестирования
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

# Фикстура для запуска сервера перед тестами
@pytest.fixture(scope="module")
def server_fixture():
    # Запускаем сервер в отдельном потоке
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    # Даем серверу время на запуск
    time.sleep(1)
    
    yield
    
    # Освобождаем ресурсы после тестов
    pass

# Фикстура для запуска мок-сервера перед каждым тестом клиента
@pytest.fixture
def mock_server_fixture():
    # Запускаем мок-сервер
    mock_server = MockServer()
    mock_server.start()
    time.sleep(0.5)  # Даем серверу время на запуск
    
    yield mock_server
    
    # Останавливаем мок-сервер после теста
    mock_server.stop()
    mock_server.join(timeout=5)

# Тест функции обработки данных
def test_do_something():
    """Тест функции обработки данных do_something"""
    test_data = b"Hello, Server!"
    result = do_something(test_data)
    assert result == test_data, "Функция do_something должна возвращать те же данные, которые получила"
    
    # Проверка на пустые данные
    empty_data = b""
    result = do_something(empty_data)
    assert result == empty_data, "Функция do_something должна корректно обрабатывать пустые данные"
    
    # Проверка на специальные символы
    special_chars = b"\n\t\r\x00\xff"
    result = do_something(special_chars)
    assert result == special_chars, "Функция do_something должна корректно обрабатывать специальные символы"

# Тест отправки сообщения на сервер и получения эхо-ответа
def test_server_echo(server_fixture):
    """Тест отправки сообщения на сервер и получения эхо-ответа"""
    client = MockClient(port=33334, message="Hello, Server!")
    client.start()
    client.join(timeout=5)
    
    assert client.error is None, f"Клиент должен подключиться без ошибок, но получил: {client.error}"
    assert client.response == "Hello, Server!", "Сервер должен отправить эхо-ответ"

# Тест обработки нескольких клиентов
def test_server_multiple_clients(server_fixture):
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
        assert client.error is None, f"Клиент {i+1} должен подключиться без ошибок"
        assert client.response == messages[i], f"Сервер должен отправить правильный эхо-ответ клиенту {i+1}"

# Тест подключения клиента к серверу
@patch('builtins.input', return_value='Test message')
def test_client_connection(mock_input, mock_server_fixture):
    """Тест подключения клиента к серверу"""
    # Перехватываем вывод в консоль
    captured_output = io.StringIO()
    
    with redirect_stdout(captured_output):
        start_client()
    
    output = captured_output.getvalue()
    
    # Проверяем, что клиент вывел нужные сообщения
    assert "Установлено соединение с сервером" in output
    assert "Отправка данных серверу: Test message" in output
    assert "Получено от сервера: Test message" in output
    assert "Соединение с сервером закрыто" in output

# Тест отправки пустого сообщения
@patch('builtins.input', return_value='')
def test_client_empty_message(mock_input, mock_server_fixture):
    """Тест отправки пустого сообщения"""
    captured_output = io.StringIO()
    
    with redirect_stdout(captured_output):
        start_client()
    
    output = captured_output.getvalue()
    
    # Проверяем, что клиент вывел нужные сообщения даже при пустом сообщении
    assert "Установлено соединение с сервером" in output
    assert "Отправка данных серверу: " in output
    assert "Получено от сервера: " in output
    assert "Соединение с сервером закрыто" in output
