import discord
from discord.ext import commands
from ArbDatabase import DataManager
from ArbUIUX import ArbEmbed, HealthEmbed, Paginator, ErrorEmbed, SuccessEmbed
from ArbUtils.ArbDataParser import get_owners_character, ListChunker
from ArbBattle import Actor, Coordinator
import cProfile


# class CharacterCombatMenu(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot
#         print(f'...Module {self.__class__.__name__} is ready')
#
#     coordinator_command = discord.SlashCommandGroup("coordinator", "Команды боевого координатора")
#     combat = discord.SlashCommandGroup("n_combat", "Команды боевого взаимодействия")
#     movement = discord.SlashCommandGroup("movement", "Команды перемещения в бою")
#     interaction_com = discord.SlashCommandGroup("interaction", "Команды для взаимодействия с объектами")
#
#     def check_if_in_battle(self, character_id:int, db:DataManager = None):
#         db = db if db else DataManager()
#         if db.check('BATTLE_CHARACTERS',f'character_id = {character_id}'):
#             return True
#         else:
#             return False
#
#     @commands.slash_command(name='battle_info')
#     async def __battle_info(self, ctx):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         battle = Actor(character).get_current_battle()
#         name, total_text = battle.describe()
#         teams_text = battle.describe_teams()
#
#         embed = ArbEmbed(name, total_text, footer=f'battle_id: {battle.id}')
#         teams_embed = ArbEmbed(f'{name} | Команды', teams_text, footer=f'battle_id: {battle.id}')
#         embeds = [embed, teams_embed]
#         view = Paginator(embeds, ctx, {1: 'Информация', 2: 'Команды'})
#         await view.update_button()
#         await ctx.respond(embed=embeds[0], view=view)
#
#     @commands.slash_command(name='combat')
#     async def __combat_info(self, ctx):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         actor = Actor(character)
#         info = actor.combat_info()
#         embed = ArbEmbed('Боевая сводка', info, footer=f'character_id: {character}')
#
#         await ctx.respond('', embed=embed)
#
#     @combat.command(name='take_target')
#     async def __take_target(self, ctx, enemy_id:int):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         target = Actor(character).take_target(enemy_id)
#         if target:
#             embed = SuccessEmbed('Цель на мушке!', f'*Вы находите противника ``{enemy_id}`` и успешно наводитесь на цель!*')
#         else:
#             embed = ErrorEmbed('Цель не обнаружена', f'*Вы не смогли найти противника ``{enemy_id}``...*')
#
#         await ctx.respond('', embed=embed)
#
#     @combat.command(name='take_melee_target')
#     async def __take_melee_target(self, ctx, enemy_id:int):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         response = Actor(character).set_melee_target(enemy_id)
#
#         if response:
#             embed = SuccessEmbed('Удалось навязать ближний бой', f'*Вы успешно сближаетесь с противником ``{enemy_id}``, навязывая ему ближний бой!*')
#         else:
#             embed = ErrorEmbed('Не удалось навязать ближний бой', f'*Вы не смогли сблизиться с противником ``{enemy_id}`` и не можете навязать ему ближний бой...*')
#
#         await ctx.respond('', embed=embed)
#
#     @combat.command(name='range_attack')
#     async def __range_attack(self, ctx, enemy_id:int=None, weapon_id:int=None):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         response, desc = Actor(character).range_attack(enemy_id, weapon_id)
#
#         if response:
#             embed = SuccessEmbed('Атака!', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Неудачная атака', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#     @combat.command(name='melee_attack')
#     async def __melee_attack(self, ctx, enemy_id:int=None, weapon_id:int=None):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         response, desc = Actor(character).melee_attack(enemy_id, weapon_id)
#
#         if response:
#             embed = SuccessEmbed('Ближняя атака!', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Неудачная ближняя атака', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#     @combat.command(name='race_attack')
#     async def __race_attack(self, ctx, attack_id:str=None, enemy_id:int=None):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         response, desc = Actor(character).race_attack(enemy_id, attack_id)
#
#         if response:
#             embed = SuccessEmbed('Расовая атака!', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Неудачная расовая атака', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#     @combat.command(name='grenade')
#     async def __throw_grenade(self, ctx, enemy_id:int=None, grenade_id:int=None):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         response, desc = Actor(character).throw_grenade(enemy_id, grenade_id)
#
#         if response:
#             embed = SuccessEmbed('Граната!', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Неудачный бросок гранаты', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#     @combat.command(name='lookout')
#     async def __lookout(self, ctx):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         await ctx.respond(f'***Вы оглядываетесь по сторонам осматривая ближайшую местность поля боя...***', ephemeral=True)
#
#         embed = ArbEmbed('Обзор поля боя...', Actor(character).lookout())
#
#         await ctx.respond('', embed=embed, ephemeral=True)
#
#     @combat.command(name='detect_sound')
#     async def __detect_sound(self, ctx, sound_id:int=None):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         if not sound_id:
#             print('тут!')
#             actor = Actor(character)
#             c_round = actor.get_current_battle().round
#
#             sound_list = actor.list_of_sounds()
#             chunks = ListChunker(5, sound_list)
#             embeds = []
#             for chunk in chunks:
#                 total_text = ''
#                 for sound in chunk:
#                     c_distance = actor.distance_to_layer(sound.layer_id)
#                     c_chance = sound.get_detection_chance(c_distance, c_round)
#                     total_text += f'\n\n``ID: {sound.id}`` **{sound.label} **\n> *Шанс обнаружения источника: **{c_chance:.2f}%***\n> *— "{sound.description}"*'
#                 embeds.append(ArbEmbed('Звуки боя', total_text))
#
#             view = Paginator(embeds, ctx, ignore_footer=True)
#             await view.update_button()
#             await ctx.respond(embed=embeds[0], view=view)
#         else:
#             c_detect = Actor(character).detect_sound_source(sound_id)
#             if c_detect:
#                 embed = SuccessEmbed('Успешное обнаружение', f'*Вы оглядываете предполагаемое место, где находился источник звука и замечаете движение неподалёку!*')
#
#             else:
#                 embed = ErrorEmbed('Неудачное обнаружение', f'*Вы оглядываете предполагаемое место, где находится источник звука, но это не приносит никаких результатов*')
#
#             await ctx.respond(f'', embed=embed)
#
#     @movement.command(name='take_cover')
#     async def __get_to_cover(self, ctx, cover_id:int=None):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         actor = Actor(character)
#         result = actor.move_to_object(cover_id)
#
#         if cover_id:
#             desc = f'Вы идёте некоторое время и сближаетесь с {actor.get_current_object().label} ``(id:{actor.current_object_id})``'
#         else:
#             desc = f'Вы покидаете укрытие и отходите от него на некоторое расстояние'
#
#         if result:
#             embed = SuccessEmbed('Перемещение к укрытию',
#                                  f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Перемещение к укрытию',
#                                f'*У вас не хватает сил и времени чтобы двигаться на данный момент!*')
#
#         await ctx.respond('', embed=embed)
#
#     @movement.command(name='escape')
#     async def __escape(self, ctx):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         actor = Actor(character)
#         result, desc = actor.escape_from_battle()
#
#         if result:
#             embed = SuccessEmbed('Побег с поля боя', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Побег с поля боя', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#     @movement.command(name='move')
#     async def __move_to(self, ctx, layer_id:int):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         actor = Actor(character)
#         start_layer = actor.current_layer_id
#         result = actor.move_to_layer(layer_id)
#         if result != start_layer:
#             embed = SuccessEmbed('Перемещение', f'*Вы идёте некоторое время и видите {actor.get_current_layer().terrain.label} ``(id:{actor.current_layer_id})``*')
#         else:
#             embed = ErrorEmbed('Перемещение', f'*У вас не хватает сил и времени чтобы двигаться дальше на данный момент!*')
#
#         await ctx.respond('', embed=embed)
#
#     @combat.command(name='reload')
#     async def __reload(self, ctx, weapon_id:int=None, ammo_id:int=None):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         actor = Actor(character)
#         response, weapon = actor.reload(weapon_id=weapon_id, item_id=ammo_id)
#         if response is None and weapon is None:
#             embed = SuccessEmbed('Перезарядка', f'*У вас нет оружия, которое можно перезарядить*')
#         elif response is None:
#             embed = ErrorEmbed(f'Перезарядка {weapon.Name}', f'*Вы осматриваете своё снаряжение и не находите подходящих патронов*')
#         elif not response:
#             embed = ErrorEmbed(f'Перезарядка {weapon.Name}', f'*У вас не хватает сил и времени чтобы перезарядить оружие!*')
#         else:
#             embed = SuccessEmbed(f'Перезарядка {weapon.Name}', f'*Нажав на фиксатор магазина и выкинув разряженную обойму на землю, вы достаете второй рукой новую из подсумки. Как только старая обойма вышла из гнезда магазина, вы вставили новую обойму {weapon.get_current_ammo()}, и, зафиксировав ее, и передернули затвор своего оружия - {weapon.Name}*')
#
#         await ctx.respond('', embed=embed)
#
#     @combat.command(name='overwatch')
#     async def __overwatch(self, ctx):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         actor = Actor(character)
#         response = actor.get_ready()
#         if response:
#             embed = SuccessEmbed('Дозор', f'*Вы взводите своё оружие и оглядываетесь вокруг в ожидании возможной атаки*')
#         else:
#             embed = ErrorEmbed('Дозор', f'*Вы не можете подготовиться к дозору*')
#
#         await ctx.respond('', embed=embed)
#
#     @combat.command(name='hunt')
#     async def __hunt(self, ctx, enemy_id:int=None):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         actor = Actor(character)
#         response = actor.take_hunt(enemy_id)
#
#         if response:
#             embed = SuccessEmbed('Охота', f'*Вы взводите своё оружие и аккуратно наводитесь на противника ``{enemy_id}``, внимательно наблюдая за его действиями и выжидая удачный момент для атаки*')
#         else:
#             embed = ErrorEmbed('Охота', f'*Вы не можете взять противника ``{enemy_id}`` под контроль*')
#         await ctx.respond('', embed=embed)
#
#     @combat.command(name='contain')
#     async def __contain(self, ctx, layer_id:int):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         actor = Actor(character)
#         response = actor.take_contain(layer_id)
#         if response:
#             embed = SuccessEmbed('Подавление', f'*Вы открываете упорядоченный и регулярный огонь по соседнему слою ``{layer_id}``, сдерживая перемещение и действия противника*')
#         else:
#             embed = ErrorEmbed('Подавление', f'*У вас нет возможности открыть огонь на подавление по слою ``{layer_id}``*')
#
#         await ctx.respond('', embed=embed)
#     @movement.command(name='fly')
#     async def __fly(self, ctx, height:int):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         actor = Actor(character)
#         response, desc = actor.fly_height(height)
#
#         if response:
#             embed = SuccessEmbed('Полет!', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Неудачная попытка взмыть в воздух', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#     @interaction_com.command(name='interact')
#     async def __interact_with_object(self, ctx, enemy_id:int=None):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         actor = Actor(character)
#         response, desc = actor.interact_with_current_object(enemy_id=enemy_id)
#
#         if response:
#             embed = SuccessEmbed('Взаимодействие!', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Неудачное взаимодействие', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#     @interaction_com.command(name='capture_object')
#     async def __capture_object(self, ctx):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         actor = Actor(character)
#         response, desc = actor.capture_object()
#
#         if response:
#             embed = SuccessEmbed('Захват позиции!', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Неудачный захват позиции', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#     @coordinator_command.command(name='supply')
#     async def __coord_supply(self, ctx, layer_id:int, supply_type: discord.Option(str, choices=['Боеприпасы', 'Гранаты', 'Медикаменты', 'Инструменты']), value:int):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         coordinator = Coordinator(character)
#
#         if supply_type == 'Боеприпасы':
#             response, desc = coordinator.supply_ammo(layer_id, value)
#         elif supply_type == 'Гранаты':
#             response, desc = coordinator.supply_grenades(layer_id, value)
#         elif supply_type == 'Медикаменты':
#             response, desc = coordinator.supply_firstaid(layer_id, value)
#         elif supply_type == 'Инструменты':
#             response, desc = coordinator.supply_repair(layer_id, value)
#
#         if response:
#             embed = SuccessEmbed('Полевое снабжение', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Полевое снабжение', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#     @coordinator_command.command(name='mines')
#     async def __coord_mines(self, ctx, layer_id: int, value: int):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         coordinator = Coordinator(character)
#
#         response, desc = coordinator.mine_laying(layer_id, mine_value=value, mine_type='APM')
#
#         if response:
#             embed = SuccessEmbed('Минирование', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Минирование', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#     @coordinator_command.command(name='artillery')
#     async def __coord_artillery(self, ctx, layer_id: int, strikes: int):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         coordinator = Coordinator(character)
#
#         response, desc = coordinator.artillery_strike(layer_id, strikes, 'he82')
#
#         if response:
#             embed = SuccessEmbed('Артудар', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Артудар', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#     @coordinator_command.command(name='reinforcement')
#     async def __coord_reinforcement(self, ctx, layer_id: int, value: int):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         coordinator = Coordinator(character)
#
#         response, desc = coordinator.reinforcement(layer_id, value)
#
#         if response:
#             embed = SuccessEmbed('Подкрепление', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Подкрепление', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#     @coordinator_command.command(name='evacuation')
#     async def __coord_evac(self, ctx, layer_id: int):
#         user_id = ctx.author.id
#         character = get_owners_character(user_id)
#         if character is None:
#             await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
#             return
#
#         if not self.check_if_in_battle(character):
#             await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
#             return
#
#         coordinator = Coordinator(character)
#
#         response, desc = coordinator.evacuation(layer_id)
#
#         if response:
#             embed = SuccessEmbed('Эвакуация', f'*{desc}*')
#         else:
#             embed = ErrorEmbed('Эвакуация', f'*{desc}*')
#
#         await ctx.respond('', embed=embed)
#
#
# def setup(bot):
#     bot.add_cog(CharacterCombatMenu(bot))