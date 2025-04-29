#код клиента:
import socket

HOST = "127.0.0.1"  # Адрес сервера
PORT = 33333        # Порт сервера

def start_client():
    # Создаем сокет
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            # Устанавливаем соединение с сервером
            sock.connect((HOST, PORT))
            print(f"Установлено соединение с сервером {HOST}:{PORT}")

            # Вводим сообщение с клавиатуры
            message = input("Введите сообщение для отправки серверу: ")
            print(f"Отправка данных серверу: {message}")

            # Отправляем данные серверу
            sock.sendall(message.encode('utf-8'))

            # Получаем ответ от сервера
            data = sock.recv(1024)
            print(f"Получено от сервера: {data.decode('utf-8')}")

        except socket.error as e:
            print(f"Ошибка при работе с сокетом: {e}")

        finally:
            print("Соединение с сервером закрыто")

if __name__ == "__main__":
    start_client()
