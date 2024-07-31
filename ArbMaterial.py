from ArbDatabase import DataManager, DataModel


class Material(DataModel):
    def __init__(self, id: str, **kwargs):
        self.material_id = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        super().__init__('MATERIALS', f'id = "{self.material_id}"', data_manager=self.data_manager)

        self.label = self.get('name','')
        self.type = self.get('type', '')
        self.market_value = self.get('market_value', 0)
        self.insulation_cold = self.get('insulation_cold', 0)
        self.insulation_heat = self.get('insulation_heat', 0)
        self.weapon_factor = self.get('weapon_factor', 0)
        self.rarity = self.get('rarity', False)
        self.biom = self.get('biome', '')
        self.disguise_factor = self.get('disguise_factor', 1)
        self.tier = self.get('tier', 0)
        self.adjective = self.get('adj', '')

    def protection_data(self) -> dict:
        protection_data = {}
        rows = self.data_manager.select_dict('MATERIALS_PROTECTION', filter=f'material_id = "{self.material_id}"')
        for row in rows:
            protection_id = row['protection_id']
            value = row['value']
            protection_data[protection_id] = value

        return protection_data

    def __repr__(self):
        return f'Material.{self.material_id}'

    def __str__(self):
        return self.label
