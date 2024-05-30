from ArbDatabase import DataManager


class Quality:
    def __init__(self, name: str, **kwargs):
        self.Name = name
        self.ArmorFactor = None
        self.DamageFactor = None
        self.InsulationFactor = None
        self.ValueFactor = None
        self.RollFactor = None

        self.data_manager = kwargs.get('data_manager', DataManager())
        data = self.fetch_data()

        if data:
            self.ArmorFactor = data.get('armor_factor', 0)
            self.DamageFactor = data.get('damage_factor', 0)
            self.InsulationFactor = data.get('insulation_factor', 0)
            self.ValueFactor = data.get('value_factor', 0)
            self.RollFactor = data.get('roll_factor', 0)

    def fetch_data(self) -> dict:
        if self.data_manager.select_dict('QUALITY_INIT', filter=f'name = "{self.Name}"') is None:
            return {}
        else:
            return self.data_manager.select_dict('QUALITY_INIT', filter=f'name = "{self.Name}"')[0]

    def __repr__(self):
        return f'({self.Name} качество)'