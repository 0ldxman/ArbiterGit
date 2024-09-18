import random
from ArbDatabase import Logger
from dataclasses import dataclass

roll_loger = Logger()


class Roll:
    def __init__(self, skill: int, char: int, cap: int, a_char: int = None, a_cap: int = None, stack_chars: bool = None, pain: int = None):
        self.logger = roll_loger

        self.max_dice = max(0, 100 + (skill - 50))

        self.max_char_bonus = max(0, (char - 20) // 2)

        self.pain_factor = 1 - ((pain - 10) / 2.25) / 100 if pain and pain > 10 else 1

        self.max_a_char_bonus = max(0, (a_char - 20) // 2) if a_char else self.max_char_bonus

        self.max_char_bonus_total = self.max_char_bonus + self.max_a_char_bonus if stack_chars and a_char else max(self.max_char_bonus, self.max_a_char_bonus)

        self.cap_koef = cap / 100

        self.a_cap_koef = a_cap / 100 if a_cap else 1

        self.dice = -1
        self.dice = self.calculate_dice()
        self.log_result()

    def calculate_dice(self):
        return (random.randint(0, self.max_dice) + random.randint(min(0, self.max_char_bonus_total), max(0, self.max_char_bonus_total))) * self.cap_koef * self.a_cap_koef * self.pain_factor

    def log_result(self):
        self.logger.info(f'Current dice value: {self.dice}')

    def checkDif(self, difficulty: int):
        result = self.dice >= difficulty
        self.logger.info(f'CheckDif: Dice value {self.dice}, difficulty {difficulty}, result {result}')
        return result

    def reRoll(self, n: int = 1):
        for _ in range(n):
            self.calculate_dice()
        return self.dice

    def cache_result(self):
        self.cached_result = self.dice
        self.logger.info(f'Result cached: {self.cached_result}')

    def modify_result(self, modifier):
        if modifier is not None:
            self.dice += modifier
            self.logger.info(f'Result modified by {modifier}: {self.dice}')

    def get_cached_result(self):
        if hasattr(self, 'cached_result'):
            self.logger.info(f'Cached result retrieved: {self.cached_result}')
            return self.cached_result
        else:
            self.logger.warning('No cached result available')
            return None

    def __repr__(self):
        return str(self.dice)

    def __str__(self):
        return str(self.dice)

    def __lt__(self, other):
        return self.dice < other

    def __le__(self, other):
        return self.dice <= other

    def __eq__(self, other):
        return self.dice == other

    def __ne__(self, other):
        return self.dice != other

    def __ge__(self, other):
        return self.dice >= other

    def __gt__(self, other):
        return self.dice > other


class RollSkill:
    def __init__(self, skill_value:int, **kwargs):
        self.baff = kwargs.get('buff', 0)
        self.max_roll = max(0, 50 + skill_value)

        self.min_roll = 0 + kwargs.get('min_bonus',0)

        pain = kwargs.get('pain', 0)
        self.pain_factor = 1 - ((pain - 10) / 2.25) / 100 if kwargs.get('pain', None) and pain > 10 else 1

        char = kwargs.get('characteristic_value', None)
        self.max_char_roll = max(0, (char - 20) // 2) if kwargs.get('characteristic_value', None) else 0

        a_char = kwargs.get('add_characteristic_value', None)
        self.max_add_char_roll = max(0, (a_char - 20) // 2) if a_char else self.max_char_roll

        self.max_char_bonus = self.max_char_roll + self.max_add_char_roll if kwargs.get('stack_chars', False) and a_char else max(self.max_char_roll, self.max_add_char_roll)

        cap = kwargs.get('capacity_value', 100) if 'capacity_value' in kwargs else 100
        self.cap_koef = cap / 100

        a_cap = kwargs.get('add_capacity_value', None)
        self.a_cap_koef = a_cap / 100 if a_cap else 1

        self.dice = self.roll_dice()

    def roll_dice(self):
        return round((random.randint(self.min_roll, self.max_roll) + random.randint(min(0, self.max_char_roll), max(0, self.max_char_bonus))) * self.cap_koef * self.a_cap_koef * self.pain_factor + self.baff)

    def reroll_dice(self, n:int):
        for _ in range(n):
            self.dice = self.roll_dice()

        return self.dice

    def check_difficulty(self, difficulty:int):
        return difficulty <= self.dice

    def check_critical_modifier(self):
        crit_barrier = self.max_roll * 0.9
        return 1 + (10 * (self.dice - crit_barrier) / self.max_roll) if self.dice > crit_barrier else 1

    def roll_characteristic(self, difficulty: int):
        attributes = {'crit_pos': round((self.dice - self.max_roll*0.9) / self.max_roll, 2),
                      'pos': round((self.dice - difficulty) / self.max_roll, 2),
                      #'neu': round((self.dice - difficulty) / self.max_roll, 2),
                      'neg': round((difficulty - self.dice) / self.max_roll, 2),
                      'crit_neg': round((self.max_roll * 0.1 - self.dice) / self.max_roll, 2)}

        return attributes

    def __str__(self):
        return f'SkillRoll({self.dice})'

    def __lt__(self, other):
        return self.dice < other

    def __le__(self, other):
        return self.dice <= other

    def __eq__(self, other):
        return self.dice == other

    def __ne__(self, other):
        return self.dice != other

    def __ge__(self, other):
        return self.dice >= other

    def __gt__(self, other):
        return self.dice > other


class RollCharacteristic:
    def __init__(self, char_value:int, **kwargs):
        self.max_roll = char_value + kwargs.get('max_roll_bonus', 0)
        self.min_roll = 0 + kwargs.get('min_roll_bonus', 0)

        pain = kwargs.get('pain', 0)
        self.pain_factor = 1 - ((pain - 10) / 2.25) / 100 if kwargs.get('pain', None) and pain > 10 else 1

        self.dice = self.roll_dice()

    def roll_dice(self):
        return random.randint(self.min_roll, self.max_roll) * self.pain_factor

    def reroll_dice(self, n:int):
        for _ in range(n):
            self.dice = self.roll_dice()
        return self.dice

    def check_difficulty(self, difficulty:int):
        return difficulty <= self.dice

    def check_crit(self):
        crit_barrier = self.max_roll * 0.9
        return self.dice > crit_barrier

    def roll_characteristic(self, difficulty: int):
        attributes = {'crit_pos': round((self.dice - self.max_roll*0.9) / self.max_roll, 2),
                      'pos': round((self.dice - difficulty) / self.max_roll, 2),
                      #'neu': round((self.dice - difficulty) / self.max_roll, 2),
                      'neg': round((difficulty - self.dice) / self.max_roll, 2),
                      'crit_neg': round((self.max_roll * 0.1 - self.dice) / self.max_roll, 2)}

        return attributes

    def __lt__(self, other):
        return self.dice < other

    def __le__(self, other):
        return self.dice <= other

    def __eq__(self, other):
        return self.dice == other

    def __ne__(self, other):
        return self.dice != other

    def __ge__(self, other):
        return self.dice >= other

    def __gt__(self, other):
        return self.dice > other

    def __str__(self):
        return f'CharRoll({self.dice})'


class RollCapacity:
    def __init__(self, capacity_value, **kwargs):
        self.max_roll = capacity_value + kwargs.get('max_roll_bonus', 0)
        self.min_roll = max(0, capacity_value - 50) + kwargs.get('min_roll_bonus', 0)

        pain = kwargs.get('pain', 0)
        self.pain_factor = 1 - ((pain - 10) / 2.25) / 100 if kwargs.get('pain', None) and pain > 10 else 1

        self.dice = self.roll_dice()

    def roll_dice(self):
        return random.randint(self.min_roll, self.max_roll) * self.pain_factor

    def reroll_dice(self, n: int):
        for _ in range(n):
            self.dice = self.roll_dice()
        return self.dice

    def check_difficulty(self, difficulty: int):
        return difficulty <= self.dice

    def check_crit(self):
        crit_barrier = 90
        return self.dice > crit_barrier

    def roll_characteristic(self, difficulty: int):
        attributes = {'crit_pos': round((self.dice - self.max_roll * 0.9) / self.max_roll, 2),
                      'pos': round((self.dice - difficulty) / self.max_roll, 2),
                      # 'neu': round((self.dice - difficulty) / self.max_roll, 2),
                      'neg': round((difficulty - self.dice) / self.max_roll, 2),
                      'crit_neg': round((self.max_roll * 0.1 - self.dice) / self.max_roll, 2)}

        return attributes

    def __lt__(self, other):
        return self.dice < other

    def __le__(self, other):
        return self.dice <= other

    def __eq__(self, other):
        return self.dice == other

    def __ne__(self, other):
        return self.dice != other

    def __ge__(self, other):
        return self.dice >= other

    def __gt__(self, other):
        return self.dice > other

    def __str__(self):
        return f'CapacityRoll({self.dice})'


@dataclass()
class TargetRoll:
    id: int
    roll: int

    def __eq__(self, other):
        return self.roll == other.roll

    def __ne__(self, other):
        return self.roll != other.roll

    def __lt__(self, other):
        return self.roll < other.roll

    def __le__(self, other):
        return self.roll <= other.roll

    def __gt__(self, other):
        return self.roll > other.roll

    def __ge__(self, other):
        return self.roll >= other.roll


class RollCheck:
    def __init__(self, sides: int, modifiers: tuple[float] = None):
        self.sides = sides
        self.modifiers = modifiers if modifiers else []
        self.result = self.roll()

        self.is_critical = self.check_critical_success()
        self.crit_modifier = self.check_critical_modifier()

    def roll(self) -> int:
        c_roll = random.randint(1, self.sides)
        for modifier in self.modifiers:
            c_roll *= modifier if modifier is not None else 1

        return int(round(c_roll))

    def check_critical_success(self) -> bool:
        return self.result >= self.sides * 0.9

    def check_critical_failure(self) -> bool:
        return self.result <= self.sides * 0.1

    def check_critical_modifier(self):
        crit_barrier = self.sides * 0.9
        return 1 + (10 * (self.result - crit_barrier) / self.result) if self.result > crit_barrier else 1

    def __repr__(self):
        return f'SkillCheck({self.sides}, result={self.result})'

    def __str__(self):
        return f'Кубик d{self.sides}\n' \
               f'**Выпало:** {self.result} {f"(Критический успех!)" if self.is_critical else ""}'