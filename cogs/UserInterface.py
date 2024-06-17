from discord.ext import commands
from discord import default_permissions
from ArbCharacters import InterCharacter
from ArbDatabase import DataManager
from ArbHealth import LocalDisease, LocalInjury, Body
from ArbUIUX import ArbEmbed, HealthEmbed, Paginator
from ArbUtils.ArbDataParser import get_owners_character
from ArbCharacterMemory import CharacterMemory, CharacterRelations


class CharacterMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print(f'...Module {self.__class__.__name__} is ready')

    def character_relations(self, character:int, data_manager: DataManager = None):
        db = DataManager() if not data_manager else data_manager
        char_obj = CharacterRelations(character, data_manager=db)

        text = ''

        for rel in char_obj.relationships:
            if char_obj.relationships[rel].__repr__() is not None:
                text += f'\n {char_obj.relationships[rel].__repr__()}'

        relations_embed = ArbEmbed('Отношения', text)
        return relations_embed

    def character_info(self, character:int, data_manager:DataManager= None):
        db = DataManager() if not data_manager else data_manager
        char_obj = InterCharacter(character, data_manager=db)

        text = f'{char_obj.__str__()}'
        info_embed = ArbEmbed('Информация о персонаже', text, footer=f'Последний цикл: {char_obj.updated} ({char_obj.cycles_to_skip()} дня назад)\nСервер: {char_obj.server}')

        return info_embed

    def character_health_embeds(self, character:int, data_manager:DataManager = None):
        db = DataManager() if not data_manager else data_manager

        body = Body(character, data_manager=db)

        vital_damage = body.vital_damage()

        embed_stats = HealthEmbed(f'Жизненные показатели', f'{body.phisical_stats_print()}', damage=vital_damage)

        embed_injuries = HealthEmbed(f'Ранения', f'{body.__str__() if body.__str__() else "*(Здесь будут отображаться ранения вашего персонажа)*"}', damage=vital_damage)

        return embed_stats, embed_injuries

    def character_skills_and_chars_embed(self, character:int, data_manager:DataManager = None):
        db = DataManager() if not data_manager else data_manager

        chars_text, skill_text = InterCharacter(character, data_manager=db).fetch_skills()

        text = f'{chars_text}\n{skill_text}'

        embed = ArbEmbed(f'Навыки и характеристики', text)

        return embed

    def character_equipment(self, character:int, data_manager:DataManager = None):
        from ArbItems import CharacterEquipment, Inventory

        db = DataManager() if not data_manager else data_manager

        clothes_text, weapons_text = CharacterEquipment(character, data_manager=db).describe()
        print(CharacterEquipment(character))
        items_text = Inventory.get_inventory_by_character(character, db).describe()

        embed_equipment = ArbEmbed(f'Снаряжение персонажа', f'**——— ЭКИПИРОВКА ———**\n{clothes_text}\n\n**——— ОРУЖИЕ ———**\n{weapons_text}', footer=f'character_id: {character}')
        embed_inventory = ArbEmbed(f'Инвентарь', items_text if items_text else '*(Здесь будут отображаться ваши предметы)*')
        return embed_equipment, embed_inventory

    @commands.slash_command(name='character_body', description='Ранения персонажа')
    async def __character_body(self, ctx, character_id:int=None):
        if not character_id:
            user_id = ctx.author.id
            character = get_owners_character(user_id)
        else:
            character = character_id

        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа')
            return

        embed_stats, embed_injuries = self.character_health_embeds(character)

        embeds = [embed_stats, embed_injuries]

        view = Paginator(embeds, ctx, {1:'Физ. Показатели', 2:'Ранения'})
        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @commands.slash_command(name='relations', description='Взаимоотношения с другими персонажами')
    async def __character_relations(self, ctx, character_id:int=None):
        if not character_id:
            user_id = ctx.author.id
            character = get_owners_character(user_id)
        else:
            character = character_id

        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа')
            return

        embed_info = self.character_info(character)
        embed_relations = self.character_relations(character)
        embeds = [embed_info, embed_relations]
        view = Paginator(embeds, ctx, {1: 'Информация', 2: 'Отношения'})
        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @commands.slash_command(name='self_info', description='Информация о вашем персонаже')
    async def __character_info(self, ctx, character_id:int=None):
        if not character_id:
            user_id = ctx.author.id
            character = get_owners_character(user_id)
        else:
            character = character_id

        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа')
            return

        db = DataManager()

        embed_info = self.character_info(character, db)
        embed_skills = self.character_skills_and_chars_embed(character, db)
        embeds = [embed_info, embed_skills]

        view = Paginator(embeds, ctx, {1: 'Информация', 2: 'Навыки и характеристики'})
        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)

    @commands.slash_command(name='self_inventory', description=f'Информация о вашем инвенторе')
    async def __character_inventory(self, ctx, character_id:int=None):
        if not character_id:
            user_id = ctx.author.id
            character = get_owners_character(user_id)
        else:
            character = character_id

        if character is None:
            await ctx.send(f'{ctx.author.mention}, у вас нет персонажа')
            return

        db = DataManager()

        embed_equipment, embed_inventory = self.character_equipment(character, db)
        embeds = [embed_equipment, embed_inventory]

        view = Paginator(embeds, ctx, {1: 'Снаряжение', 2: 'Инвентарь'})
        await view.update_button()
        await ctx.respond(embed=embeds[0], view=view)


def setup(bot):
    bot.add_cog(CharacterMenu(bot))