import uuid

# Генерируем UUID
uuid_str = str(uuid.uuid4())

# Преобразуем UUID в число
uuid_num = int(uuid_str.replace("-", ""), 16)
print(uuid_num)

import hashlib

# Ваш входной идентификатор
input_id = uuid_str

# Преобразуем строку в байтовый объект
input_bytes = input_id.encode()

# Используем хеш-функцию MD5 для получения хеша
hash_object = hashlib.md5(input_bytes)
hash_hex = hash_object.hexdigest()

# Преобразуем хеш в число
hash_int = int(hash_hex, 16)

# Получаем строки только с цифрами
digits = ''.join(filter(str.isdigit, str(hash_int)))

print("Только цифры из хеша:", digits[:4])

input_data = "your_input_data"

# Преобразуем данные в байтовый объект
data_bytes = input_data.encode()

# Используем хеш-функцию SHA-256 для получения хеша
hash_object = hashlib.sha256(data_bytes)
hash_hex = hash_object.hexdigest()

# Преобразуем хеш в число
hash_int = int(hash_hex, 16)

# Получаем строки только с цифрами
id_from_data = ''.join(filter(str.isdigit, str(hash_int)))

print("Идентификатор из данных:", id_from_data)