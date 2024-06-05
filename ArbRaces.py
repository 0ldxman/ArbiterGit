from ArbDatabase import DataManager
from ArbHealth import BodyPart

class Race:
    def __init__(self, id: str, data_manager: DataManager = None):
        self.ID = id
        if data_manager is None:
            self.data_manager = DataManager()  # Создание экземпляра DataManager по умолчанию
        else:
            self.data_manager = data_manager
        race_data = self.load_race_information()

        self.Name = race_data.get('name')
        self.Type = race_data.get('type')
        self.Rare = race_data.get('rare')
        self.Size = race_data.get('size')
        self.IsPrimitive = race_data.get('primitive') == 1
        self.IsRobot = race_data.get('is_robot') == 1
        self.PainLimit = race_data.get('pain_limit')
        self.PainFactor = race_data.get('pain_factor')
        self.Blood = race_data.get('blood')
        self.StressFactor = race_data.get('stress_factor')
        self.Pregnancy = race_data.get('pregnancy')
        self.Fertility = race_data.get('fertilit')
        self.NatureDisguise = race_data.get('disguise')

        self.body_parts = self.fetch_bodyparts()
        self.parent_part = self.data_manager.selectOne("RACES_BODY", columns="part_id", filter=f'race = "{self.ID}" AND linked is NULL')[0]

    def load_race_information(self):
        race_data = self.data_manager.select_dict('RACES_INIT', '*', f'id = "{self.ID}"')[0]
        return race_data

    def fetch_bodyparts(self):
        body_parts = []
        # Получаем список частей тела для данной расы из таблицы RACES_BODY
        body_parts_data = self.data_manager.select("RACES_BODY", columns="part_id", filter=f'race = "{self.ID}"')

        for part_id in body_parts_data:
            part = BodyPart(part_id[0], data_manager=self.data_manager) # Используем оригинальную часть тела
            body_parts.append(part)

        return body_parts