import discord
from discord.ext import commands
from ArbUIUX import SuccessEmbed, ErrorEmbed
from ArbDatabase import DataManager, DataModel
from ArbHealth import Body, BodyElement, BodyPart, Implant, ImplantType, Injury, DiseaseType, Disease
from ArbBattle import BattleTeam, Battlefield, Layer, GameObject, Actor


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print(f'...Module {self.__class__.__name__} is ready')

    battle_com = discord.SlashCommandGroup("battle", "Команды управления боем")
    layer_com = discord.SlashCommandGroup("layers", "Команды управления слоями поля боя")
    object_com = discord.SlashCommandGroup("objects", "Команды управления объектами поля боя")
    trap_com = discord.SlashCommandGroup("traps", "Команды управления ловушками поля боя")
    team_com = discord.SlashCommandGroup("team", "Команды управления командами поля боя")
    sound_com = discord.SlashCommandGroup("sound", "Команды управления командами поля боя")

    async def body_parts(ctx: discord.AutocompleteContext):
        """
        Here we will check if 'ctx.options['animal_type']' is a marine or land animal and return respective option choices
        """
        character = ctx.options['character_id']
        body = Body(character).body_parts
        print([part.ID for part in body if part.ID != 'Destroyed'])
        return [part.Label for part in body if part.ID != 'Destroyed']

    async def damage_types(self):
        db = DataManager()
        return [dam_type.get('id') for dam_type in db.select_dict('DAMAGE_TYPE')]

    async def time_types(self):
        db = DataManager()
        return [time_type['label'] for time_type in db.select_dict('DAYTIME_CONDS')]

    async def weather_types(self):
        db = DataManager()
        return [time_type['label'] for time_type in db.select_dict('WEATHER_CONDS')]

    async def battle_types(self):
        db = DataManager()
        return [t.get('label') for t in db.select_dict('BATTLE_CONDITIONS') if t.get('id') is not None]

    async def terrain_types(self):
        db = DataManager()
        return [t.get('label') for t in db.select_dict('TERRAIN_TYPE') if t.get('id') is not None]

    async def team_roles(self):
        db = DataManager()
        return [t.get('label') for t in db.select_dict('TEAM_ROLES') if t.get('id') is not None]

    async def races(self):
        db = DataManager()
        return [t.get('name') for t in db.select_dict('RACES_INIT') if t.get('id') is not None]

    async def org_id(self):
        db = DataManager()
        return [t.get('id') for t in db.select_dict('ORG_INIT') if t.get('id') is not None]

    async def object_type(self):
        db = DataManager()
        return [t.get('label') for t in db.select_dict('OBJECT_TYPE') if t.get('label') is not None]

    async def traps_type(self):
        db = DataManager()
        return [t.get('label') for t in db.select_dict('TRAPS_INIT') if t.get('label') is not None]

    async def sound_types(self):
        db = DataManager()
        return [t.get('label') for t in db.select_dict('SOUNDS') if t.get('label') is not None]

    def get_time_id_by_label(self, label:str):
        db = DataManager()
        if db.check('DAYTIME_CONDS', filter=f'label = "{label}"'):
            return db.select_dict('DAYTIME_CONDS', filter=f'label = "{label}"')[0].get('id')
        else:
            return 'Day'

    def get_weather_id_by_label(self, label:str):
        db = DataManager()
        if db.check('WEATHER_CONDS', filter=f'label = "{label}"'):
            return db.select_dict('WEATHER_CONDS', filter=f'label = "{label}"')[0].get('id')
        else:
            return 'Sunny'

    def get_battletype_id_by_label(self, label:str):
        db = DataManager()
        if db.check('BATTLE_CONDITIONS', filter=f'label = "{label}"'):
            return db.select_dict('BATTLE_CONDITIONS', filter=f'label = "{label}"')[0].get('id')
        else:
            return 'Overkill'

    def get_teamrole_id_by_label(self, label:str):
        db = DataManager()
        if db.check('TEAM_ROLES', filter=f'label = "{label}"'):
            return db.select_dict('TEAM_ROLES', filter=f'label = "{label}"')[0].get('id')
        else:
            return 'Participants'

    def get_race_id_by_label(self, label:str):
        db = DataManager()
        if db.check('RACES_INIT', filter=f'name = "{label}"'):
            return db.select_dict('RACES_INIT', filter=f'name = "{label}"')[0].get('id')
        else:
            return 'Human'

    def get_terrain_type_by_label(self, label:str):
        db = DataManager()
        if db.check('TERRAIN_TYPE', filter=f'label = "{label}"'):
            return db.select_dict('TERRAIN_TYPE', filter=f'label = "{label}"')[0].get('id')
        else:
            return 'Field'

    def get_object_type_by_label(self, label:str):
        db = DataManager()
        print(label, )
        if db.check('OBJECT_TYPE', filter=f'label = "{label}"'):
            return db.select_dict('OBJECT_TYPE', filter=f'label = "{label}"')[0].get('object_id')
        else:
            return 'Tree'

    def get_trap_type_by_label(self, label:str):
        db = DataManager()
        print(label)
        if db.check('TRAPS_INIT', filter=f'label = "{label}"'):
            return db.select_dict('TRAPS_INIT', filter=f'label = "{label}"')[0].get('id')
        else:
            return 'APM'

    def get_sound_type_by_label(self, label:str):
        db = DataManager()
        print(label)
        if db.check('SOUNDS', filter=f'label = "{label}"'):
            return db.select_dict('SOUNDS', filter=f'label = "{label}"')[0].get('id')
        else:
            return 'Click'

    async def teams_id(ctx: discord.AutocompleteContext):
        """
        Here we will check if 'ctx.options['animal_type']' is a marine or land animal and return respective option choices
        """
        character = ctx.options['battle_id']
        battle = Battlefield(character)

        print([team_id for team_id in battle.fetch_teams()])
        return [f'{team_id.id} ({team_id.label})' for team_id in battle.fetch_teams()]



    async def attacks(ctx):
        db = DataManager()
        attack_type = ctx.options['attack_type']
        if attack_type == 'Огнестрельная':
            attacks_list = [weapon.get('id') for weapon in db.select_dict('WEAPONS', filter='class != "ColdSteel"')]
        elif attack_type == 'Ближняя':
            attacks_list = [weapon.get('id') for weapon in db.select_dict('WEAPONS')]
        elif attack_type == 'Расовая':
            attacks_list = [attack.get('id') for attack in db.select_dict('RACES_MELEE')]
        elif attack_type == 'Взрыв' or attack_type == 'Осколки':
            attacks_list = [attack.get('id') for attack in db.select_dict('AMMO',filter='caliber = "Граната"')]
        return attacks_list

    @commands.slash_command(name="recieve_damage")
    @commands.has_permissions(manage_channels=True)
    async def simulate_damage(self,
            ctx: discord.ApplicationContext,
            character_id: discord.Option(int),
            body_part: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(body_parts)),
            damage_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(damage_types)),
            damage: discord.Option(int),
            root: discord.Option(str, required=False)
    ):
        body = Body(character_id).body_parts
        part = None
        for i in body:
            if i.Label == body_part:
                part = i

        c_damage = Damage(damage, damage_type, root=root)
        part.apply_damage(c_damage, True)

        await ctx.respond(f'{character_id} получил {damage} ({damage_type}) в {body_part}')

    @commands.slash_command(name='simulate_attack')
    @commands.has_permissions(manage_channels=True)
    async def simulate_attack(self,
                              ctx: discord.ApplicationContext,
                              character_id: discord.Option(int),
                              attack_type: discord.Option(str, choices=['Огнестрельная', 'Ближняя', 'Расовая', 'Взрыв',
                                                                        'Осколки']),
                              weapon: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(attacks)),
                              attacks: discord.Option(int),
                              body_part: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(body_parts), required=False),
                                ):

        from ArbAttacks import CombatManager
        from ArbWeapons import RangeWeapon, MeleeWeapon
        from ArbAmmo import Grenade
        from ArbHealth import RaceAttack

        cm = CombatManager()

        if body_part:
            body = Body(character_id).body_parts
            part = None
            for i in body:
                if i.Label == body_part:
                    part = i
        else:
            part = None

        total_damage = []

        attack_label = ''
        attaker = ''

        if attack_type == 'Огнестрельная':
            attack_label = 'огнестрельной'
            c_weapon = RangeWeapon(weapon)
            attaker = c_weapon.Name
            for _ in range(attacks):
                damage_dict = c_weapon.range_damage()
                n_damage = cm.calculate_total_damage(damage_dict, character_id, part_id=part.ID) if part is not None else cm.calculate_total_damage(damage_dict, character_id)
                total_damage += n_damage

        elif attack_type == 'Ближняя':
            attack_label = 'ближней'
            c_weapon = MeleeWeapon(weapon)
            attaker = c_weapon.Name
            for _ in range(attacks):
                damage_dict = c_weapon.melee_damage()
                n_damage = cm.calculate_total_damage(damage_dict, character_id, part_id=part.ID) if part is not None else cm.calculate_total_damage(damage_dict, character_id)
                total_damage += n_damage

        elif attack_type == 'Взрыв':
            attack_label = 'взрывной'
            c_weapon = Grenade(weapon)
            attaker = c_weapon.name
            for _ in range(attacks):
                damage_dict = c_weapon.detonate()['main_damage']
                n_damage = cm.calculate_total_damage(damage_dict, character_id, part_id=part.ID) if part is not None else cm.calculate_total_damage(damage_dict, character_id)
                total_damage += n_damage

        elif attack_type == 'Осколки':
            attack_label = 'взрывной'
            c_weapon = Grenade(weapon)
            attaker = c_weapon.name
            for _ in range(attacks):
                damage_dict = c_weapon.detonate()['fragments_damage']
                n_damage = cm.calculate_total_damage(damage_dict, character_id, part_id=part.ID) if part is not None else cm.calculate_total_damage(damage_dict, character_id)
                total_damage += n_damage

        elif attack_type == 'Расовая':
            attack_label = 'естественной'
            c_weapon = RaceAttack(weapon)
            attaker = c_weapon.name
            for _ in range(attacks):
                damage_dict = c_weapon.attack()
                n_damage = cm.calculate_total_damage(damage_dict, character_id, part_id=part.ID) if part is not None else cm.calculate_total_damage(damage_dict, character_id)
                total_damage += n_damage

        desc = f'{InterCharacter(character_id).name} подвергается {attack_label} атаке! ({attaker})'

        if total_damage:
            cm.recive_damage(character_id, total_damage, apply_effect=True)


        embed = ErrorEmbed(title='Атака',
                           desc=f'{desc}')

        await ctx.respond('', embed=embed)

    @commands.slash_command(name='execute')
    @commands.has_permissions(administrator=True)
    async def execute(self, ctx, command:str):
        try:
            exec(command)
            embed = SuccessEmbed('Команда выполнена успешно!', f'Команда ``{command}`` была успешно выполнена!')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed('Ошибка!',f'При исполнении команды произошла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @battle_com.command(name='generate_battle')
    @commands.has_permissions(administrator=True)
    async def generate_battle(self, ctx,
                              time: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(time_types), required=False),
                              weather: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(weather_types), required=False),
                              battle_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(battle_types), required=False),
                              layers_value: discord.Option(int, required=False),
                              battle_type_value: discord.Option(str, required=False),
                              distance_delta: discord.Option(int, required=False),
                              key_round: discord.Option(int, required=False),
                              last_round: discord.Option(int, required=False),
                              title: discord.Option(str, required=False),
                              description: discord.Option(str, required=False),
                              layers_types: discord.Option(str, required=False)):

        input = {}

        if layers_value:
            input['layers'] = layers_value

        if time:
            cur_time = self.get_time_id_by_label(time)
            input['time'] = cur_time

        if weather:
            cur_weather = self.get_weather_id_by_label(weather)
            input['weather'] = cur_weather

        if battle_type:
            cur_type = self.get_battletype_id_by_label(battle_type)
            input['type'] = cur_type

        if battle_type_value:
            input['type_value'] = battle_type_value

        if distance_delta:
            input['delta'] = distance_delta

        if key_round:
            input['key_round'] = key_round

        if last_round:
            input['last_round'] = last_round

        if title:
            input['label'] = title

        if description:
            input['desc'] = description

        if layers_types:
            cur_terrains = process_string(layers_types)
            input['available_types'] = cur_terrains
        else:
            input['available_types'] = ['Природный']

        print(input)

        new_battle = GenerateBattle(**input)

        try:
            new_battle.insert_data()
            embed = SuccessEmbed('Создание поля боя', f'Поле боя ``id:{new_battle.id} | {new_battle.label}`` было успешно создано!\nКоличество слоев: ``{len(new_battle.layers)}``')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed('Создание поля боя', f'При создании поля боя возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @battle_com.command(name='manage_battle')
    @commands.has_permissions(administrator=True)
    async def manage_battle(self, ctx, battle_id: discord.Option(int),
                            time: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(time_types), required=False),
                            weather: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(weather_types), required=False),
                            battle_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(battle_types), required=False),
                            label: discord.Option(str, required=False),
                            distance: discord.Option(int, required=False),
                            description: discord.Option(str, required=False),
                            round: discord.Option(int, required=False),
                            key_round: discord.Option(int, required=False),
                            last_round: discord.Option(int, required=False),
                            battle_type_value: discord.Option(str, required=False)):

        battle = Battlefield(battle_id)

        change_log = ''

        input = {}

        if time:
            cur_time = self.get_time_id_by_label(time)
            input['time'] = cur_time
            change_log += f'\n Время: {time}'

        if weather:
            cur_weather = self.get_weather_id_by_label(weather)
            input['weather'] = cur_weather
            change_log += f'\n Погода: {weather}'

        if battle_type:
            cur_type = self.get_battletype_id_by_label(battle_type)
            input['type'] = cur_type
            change_log += f'\n Тип боя: {battle_type}'

        if battle_type_value:
            input['type_value'] = battle_type_value
            change_log += f'\n Условие типа боя: {battle_type_value}'

        if distance:
            input['distance'] = distance
            change_log += f'\n Расстояние между слоями: {distance}'

        if round:
            input['round'] = round
            change_log += f'\n Текущий раунд: {round}'

        if key_round:
            input['key_round'] = key_round
            change_log += f'\n Ключевые раунды каждые: {key_round}'

        if last_round:
            input['last_round'] = last_round
            change_log += f'\n Последний раунд: {last_round}'

        if label:
            input['label'] = label
            change_log += f'\n Название боя: {label}'

        if description:
            input['desc'] = description
            change_log += f'\n Описание боя: {description}'


        try:
            battle.update_battle(**input)
            battle = Battlefield(battle_id)
            embed = SuccessEmbed('Изменение поля боя', f'В настройки поля боя ``id:{battle.id} | {battle.label}`` были внесены изменения: ```\n{change_log}```')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed('Изменение поля боя', f'При изменении поля боя возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)


    @team_com.command(name='create_team')
    @commands.has_permissions(administrator=True)
    async def create_team(self, ctx, battle_id: discord.Option(int),
                          label: discord.Option(str, required=False),
                          role: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(team_roles)),
                          commander: discord.Option(int, required=False),
                          coordinator: discord.Option(int, required=False),
                          command_points: discord.Option(int, required=False),
                          generate_units: discord.Option(int, required=False),
                          units_race: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(races)),
                          units_org_id: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(org_id)),
                          generate_commander: discord.Option(bool, required=False),
                          generate_coordinator: discord.Option(bool, required=False),
                          team_round_activity: discord.Option(bool, required=False),
                          team_spawn_layer: discord.Option(int, required=False)):

        input = {}
        change_log = ''

        if label:
            input['label'] = label
            change_log += f'\n Название команды: "{label}"'

        if role:
            input['role'] = self.get_teamrole_id_by_label(role)
            change_log += f'\n Роль команды: {role}'

        if commander:
            input['commander'] = commander
            change_log += f'\n ID командира: {commander}'

        if coordinator:
            input['coordinator'] = coordinator
            change_log += f'\n ID координатора: {coordinator}'

        if command_points:
            input['com_points'] = command_points
            change_log += f'\n Очки командования: {command_points} ОК.'

        if team_round_activity:
            input['round_active'] = team_round_activity
            change_log += f'\n Начальная доступность помощи: {team_round_activity}'

        if generate_units:
            input['members_value'] = generate_units
            change_log += f'\n Количество членов команды: {generate_units}'

        if generate_commander:
            input['generate_commander'] = generate_commander
            change_log += f'\n Создать командира? (кол-во юнитов +1): {generate_commander}'

        if generate_commander:
            input['generate_coordinator'] = generate_coordinator
            change_log += f'\n Создать координатора? (кол-во юнитов +1): {generate_coordinator}'

        if units_race:
            input['members_race'] = self.get_race_id_by_label(units_race)
            change_log += f'\n Раса членов команды: {units_race}'

        if units_org_id:
            input['members_org'] = units_org_id
            change_log += f'\n ID организации членов команды: {units_org_id}'

        if team_spawn_layer:
            input['members_layer'] = team_spawn_layer
            change_log += f'\n Точка спавна (Слой): {team_spawn_layer}'

        new_team = GenerateTeam(battle_id, **input)

        await ctx.respond(f'***Ожидание генерации новой команды...***')

        try:
            new_team.insert_data()
            embed = SuccessEmbed('Создание команды', f'Вы создали новую команду ``id:{new_team.id} ({new_team.label})`` со следующими параметрами: ```\n{change_log}```')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed('Создание команды', f'При создании новой команды возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @battle_com.command(name='delete_battle')
    @commands.has_permissions(administrator=True)
    async def delete_battle(self, ctx, battle_id: discord.Option(int)):
        try:
            battle = Battlefield(battle_id)
            battle.delete_battle()
            embed = SuccessEmbed('Удаление поля боя', f'Поле боя ``id:{battle.id} | {battle.label}`` было успешно удалено!')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed('Удаление поля боя', f'При удалении поля боя возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @battle_com.command(name='insert_units')
    @commands.has_permissions(administrator=True)
    async def battle_insert_units(self, ctx, battle_id: discord.Option(int), units_id: discord.Option(str), team_id:discord.Option(int, required=False), layer_id:discord.Option(int, required=False)):
        db = DataManager()
        if not db.check('BATTLE_INIT', f'id = {battle_id}'):
            await ctx.respond(f'{ctx.author.mention} поля боя с ID {battle_id} не существует!')

        battle = Battlefield(battle_id, data_manager=db)
        units_list = [int(i) for i in process_string(units_id)]
        input = {}
        if team_id:
            input['team_id'] = team_id

        if layer_id and layer_id in battle.layers:
            input['layer_id'] = layer_id

        for i in units_list:
            battle.add_actor(i, **input)

        try:
            embed = SuccessEmbed('Вступление в бой', f'Персонажи с id:``{units_list}`` успешно вступили в бой ``{battle.label} (id:{battle_id})``!')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed('Вступление в бой', f'При вступление персонажей с id:``{units_list}`` произошла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @battle_com.command(name='delete_units')
    @commands.has_permissions(administrator=True)
    async def delete_units(self, ctx, battle_id: discord.Option(int), units_id: discord.Option(str)):
        units_list = [int(i) for i in process_string(units_id)]

        try:
            battle = Battlefield(battle_id)
            for i in units_list:
                battle.delete_actor(i)

            embed = SuccessEmbed('Персонажи покидают поле боя',
                                 f'Персонажи с id:``{units_list}`` успешно покинули бой ``{battle.label} (id:{battle_id})``!')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed('Персонажи покидают поле боя', f'При покидании персонажей с id:``{units_list}`` произошла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @team_com.command(name='manage_team')
    @commands.has_permissions(administrator=True)
    async def manage_team(self, ctx, battle_id:discord.Option(int), team_id: discord.Option(int),
                          label: discord.Option(str, required=False),
                          role: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(team_roles)),
                          commander_id: discord.Option(int, required=False),
                          coordinator_id: discord.Option(int, required=False),
                          command_points: discord.Option(int, required=False),
                          round_activity: discord.Option(bool, required=False)):


        try:
            change_log = ''
            team = BattleTeam(team_id, battle_id)

            if label:
                team.set_label(label)
                change_log += f'\n Название команды: {label}'

            if role:
                team.set_role(self.get_teamrole_id_by_label(role))
                change_log += f'\n Роль команды: {role}'

            if commander_id:
                team.set_commander(commander_id)
                change_log += f'\n ID командира: {commander_id}'

            if coordinator_id:
                team.set_coordinator(coordinator_id)
                change_log += f'\n ID координатора: {coordinator_id}'

            if command_points:
                team.set_com_points(command_points)
                change_log += f'\n Очки командования: {command_points}'

            if round_activity:
                team.set_activity(round_activity)
                change_log += f'\n Доступ к активности в текущем раунде: {round_activity}'

            embed = SuccessEmbed('Изменение параметров команды',
                                 f'Параметры команды ``{team.id} ({team.label})`` были успешно изменены!\n```{change_log}```')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed('Изменение параметрво команды', f'При изменение параметров команды ``{team_id}`` возникла ошибка:\n``{e}``')
            await ctx.respond(f'', embed=embed)

    @layer_com.command(name='add_layer')
    @commands.has_permissions(administrator=True)
    async def add_layer(self, ctx, battle_id:discord.Option(int, 'Укажите ID боя'),
                        terrain_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(terrain_types)),
                        generate_objects_value: discord.Option(int, required=False),
                        label: discord.Option(str, required=False),
                        height: discord.Option(str, required=False)):

        try:
            battle = Battlefield(battle_id)

            input = {}

            if label:
                input['label'] = label

            if terrain_type:
                input['terrain_type'] = self.get_terrain_type_by_label(terrain_type)

            if height:
                input['height'] = height

            new_layer = battle.add_layer(**input)
            print(new_layer)

            if generate_objects_value:
                value_of_objects = len(new_layer.generate_objects(generate_objects_value))
            else:
                value_of_objects = 0

            embed = SuccessEmbed('Добавление нового слоя',
                                 f'В бой``{battle.label} (id:{battle_id})`` был добавлен новый слой:\n```ID: {new_layer.id}\nНазвание: {new_layer.label}\nТип местности: {new_layer.terrain.label}\nОтносительная высота: {new_layer.height}\nОбъектов сгенерировано: {value_of_objects}```')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed('Добавление нового слоя', f'При добавлении нового слоя произошла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @layer_com.command(name='manage_layer')
    @commands.has_permissions(administrator=True)
    async def manage_layer(self, ctx, battle_id:discord.Option(int, 'Укажите ID боя'),
                            layer_id: discord.Option(int, 'Укажите ID слоя'),
                            terrain_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(terrain_types)),
                            generate_objects_value: discord.Option(int),
                            label: discord.Option(str, required=False),
                            height: discord.Option(str, required=False)):

        try:
            layer = Layer(layer_id, battle_id)
            if label:
                layer.set_label(label)

            if terrain_type:
                layer.set_terrain(self.get_terrain_type_by_label(terrain_type))

            if height:
                layer.set_height(height)

            if generate_objects_value:
                value_of_objects = len(layer.generate_objects(generate_objects_value))
            else:
                value_of_objects = 0

            embed = SuccessEmbed('Редактирование слоя',
                                 f'В слой ``{layer.label} (id:{layer_id}.{layer.battle_id})`` были внесены изменения. Текущие параметры:\n```ID: {layer.id}\nНазвание: {layer.label}\nТип местности: {layer.terrain.label}\nОтносительная высота: {layer.height}\nОбъектов сгенерировано: {value_of_objects}```')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed('Редактирование слоя', f'При редактировании слоя возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @layer_com.command(name='delete_layer')
    @commands.has_permissions(administrator=True)
    async def delete_layer(self, ctx, battle_id:discord.Option(int, 'Укажите ID боя'),
                                        layer_id: discord.Option(int, 'Укажите ID слоя')):
        try:
            battle = Battlefield(battle_id)
            battle.delete_layer(layer_id)

            embed = SuccessEmbed('Удаление слоя',
                                 f'В бою ``{battle.label} (id:{battle.id})`` был удален слой ``id: {layer_id}``.')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed('Удаление слоя', f'При удалении слоя возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @object_com.command(name='add_object')
    @commands.has_permissions(administrator=True)
    async def add_object(self, ctx, battle_id: discord.Option(int, 'Укажите ID боя'), layer_id: discord.Option(int, 'Укажите ID слоя'),
                         object_type: discord.Option(str, 'Укажите тип объекта', autocomplete=discord.utils.basic_autocomplete(object_type)),
                         endurance: discord.Option(int, 'Прочность объекта', required=False),
                         value: discord.Option(int, 'Количество создаваемых объектов данного типа', required=False),
                         captured: discord.Option(str, 'ID команды, захватившей объект', required=False, autocomplete=discord.utils.basic_autocomplete(teams_id)),
                         uses: discord.Option(int, 'Количество сделаных использований', required=False)):

        try:
            layer = Layer(layer_id, battle_id)

            cur_type = self.get_object_type_by_label(object_type)

            if not captured:
                cur_captured = None
            else:
                cur_captured = int(captured.split()[0])

            print(cur_type)
            layer.add_object(cur_type, endurance if endurance else None, cur_captured, value if value else None, uses if uses else None)

            embed = SuccessEmbed(f'Создание объекта на слое {layer_id}.{battle_id}',
                                 f'На слое ``{layer_id}.{battle_id}({layer.label})`` были созданы объекты ``{object_type}`` в количестве ``{value}``')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed(f'Создание объекта на слое {layer_id}.{battle_id}', f'При создании объекта возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @object_com.command(name='manage_object')
    @commands.has_permissions(administrator=True)
    async def manage_object(self, ctx, battle_id: discord.Option(int),
                            layer_id: discord.Option(int),
                            object_id: discord.Option(int),
                            object_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(object_type), required=False),
                            endurance: discord.Option(int, required=False),
                            uses: discord.Option(int, required=False),
                            captured: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(teams_id), required=False)):

        try:
            object = GameObject(object_id, layer_id, battle_id)

            cur_type = self.get_object_type_by_label(object_type)

            if not captured:
                cur_captured = None
            else:
                cur_captured = int(captured.split()[0])


            object.edit(cur_type, endurance if endurance else None, uses if uses else None, cur_captured)

            embed = SuccessEmbed(f'Редактирование объекта',
                                 f'На слое ``{layer_id}.{battle_id}`` был отредактирован объект ``{object_id}``.')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed(f'Редактирование объекта',
                               f'При редактировании объекта возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @object_com.command(name='delete_object')
    @commands.has_permissions(administrator=True)
    async def delete_object(self, ctx, battle_id: discord.Option(int),
                            layer_id: discord.Option(int),
                            object_id: discord.Option(int)):

        try:
            object = GameObject(object_id, layer_id, battle_id)

            object.delete_object()

            embed = SuccessEmbed(f'Удаление объекта',
                                 f'На слое ``{layer_id}.{battle_id}`` был удален объект ``{object_id}``.')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed(f'Удаление объекта',
                               f'При удалении объекта возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @trap_com.command(name='add_trap')
    @commands.has_permissions(administrator=True)
    async def add_trap(self, ctx, battle_id: discord.Option(int),
                       layer_id: discord.Option(int),
                       trap_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(traps_type)),
                       trap_buff: discord.Option(int, required=False),
                       value: discord.Option(int, required=False, default=1)):

        try:
            layer = Layer(layer_id, battle_id)

            cur_type = self.get_trap_type_by_label(trap_type)
            print(cur_type)

            print(cur_type)
            layer.add_trap(cur_type, trap_buff, value)

            embed = SuccessEmbed(f'Создание ловушки на слое {layer_id}.{battle_id}',
                                 f'На слое ``{layer_id}.{battle_id}({layer.label})`` были созданы ловушки ``{trap_type}`` в количестве ``{value}``')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed(f'Создание ловушки на слое {layer_id}.{battle_id}', f'При создании ловушки возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @trap_com.command(name='manage_trap')
    @commands.has_permissions(administrator=True)
    async def manage_trap(self, ctx, battle_id: discord.Option(int),
                          layer_id: discord.Option(int),
                          trap_id: discord.Option(int),
                          trap_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(traps_type), required=False),
                          buff: discord.Option(int, required=False)):
        try:
            layer = Layer(layer_id, battle_id)

            if trap_type:
                cur_type = self.get_trap_type_by_label(trap_type)
            else:
                cur_type = None

            if buff:
                cur_buff = buff
            else:
                cur_buff = None

            layer.edit_trap(trap_id, cur_type, cur_buff)

            embed = SuccessEmbed(f'Редактирование ловушки',
                                 f'На слое ``{layer_id}.{battle_id}`` была отредактирована ловушка ``{trap_id}``.')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed(f'Редактирование ловушки',
                               f'При редактировании ловушки возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @trap_com.command(name='delete_trap')
    @commands.has_permissions(administrator=True)
    async def delete_trap(self, ctx,
                          battle_id: discord.Option(int),
                          layer_id: discord.Option(int),
                          trap_id: discord.Option(int)):

        try:
            layer = Layer(layer_id, battle_id)
            layer.delete_trap(trap_id)

            embed = SuccessEmbed(f'Удаление ловушки',
                                 f'На слое ``{layer_id}.{battle_id}`` была удалена ловушка ``{trap_id}``.')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed(f'Удаление ловушки',
                               f'При удалении ловушки возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @layer_com.command(name='add_leffect')
    @commands.has_permissions(administrator=True)
    async def add_layer_effect(self, ctx, battle_id:int, layer_id:int):
        pass

    @layer_com.command(name='manage_leffects')
    @commands.has_permissions(administrator=True)
    async def manage_layer_effect(self, ctx, battle_id:int, layer_id:int, effect:str):
        pass

    @layer_com.command(name='delete_leffect')
    @commands.has_permissions(administrator=True)
    async def delete_layer_effect(self, ctx, battle_id:int, layer_id:int, effect:str):
        pass

    @sound_com.command(name='add_sound')
    @commands.has_permissions(administrator=True)
    async def add_sound(self, ctx, battle_id: discord.Option(int),
                        sound_type: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(sound_types)),
                        layer_id: discord.Option(int, required=False),
                        actor_id: discord.Option(int, required=False),
                        round_id: discord.Option(int, required=False),
                        volume: discord.Option(int, required=False)):

        try:
            battle = Battlefield(battle_id)
            cur_type = self.get_sound_type_by_label(sound_type)

            sound = battle.add_sound(cur_type, actor_id, round_id, volume)

            embed = SuccessEmbed(f'Создание звука {sound_type}',
                                 f'На слое ``{sound.layer_id}.{battle_id}`` был создан звук ``{sound_type}``.')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed(f'Создание звука {sound_type}', f'При создании звука возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @sound_com.command(name='manage_sound')
    @commands.has_permissions(administrator=True)
    async def manage_sound(self, ctx, battle_id: discord.Option(int),
                           sound_id: discord.Option(int),
                           sound_type: discord.Option(str, required=False, autocomplete=discord.utils.basic_autocomplete(sound_types)),
                           actor_id: discord.Option(int, required=False),
                           layer_id: discord.Option(int, required=False),
                           round: discord.Option(int, required=False),
                           volume: discord.Option(int, required=False)):
        try:
            battle = Battlefield(battle_id)
            if sound_type:
                cur_type = self.get_sound_type_by_label(sound_type)
            else:
                cur_type = None

            sound = battle.edit_sound(sound_id, actor_id, cur_type, layer_id, round, volume)

            embed = SuccessEmbed(f'Редактирование звука {sound_id}',
                                 f'На слое ``{sound.layer_id}.{battle_id}`` был отредактирован звук ``{sound_id}``.')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed(f'Редактирование звука {sound_id}', f'При редактировании звука возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @sound_com.command(name='delete_sound')
    @commands.has_permissions(administrator=True)
    async def delete_sound(self, ctx, battle_id: discord.Option(int),
                           sound_id: discord.Option(int)):
        try:
            battle = Battlefield(battle_id)

            sound = battle.delete_sound(sound_id)

            embed = SuccessEmbed(f'Удаление звука {sound_id}',
                                 f'В бою ``id {battle_id}`` был удален звук ``{sound_id}``.')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed(f'Удаление звука {sound_id}',
                               f'При удалении звука возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @battle_com.command(name='forcend')
    @commands.has_permissions(administrator=True)
    async def force_battle_end(self, ctx, battle_id:int):
        pass

    @battle_com.command(name='next_turn')
    @commands.has_permissions(administrator=True)
    async def next_turn(self, ctx, battle_id: discord.Option(int)):
        try:
            battle = Battlefield(battle_id)
            actor, is_new_round = battle.next_actor()
            if actor is None:
                embed = SuccessEmbed(f'Конец боя!',
                                   f'*Бой был окончен:*\n```{is_new_round[1].label} — {is_new_round[0].status}```')
                await ctx.respond(f'', embed=embed)
                return

            title = 'Новый раунд' if is_new_round else 'Следующий ход'
            desc = f'*Персонаж ``{actor.get_name()}`` завершает свой ход*'
            if is_new_round:
                desc += f'*. Начинается новый раунд ``{is_new_round}``!*'

            embed = SuccessEmbed(title, desc)
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed(f'Следующий ход',
                               f'При смене хода возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @battle_com.command(name='force_next_round')
    @commands.has_permissions(administrator=True)
    async def next_round(self, ctx, battle_id: discord.Option(int)):
        try:
            battle = Battlefield(battle_id)
            battle.next_round()

            embed = SuccessEmbed('Новый раунд', f'Начинается новый раунд: ``{battle.round}``!')
            await ctx.respond(f'', embed=embed)

        except Exception as e:
            embed = ErrorEmbed(f'Новый раунд',
                               f'При смене раунда возникла ошибка ``{e}``.')
            await ctx.respond(f'', embed=embed)

    @battle_com.command(name='forcereroll')
    @commands.has_permissions(administrator=True)
    async def force_initiative_change(self, ctx, battle_id:int):
        pass

    @commands.command(name='unit_combat')
    @commands.has_permissions(administrator=True)
    async def manage_unit_combat(self, ctx, character_id:int):
        pass


def setup(bot):
    bot.add_cog(AdminCommands(bot))