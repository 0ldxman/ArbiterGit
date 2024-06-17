from discord.ext import commands
from ArbDatabase import DataManager
from ArbUIUX import ArbEmbed, HealthEmbed, Paginator, ErrorEmbed, SuccessEmbed
from ArbUtils.ArbDataParser import get_owners_character, ListChunker
from ArbBattle import Actor


class CharacterCombatMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print(f'...Module {self.__class__.__name__} is ready')

    def check_if_in_battle(self, character_id:int, db:DataManager = None):
        db = db if db else DataManager()
        if db.check('BATTLE_CHARACTERS',f'character_id = {character_id}'):
            return True
        else:
            return False

    @commands.slash_command(name='battle_info')
    async def __battle_info(self, ctx):
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
            return

        if not self.check_if_in_battle(character):
            await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
            return

        battle = Actor(character).get_current_battle()
        name, total_text = battle.describe()
        teams_text = battle.describe_teams()

        embed = ArbEmbed(name, total_text, footer=f'battle_id: {battle.id}')
        teams_embed = ArbEmbed(f'{name} | Команды', teams_text, footer=f'battle_id: {battle.id}')
        embeds = [embed, teams_embed]
        view = Paginator(embeds, ctx, {1: 'Информация', 2: 'Команды'})
        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @commands.slash_command(name='combat_info')
    async def __combat_info(self, ctx):
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
            return

        if not self.check_if_in_battle(character):
            await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
            return

        actor = Actor(character)
        info = actor.combat_info()
        embed = ArbEmbed('Боевая сводка', info, footer=f'character_id: {character}')

        await ctx.respond('', embed=embed)

    @commands.slash_command(name='take_target')
    async def __take_target(self, ctx, enemy_id:int):
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
            return

        if not self.check_if_in_battle(character):
            await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
            return

        target = Actor(character).take_target(enemy_id)
        if target:
            embed = SuccessEmbed('Цель на мушке!', f'*Вы находите противника ``{enemy_id}`` и успешно наводитесь на цель!*')
        else:
            embed = ErrorEmbed('Цель не обнаружена', f'*Вы не смогли найти противника ``{enemy_id}``...*')

        await ctx.respond('', embed=embed)

    @commands.slash_command(name='take_melee_target')
    async def __take_melee_target(self, ctx, enemy_id:int):
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
            return

        if not self.check_if_in_battle(character):
            await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
            return

        response = Actor(character).set_melee_target(enemy_id)

        if response:
            embed = SuccessEmbed('Удалось навязать ближний бой', f'*Вы успешно сближаетесь с противником ``{enemy_id}``, навязывая ему ближний бой!*')
        else:
            embed = ErrorEmbed('Не удалось навязать ближний бой', f'*Вы не смогли сблизиться с противником ``{enemy_id}`` и не можете навязать ему ближний бой...*')

        await ctx.respond('', embed=embed)

    @commands.slash_command(name='range_attack')
    async def __range_attack(self, ctx, enemy_id:int=None, weapon_id:int=None):
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
            return

        if not self.check_if_in_battle(character):
            await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
            return

        response, desc = Actor(character).range_attack(enemy_id, weapon_id)

        if response:
            embed = SuccessEmbed('Атака!', f'*{desc}*')
        else:
            embed = ErrorEmbed('Неудачная атака', f'*{desc}*')

        await ctx.respond('', embed=embed)

    @commands.slash_command(name='melee_attack')
    async def __melee_attack(self, ctx, enemy_id:int=None, weapon_id:int=None):
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
            return

        if not self.check_if_in_battle(character):
            await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
            return

        response, desc = Actor(character).melee_attack(enemy_id, weapon_id)

        if response:
            embed = SuccessEmbed('Ближняя атака!', f'*{desc}*')
        else:
            embed = ErrorEmbed('Неудачная ближняя атака', f'*{desc}*')

        await ctx.respond('', embed=embed)

    @commands.slash_command(name='race_attack')
    async def __race_attack(self, ctx, attack_id:str=None, enemy_id:int=None):
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
            return

        if not self.check_if_in_battle(character):
            await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
            return

        response, desc = Actor(character).race_attack(enemy_id, attack_id)

        if response:
            embed = SuccessEmbed('Расовая атака!', f'*{desc}*')
        else:
            embed = ErrorEmbed('Неудачная расовая атака', f'*{desc}*')

        await ctx.respond('', embed=embed)

    @commands.slash_command(name='grenade')
    async def __throw_grenade(self, ctx, enemy_id:int=None, grenade_id:int=None):
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
            return

        if not self.check_if_in_battle(character):
            await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
            return

        response, desc = Actor(character).throw_grenade(enemy_id, grenade_id)

        if response:
            embed = SuccessEmbed('Граната!', f'*{desc}*')
        else:
            embed = ErrorEmbed('Неудачный бросок гранаты', f'*{desc}*')

        await ctx.respond('', embed=embed)

    @commands.slash_command(name='lookout')
    async def __lookout(self, ctx):
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
            return

        if not self.check_if_in_battle(character):
            await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
            return

        embed = ArbEmbed('Обзор поля боя...', Actor(character).lookout())
        await ctx.respond('', embed=embed)

    @commands.slash_command(name='detect_sound')
    async def __detect_sound(self, ctx, sound_id:int=None):
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
            return

        if not self.check_if_in_battle(character):
            await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
            return

        if not sound_id:
            print('тут!')
            actor = Actor(character)
            c_round = actor.get_current_battle().round

            sound_list = actor.list_of_sounds()
            chunks = ListChunker(5, sound_list)
            embeds = []
            for chunk in chunks:
                total_text = ''
                for sound in chunk:
                    c_distance = actor.distance_to_layer(sound.layer_id)
                    c_chance = sound.get_detection_chance(c_distance, c_round)
                    total_text += f'\n\n``ID: {sound.id}`` **{sound.label} **\n> *Шанс обнаружения источника: **{c_chance:.2f}%***\n> *— "{sound.description}"*'
                embeds.append(ArbEmbed('Звуки боя', total_text))

            view = Paginator(embeds, ctx, ignore_footer=True)
            await view.update_button()
            await ctx.respond(embed=embeds[0], view=view)
        else:
            c_detect = Actor(character).detect_sound_source(sound_id)
            if c_detect:
                embed = SuccessEmbed('Успешное обнаружение', f'*Вы оглядываете предполагаемое место, где находился источник звука и замечаете движение неподалёку!*')

            else:
                embed = ErrorEmbed('Неудачное обнаружение', f'*Вы оглядываете предполагаемое место, где находится источник звука, но это не приносит никаких результатов*')

            await ctx.respond(f'', embed=embed)

    @commands.slash_command(name='take_cover')
    async def __get_to_cover(self, ctx, cover_id:int=None):
        pass

    @commands.slash_command(name='escape')
    async def __escape(self, ctx):
        pass

    @commands.slash_command(name='move')
    async def __move_to(self, ctx, layer_id:int):
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
            return

        if not self.check_if_in_battle(character):
            await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
            return

        actor = Actor(character)
        start_layer = actor.current_layer_id
        result = actor.move_to_layer(layer_id)
        if result != start_layer:
            embed = SuccessEmbed('Перемещение', f'*Вы идёте некоторое время и видите {actor.get_current_layer().terrain.label} ``(id:{actor.current_layer_id})``*')
        else:
            embed = ErrorEmbed('Перемещение', f'*У вас не хватает сил и времени чтобы двигаться дальше на данный момент!*')

        await ctx.respond('', embed=embed)

    @commands.slash_command(name='reload')
    async def __reload(self, ctx, weapon_id:int=None, ammo_id:int=None):
        user_id = ctx.author.id
        character = get_owners_character(user_id)
        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа!')
            return

        if not self.check_if_in_battle(character):
            await ctx.send(f'{ctx.author.mention}, Ваш персонаж не находится в состоянии боя!')
            return

        actor = Actor(character)
        response, weapon = actor.reload(weapon_id=weapon_id, item_id=ammo_id)
        if response is None and weapon is None:
            embed = SuccessEmbed('Перезарядка', f'*У вас нет оружия, которое можно перезарядить*')
        elif response is None:
            embed = ErrorEmbed(f'Перезарядка {weapon.Name}', f'*Вы осматриваете своё снаряжение и не находите подходящих патронов*')
        elif not response:
            embed = ErrorEmbed(f'Перезарядка {weapon.Name}', f'*У вас не хватает сил и времени чтобы перезарядить оружие!*')
        else:
            embed = SuccessEmbed(f'Перезарядка {weapon.Name}', f'*Нажав на фиксатор магазина и выкинув разряженную обойму на землю, вы достаете второй рукой новую из подсумки. Как только старая обойма вышла из гнезда магазина, вы вставили новую обойму {weapon.get_current_ammo()}, и, зафиксировав ее, и передернули затвор своего оружия - {weapon.Name}*')

        await ctx.respond('', embed=embed)

    @commands.slash_command(name='overwatch')
    async def __overwatch(self, ctx):
        pass

    @commands.slash_command(name='hunt')
    async def __hunt(self, ctx, enemy_id:int=None):
        pass

    @commands.slash_command(name='contain')
    async def __contain(self, ctx, layer_id:int):
        pass


def setup(bot):
    bot.add_cog(CharacterCombatMenu(bot))