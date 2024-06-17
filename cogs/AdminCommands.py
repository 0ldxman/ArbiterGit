import discord
from discord.ext import commands
from ArbCharacters import InterCharacter
from ArbRaces import Race
from ArbDatabase import DataManager
from ArbHealth import LocalDisease, LocalInjury, Body
from ArbUIUX import ArbEmbed, HealthEmbed, ErrorEmbed, SuccessEmbed
from ArbUtils.ArbDataParser import get_owners_character
from ArbDamage import Damage


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print(f'...Module {self.__class__.__name__} is ready')

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

def setup(bot):
    bot.add_cog(AdminCommands(bot))