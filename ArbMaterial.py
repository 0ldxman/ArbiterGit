from ArbDatabase import DataManager


class Material:
    def __init__(self, id: str, **kwargs):
        self.ID = id
        self.data_manager = kwargs.get('data_manager', DataManager())

        data = self.fetch_data()
        self.Name = data.get('name','')
        self.Type = data.get('type', '')
        self.MarketValue = data.get('market_value', 0)
        self.InsulationCold = data.get('insulation_cold', 0)
        self.InsulationHeat = data.get('insulation_heat', 0)
        self.WeaponFactor = data.get('weapon_factor', 0)
        self.Rare = data.get('rarity', False)
        self.Biom = data.get('biome', '')
        self.DisguiseFactor = data.get('disguise_factor')

    def fetch_data(self) -> dict:
        if self.data_manager.select_dict('MATERIALS',filter=f'id = "{self.ID}"') is None:
            return {}
        else:
            return self.data_manager.select_dict('MATERIALS', filter=f'id = "{self.ID}"')[0]

    def protection_data(self) -> dict:
        protection_data = {}
        rows = self.data_manager.select_dict('MATERIALS_PROTECTION', filter=f'material_id = "{self.ID}"')
        for row in rows:
            protection_id = row['protection_id']
            value = row['value']
            protection_data[protection_id] = value

        return protection_data

    def __repr__(self):
        return f'Material.{self.ID}'

    def __str__(self):
        return self.Name
