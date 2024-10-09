import csv
import faker
import os
from dataclasses import dataclass


class CSVWriter:
    @staticmethod
    def generate_name(gender):
        fake = faker.Faker('ru_RU')  # Создаем объект Faker для русскоязычных имен
        if gender.lower() == 'male':
            return fake.first_name_male()
        elif gender.lower() == 'female':
            return fake.first_name_female()
        else:
            raise ValueError("Invalid gender. Please specify 'male' or 'female'.")

    @classmethod
    def generate_and_write_names(cls, num_names, gender, file_name, folder_name='data_models'):
        generated_names = []
        existing_names = set()

        # Проверка наличия файла и считывание существующих имен
        folder_path = os.path.join(os.getcwd(), folder_name)
        file_path = os.path.join(folder_path, file_name)
        if os.path.exists(file_path):
            with open(file_path, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    existing_names.add(row[0].lower())

        # Генерация имен
        while len(generated_names) < num_names:
            name = cls.generate_name(gender)
            if name.lower() not in existing_names:
                generated_names.append(name)
                existing_names.add(name.lower())

        # Запись в CSV
        cls.write_list(generated_names, file_name)

    @staticmethod
    def write_list(data, file_name):
        with open(file_name, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            for item in data:
                writer.writerow([item])