import num2words
import text_to_num


class specnum:
    ROMAN_NUMERAL_MAP = {
        1: 'I', 4: 'IV', 5: 'V', 9: 'IX', 10: 'X', 40: 'XL',
        50: 'L', 90: 'XC', 100: 'C', 400: 'CD', 500: 'D', 900: 'CM', 1000: 'M'
    }

    def __init__(self, value):
        self.text_number = None
        self.number = None
        self.roman_number = None

        if isinstance(value, str):  # Если вход - строка
            if any(char.isdigit() for char in value):  # Если строка содержит цифры - преобразовываем
                self.text_number = value
                self.number = self.text_to_int(value)
                self.roman_number = self.int_to_roman(self.number)
            else:  # Иначе, проверяем, является ли строка римским числом
                if all(char.upper() in 'IVXLCDM' for char in value):
                    self.roman_number = value
                    self.number = self.roman_to_int(value)
                    self.text_number = self.int_to_text(self.number)
        elif isinstance(value, int):  # Если вход - число
            self.number = value
            self.text_number = self.int_to_text(value)
            self.roman_number = self.int_to_roman(value)


    def int_to_text(self, num: int = None):
        if num:
            return num2words.num2words(num, lang='ru')
        else:
            return None

    def text_to_int(self, text: str = None):
        if text:
            return text_to_num.text2num(text, lang='ru')
        else:
            return None
    def int_to_roman(self, num: int = None):
        if num:
            rom_num = ''
            for arabic_num, roman_numeral in sorted(self.ROMAN_NUMERAL_MAP.items(), key=lambda x: x[0], reverse=True):
                div_part = num // arabic_num
                rom_num += div_part * roman_numeral
                num -= div_part * arabic_num
            return rom_num
        else:
            return None

    def roman_to_int(self, rom_num: str = None):
        if not rom_num:
            return None

        result = 0
        i = 0
        while i < len(rom_num):
            if i + 1 < len(rom_num) and rom_num[i:i + 2] in self.ROMAN_NUMERAL_MAP.values():
                next_roman_numeral = rom_num[i:i + 2]
                for arabic_num, roman_numeral in self.ROMAN_NUMERAL_MAP.items():
                    if roman_numeral == next_roman_numeral:
                        result += arabic_num
                        i += 2
                        break
            else:
                current_roman_numeral = rom_num[i]
                for arabic_num, roman_numeral in self.ROMAN_NUMERAL_MAP.items():
                    if roman_numeral == current_roman_numeral:
                        result += arabic_num
                        i += 1
                        break

        return result

    def __str__(self):
        return f'{self.number} ({self.text_number}) ({self.roman_number})'

    def __repr__(self):
        return f'WordNumber[{self.number}, {self.text_number}, {self.roman_number}]'

    def __int__(self):
        return int(self.number)