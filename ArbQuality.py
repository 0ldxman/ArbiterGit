from ArbDatabase import DataManager, DataModel


class Quality(DataModel):
    def __init__(self, label: str, **kwargs):
        self.label = label
        self.data_manager = kwargs.get('data_manager', DataManager())
        super().__init__('QUALITY_INIT', f'name = "{self.label}"', data_manager=self.data_manager)

        self.armor_factor = self.get('armor_factor', 0)
        self.damage_factor = self.get('damage_factor', 0)
        self.insulation_factor = self.get('insulation_factor', 0)
        self.value_factor = self.get('value_factor', 0)
        self.roll_factor = self.get('roll_factor', 0)

    def __repr__(self):
        return f'({self.label} качество)'