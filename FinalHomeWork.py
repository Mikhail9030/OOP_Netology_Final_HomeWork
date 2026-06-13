import os
import time
import json
import logging
import requests
from tqdm import tqdm

# Настройка базового логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class YandexDisk:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://cloud-api.yandex.net/v1/disk/resources"
        self.headers = {
            "Authorization": f"OAuth {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def create_folder(self, folder_name: str) -> bool:
        """Создает папку на Яндекс.Диске."""
        params = {"path": folder_name}
        response = requests.put(self.base_url, headers=self.headers, params=params)

        if response.status_code == 201:
            logging.info(f"Папка '{folder_name}' успешно создана.")
            return True
        elif response.status_code == 409:
            logging.info(f"Папка '{folder_name}' уже существует.")
            return True
        else:
            logging.error(f"Ошибка создания папки: {response.json().get('message')}")
            return False

    def upload_from_url(self, source_url: str, dest_path: str) -> str:
        """Инициирует загрузку файла по URL и возвращает ссылку на статус операции."""
        upload_url = f"{self.base_url}/upload"
        params = {
            "url": source_url,
            "path": dest_path
        }
        response = requests.post(upload_url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json().get("href")

    def wait_for_operation(self, operation_url: str, timeout: int = 30) -> bool:
        """Ожидает завершения асинхронной операции на серверах Яндекса."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = requests.get(operation_url, headers=self.headers)
            response.raise_for_status()
            status = response.json().get("status")
            if status == "success":
                return True
            elif status == "failed":
                return False
            time.sleep(1)
        return False

    def get_file_info(self, file_path: str) -> dict:
        """Получает метаданные файла (включая размер)."""
        params = {"path": file_path}
        response = requests.get(self.base_url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()


def main():
    # 1. Сбор входных данных
    ya_token = input("Введите токен Яндекс.Диска: ").strip()
    group_name = input("Введите название вашей группы (для папки): ").strip()

    raw_texts = input("Введите тексты для картинок (через запятую): ")
    texts = [t.strip() for t in raw_texts.split(',') if t.strip()]

    if not texts:
        logging.warning("Вы не ввели ни одного текста для картинок. Программа завершена.")
        return

    # 2. Инициализация клиента Я.Диска и создание папки
    ya_disk = YandexDisk(ya_token)
    if not ya_disk.create_folder(group_name):
        return

    results = []

    # 3. Обработка каждой картинки с прогресс-баром
    print("\nНачинаем загрузку картинок 'по воздуху'...")
    for text in tqdm(texts, desc="Загрузка на Я.Диск"):
        cat_api_url = f"https://cataas.com/cat/says/{text}"
        file_name = f"{text}.jpg"
        disk_path = f"{group_name}/{file_name}"

        try:
            # Шаг 1: Инициируем загрузку (Яндекс сам скачает картинку по URL)
            operation_url = ya_disk.upload_from_url(cat_api_url, disk_path)

            # Шаг 2: Ждем, пока Яндекс скачает и сохранит файл
            if ya_disk.wait_for_operation(operation_url):
                # Шаг 3: Получаем информацию о файле, чтобы узнать его размер
                file_info = ya_disk.get_file_info(disk_path)
                file_size = file_info.get("size", 0)

                results.append({
                    "file_name": file_name,
                    "size": file_size
                })
            else:
                logging.error(f"Ошибка на стороне Яндекса при загрузке {file_name}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Сетевая ошибка при обработке '{text}': {e}")
        except Exception as e:
            logging.error(f"Непредвиденная ошибка при обработке '{text}': {e}")

    # 4. Сохранение результатов в JSON
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("\nГотово! Информация о файлах сохранена в results.json")


if __name__ == "__main__":
    main()