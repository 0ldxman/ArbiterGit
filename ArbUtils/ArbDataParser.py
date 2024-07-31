from ArbDatabase import DataManager

def get_owners_character(user_id:int):
  db = DataManager()
  return db.select_dict('META_INFO', filter=f'id = {user_id}')[0].get('playing_as', None)


class ListChunker:
  def __init__(self, items_per_chunk:int, input_list:list):
    self.items_per_chunk = items_per_chunk
    self.input_list = input_list
    self.chunks = self.chunk(self.input_list)

  def __repr__(self):
      return f"ListChunker(items_per_chunk={self.items_per_chunk})"

  def __str__(self):
    return f"ListChunker with {self.items_per_chunk} items per chunk"

  def __len__(self):
    """Возвращает количество подсписков, которые будут созданы"""
    return len(self.input_list) // self.items_per_chunk + (1 if len(self.input_list) % self.items_per_chunk != 0 else 0)

  def __iter__(self):
    self._index = 0
    return self

  def __next__(self):
    if self._index >= len(self.input_list):
      raise StopIteration
    chunk = self.chunks[self._index // self.items_per_chunk]
    self._index += self.items_per_chunk
    return chunk

  def chunk(self, input_list):
    """Разбивает input_list на подсписки с количеством элементов, равным items_per_chunk"""
    if self.items_per_chunk <= 0:
      raise ValueError("Количество элементов в подсписке должно быть больше нуля")
    self.input_list = input_list
    self.chunks = [input_list[i:i + self.items_per_chunk] for i in range(0, len(input_list), self.items_per_chunk)]
    return self.chunks

  def flatten(self, chunked_list):
    """Собирает разбитый список обратно в один список"""
    return [item for sublist in chunked_list for item in sublist]

  def set_items_per_chunk(self, new_items_per_chunk):
    """Устанавливает новое значение для items_per_chunk"""
    if new_items_per_chunk <= 0:
      raise ValueError("Количество элементов в подсписке должно быть больше нуля")
    self.items_per_chunk = new_items_per_chunk
    self.chunks = self.chunk(self.input_list)  # Обновляем подсписки после изменения items_per_chunk

  def get_items_per_chunk(self):
    """Возвращает текущее значение items_per_chunk"""
    return self.items_per_chunk

  def is_chunkable(self, input_list):
    """Проверяет, можно ли разбить список на подсписки"""
    return len(input_list) >= self.items_per_chunk

def process_string(input_string):
  # Разделить строку по запятой
  words = input_string.split(',')
  # Удалить пробелы и сделать каждое слово с заглавной буквы
  processed_words = [word.strip().title() for word in words]
  return processed_words


def string_to_list(input_string, delimiter=','):
    # Разбиваем строку по заданному разделителю
    elements = input_string.split(delimiter)

    # Удаляем лишние пробелы в каждом элементе
    cleaned_elements = [element.strip().title() for element in elements]

    return cleaned_elements