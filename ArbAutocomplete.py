from typing import Callable

import discord

from ArbDatabase import DataManager


class ArbAutoComplete:
    @staticmethod
    def db_options(table:str, column:str, filter:str=None) -> Callable:
        def options():
            db = DataManager()
            print('тут')
            response_list = db.select_dict(table, filter=filter)
            total_response = []
            for res in response_list:
                total_response.append(res.get(column))
            print(total_response)
            return total_response
        return options

    @staticmethod
    def extract(table:str, find_column:str, value, extract_column:str) -> float | int | str:
        db = DataManager()
        response = db.select_dict(table, filter=f'{find_column} = "{value}"')
        if response:
            return response[0].get(extract_column)


class AAC:
    @staticmethod
    def db_call(table:str, column:str, filter:str=None) -> Callable:
        async def options(ctx: discord.AutocompleteContext):
            db = DataManager()
            response_list = db.select_dict(table, filter=filter)
            total_response = []
            for res in response_list:
                total_response.append(res.get(column))

            return total_response
        return options

    @staticmethod
    def db_options(table:str, column:str, filter:str=None):
        db = DataManager()
        response_list = db.select_dict(table, filter=filter)
        total_response = []
        for res in response_list:
            total_response.append(res.get(column))

        return total_response

    @staticmethod
    def extract(table: str, find_column: str, value, extract_column: str) -> float | int | str:
        db = DataManager()
        response = db.select_dict(table, filter=f'{find_column} = "{value}"')
        if response:
            return response[0].get(extract_column)

#
# class ExampleAutocompletion(commands.Cog):
#     ctx_parse = discord.ApplicationContext
#
#     def __init__(self, bot: discord.Bot):
#         self.bot = bot.user
#
#     @staticmethod
#     def colorAutocomplete(self: discord.AutocompleteContext):
#         return mycolors
#
#     @staticmethod
#     def flowertypeAutocomplete(self: discord.AutocompleteContext):
#         chosen_color = self.options["color"]
#         match chosen_color:
#             case "red":
#                 return ["Rose", "Georgina"]
#             case "white":
#                 return ["Chrisantem", "Gortensia"]
#             case "yellow":
#                 return ["Sunflower", "Narciss"]
#             case _:
#                 return ["There is no flower with this color"]