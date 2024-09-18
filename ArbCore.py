from ArbDatabase import DataManager, DataModel, DataDict


class Review(DataModel):
    def __init__(self, id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.review_id: int = id
        DataModel.__init__(self, 'PLAYERS_REVIEWS', f'id = {id}')
        self.player_id: int | None = self.get('player', None)
        self.title: str = self.get('title', 'Неизвестный отзыв') if self.get('title') else 'Отзыв'
        self.review_text: str = self.get('desc', '') if self.get('desc') else 'Пользователь не оставил пояснения к отзыву'
        self.rating: float = self.get('rating', 0)
        self.reviewer: int | None = self.get('reviewer', None)

    def to_dict(self):
        return {
            'id': self.review_id,
            'player_id': self.player_id,
            'title': self.title,
            'review_text': self.review_text,
            'rating': self.rating,
            'reviewer': self.reviewer
        }

    def to_embed(self, ctx):
        from ArbUIUX import ArbEmbed
        reviewer = ctx.bot.get_user(self.reviewer)
        reviewer_name = reviewer.display_name if self.reviewer else 'Анонимно'
        reviewer_avatar = reviewer.avatar if self.reviewer else 'https://ia800305.us.archive.org/31/items/discordprofilepictures/discordred.png'

        embed = ArbEmbed(title=f'',
                         desc=f'## "{self.title}"\n'
                              f'# {":star:" * int(round(self.rating))}\n'
                              f'-# — *"{self.review_text}"*',
                         footer=f'Идентификатор отзыва: {self.review_id}')
        embed.set_author(reviewer_name, icon_url=reviewer_avatar)

        return embed

    @staticmethod
    def calculate_rating(player_id:int):
        reviews = Review.get_all_player_reviews(player_id)
        if not reviews:
            return 5

        count = len(reviews)

        total_rating = sum([review.rating for review in reviews])

        return round(total_rating/count, 1)

    @staticmethod
    def get_all_player_reviews(player_id:int, **kwargs):
        db = kwargs.get('data_manager', DataManager())
        return [Review(review.get('id'), data_manager=db) for review in db.select_dict('PLAYERS_REVIEWS', filter=f'player = {player_id}')]

    @staticmethod
    def create_review(player_id:int, **kwargs):
        db = kwargs.get('data_manager', DataManager())
        title = kwargs.get('title', 'Отзыв')
        review_text = kwargs.get('review_text', '')
        rating = kwargs.get('rating', 0)
        reviewer = kwargs.get('reviewer', None)

        review_id = db.maxValue('PLAYERS_REVIEWS', 'id') + 1

        db.insert('PLAYERS_REVIEWS', {'id': review_id,
                                      'player': player_id,
                                      'title': title,
                                      'desc': review_text,
                                      'rating': rating,
                                      'reviewer': reviewer})

        return Review(review_id, data_manager=db)


class RPRequest(DataModel):
    def __init__(self, request_id:int, **kwargs):
        self.request_id = request_id
        self.data_manager = kwargs.get('data_manager', DataManager())
        DataModel.__init__(self, 'SERVERS_REQUESTS', f'id = {self.request_id}', data_manager=self.data_manager)
        self.requester_id = self.get('requester', None)
        self.server_id = self.get('server', None)
        self.admin_id = self.get('admin', None)
        self.title = self.get('title', 'Личный')
        self.description = self.get('desc', 'Описание игрового ивента недоступно')
        self.type = self.get('type', 'Ивент')
        self.timestamp = self.get('timestamp', None)
        self.planned_timestamp = self.get('plan_timestamp', None)
        self.status = self.get('status', 'Не рассмотрено')

    async def request_notification(self, ctx):
        server = Server(ctx.guild.id, data_manager=self.data_manager)
        embed = self.to_embed(ctx)
        chat = ctx.guild.get_channel(server.responses_chat)
        if not chat:
            chat = ctx.guild.get_thread(server.responses_chat)
        await chat.send('## @everyone поступил новый запрос на игровую отыгровку!', embed=embed)

    def to_embed(self, ctx):
        from ArbUIUX import ArbEmbed

        requester = ctx.bot.get_user(self.requester_id)
        admin = ctx.bot.get_user(self.admin_id)
        timestamp = self.timestamp
        planned_timestamp = self.planned_timestamp if self.planned_timestamp else '||Не указано||'

        embed = ArbEmbed(title=f'Запрос на {self.type.lower()} ивент "{self.title}"',
                         desc=f'> **Идентификатор:** #{self.request_id}\n'
                              f'> **Отправитель:** ||{requester.mention}||\n'
                              f'> **Администратор:** ||{admin.mention if admin else "Не указан"}||\n'
                              f'> **Дата и время проведения:** {planned_timestamp}\n'
                              f'\n'
                              f'\n — *"{self.description}"*',
                         footer=f'{requester.display_name} | {timestamp}',
                         footer_logo=requester.avatar)

        return embed

    @staticmethod
    def get_all_requests(server_id:int, **kwargs):
        db = kwargs.get('data_manager', DataManager())
        return [RPRequest(request.get('id'), data_manager=db) for request in db.select_dict('SERVERS_REQUESTS', filter=f'server = {server_id}')]

    @staticmethod
    def create_request(server_id: int, **kwargs):
        import datetime

        db = kwargs.get('data_manager', DataManager())
        title = kwargs.get('title', 'Отыгровка')
        description = kwargs.get('description', 'Описание игрового ивента недоступно')
        type = kwargs.get('type', 'Ивент')
        timestamp = kwargs.get('timestamp', datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
        planned_timestamp = kwargs.get('planned_timestamp', None)
        status = kwargs.get('status', 'Не рассмотрено')

        request_id = db.maxValue('SERVERS_REQUESTS', 'id') + 1

        db.insert('SERVERS_REQUESTS', {'id': request_id,
                                       'server': server_id,
                                       'requester': kwargs.get('requester_id', None),
                                       'admin': kwargs.get('admin_id', None),
                                       'title': title,
                                       'desc': description,
                                       'type': type,
                                       'timestamp': timestamp,
                                       'plan_timestamp': planned_timestamp,
                                       'status': status})

        return RPRequest(request_id, data_manager=db)

    @classmethod
    def get_request_by_id(cls, request_id:int, **kwargs):
        db = kwargs.get('data_manager', DataManager())
        return RPRequest(request_id, data_manager=db) if db.check('SERVERS_REQUESTS', f'id = {request_id}') else None


class Player(DataModel):
    def __init__(self, player_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        DataModel.__init__(self, 'PLAYERS', f'id = {player_id}')
        self.player_id = player_id
        self.current_character = self.get('character_id', None)

    @staticmethod
    def register(player_id:int, current_character: int = None, data_manager: DataManager = None):
        if data_manager:
            db = data_manager
        else:
            db = DataManager()

        if db.check('PLAYERS', f'id = {player_id}'):
            return
        else:
            db.insert('PLAYERS', {'id': player_id, 'character_id': current_character})

    def get_servers_max_characters(self) -> dict[int, int]:
        if self.data_manager.check('PLAYERS_SERVERS', f'id = {self.player_id}'):
            servers_data = self.data_manager.select_dict('PLAYERS_SERVERS', filter=f'id = {self.player_id}')
            data = {}
            for server in servers_data:
                data[server.get('server_id')] = server.get('max_chars', 0)

            return data
        else:
            return {}

    def get_character(self) -> int:
        return self.current_character if self.current_character else None

    def get_character_data(self):
        from ArbCharacters import Character
        if self.get_character():
            return Character(self.get_character(), data_manager=self.data_manager)
        else:
            return None

    def get_all_server_characters(self, server_id:int):
        servers_characters = self.get_all_characters()
        return servers_characters.get(server_id, [])

    def get_all_characters(self):
        server_characters = {}
        characters = self.data_manager.select_dict('CHARS_INIT', filter=f'owner = {self.player_id}')
        for character in characters:
            if character.get('server') not in server_characters:
                server_characters[character.get('server')] = []
            server_characters[character.get('server')].append(character.get('id'))

        return server_characters

    async def player_card(self, ctx):
        from ArbUIUX import ArbEmbed, Paginator
        from ArbCharacters import Character

        player = ctx.bot.get_user(self.player_id)
        server = ctx.guild.id

        rating = Review.calculate_rating(self.player_id)
        player_name = player.display_name
        player_avatar_url = player.avatar
        reviews = Review.get_all_player_reviews(self.player_id, data_manager=self.data_manager)

        characters_on_server = len(self.get_all_server_characters(server))
        current_character = self.get_character_data()

        main_embed = ArbEmbed(f'Карточка игрока {player_name}',
                              f'# {":star:" * int(round(rating))} **({round(rating, 2)}/5)**\n Текущий персонаж: ||**{current_character.name if current_character else "Отсутствует"}**||\n Персонажей на сервере: **{characters_on_server} / {self.get_servers_max_characters().get(server, 0)}**',
                              footer=f'Количество отзывов: {len(reviews)}',
                              logo_url=player_avatar_url)

        await ctx.respond('', embed=main_embed)

    def get_characters_list(self) -> list:
        characters = self.get_all_characters().values()
        total_characters = []
        for chars in list(characters):
            total_characters.extend(chars)

        return total_characters

    def switch_character(self, character_id:int):
        self.data_manager.update('PLAYERS', {'character_id': character_id}, f'id = {self.player_id}')

    def leave_character(self, character_id:int):
        current_character = self.current_character

        if current_character == character_id:
            self.data_manager.update('PLAYERS', {'character_id': None}, f'id = {self.player_id}')
        self.data_manager.update('CHARS_INIT', {'owner': None}, f'id = {character_id}')




class Server(DataModel):
    def __init__(self, server_id:int, **kwargs):
        self.data_manager = kwargs.get('data_manager', DataManager())
        self.id = server_id
        DataModel.__init__(self, 'SERVER_SETTINGS', f'id = {server_id}')
        self.responses_chat = self.get('responses_chat', None)
        self.registration_chat = self.get('registration_chat', None)
        self.features_chat = self.get('features_chat', None)
        self.moderation_chat = self.get('moderation_chat', None)
        self.basic_max_characters = self.get('basic_max_characters', 1)
        self.currency = self.get('currency', 'USD') if self.get('currency') else 'USD'

    def get_max_characters(self, player_id:int) -> int:
        if self.data_manager.check('PLAYERS_SERVERS', f'id = {player_id} AND server_id = {self.id}'):
            return self.data_manager.select_dict('PLAYERS_SERVERS', filter=f'id = {player_id} AND server_id = {self.id}')[0].get('max_chars', 0)
        else:
            return 0

    @staticmethod
    def register_server(server_id:int, **kwargs):
        db = kwargs.get('data_manager', DataManager())
        db.insert('SERVER_SETTINGS', {'id': server_id})

    @staticmethod
    def check_server_register(server_id:int, **kwargs) -> bool:
        db = kwargs.get('data_manager', DataManager())
        return db.check('SERVER_SETTINGS', f'id = {server_id}')

    @staticmethod
    def register_server_if_not_exist(server_id:int, **kwargs):
        db = kwargs.get('data_manager', DataManager())
        if not Server.check_server_register(server_id, data_manager=db):
            Server.register_server(server_id, data_manager=db)

        return Server(server_id, data_manager=db)

    def get_server_regforms(self):
        from ArbRegistration import RegForm

        regs = RegForm.get_all_forms_by_server(self.id)
        embeds = [reg.to_embed() for reg in regs]

        return embeds

    def register_player(self, player_id:int):
        if not self.data_manager.check('PLAYERS_SERVERS', f'id = {player_id} AND server_id = {self.id}'):
            self.data_manager.insert('PLAYERS_SERVERS', {'id': player_id,'server_id': self.id, 'max_chars': self.basic_max_characters if self.basic_max_characters else 1})


class Guild:
    def __init__(self, guild_id:int, **kwargs):
        pass