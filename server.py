#код сервера:
import socket

HOST = ""  # Пустая строка означает, что сервер будет слушать все доступные интерфейсы
PORT = 33333

TYPE = socket.AF_INET
PROTOCOL = socket.SOCK_STREAM

def do_something(data):
    """Пример функции для обработки данных."""
    return data  # Просто возвращаем данные (эхо-сервер)

# Создаем сокет
srv = socket.socket(TYPE, PROTOCOL)
srv.bind((HOST, PORT))
srv.listen(5)  # Очередь из 5 подключений, в лекции сказано, что 1 мало
print(f"Сервер запущен и слушает порт {PORT}")

try:
    while True:
        print("Ожидание подключения клиента...")
        sock, addr = srv.accept()
        print(f"Подключен клиент: {addr}")

        try:
            sock.settimeout(5.0)  # Устанавливаем тайм-аут для операций с клиентом
            while True:
                try:
                    data = sock.recv(1024)  # Получаем данные от клиента
                    if not data:
                        print(f"Клиент {addr} отключился")
                        break
                    print(f"Получено от {addr}: {data.decode('utf-8')}")

                    # Обрабатываем данные
                    response = do_something(data)
                    sock.sendall(response)  # Отправляем данные обратно клиенту
                    print(f"Отправлено {addr}: {response.decode('utf-8')}")

                except socket.timeout:
                    print(f"Клиент {addr} не отправил данные в течение 5 секунд")
                    break

        finally:
            sock.close()
            print(f"Соединение с клиентом {addr} закрыто")

except KeyboardInterrupt:
    print("Сервер остановлен по запросу пользователя")

finally:
    srv.close()
    print("Сервер завершил работу")
