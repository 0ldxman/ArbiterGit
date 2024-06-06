from ArbDatabase import DataManager

def get_owners_character(user_id:int):
  db = DataManager()
  return db.select_dict('META_INFO', filter=f'id = {user_id}')[0].get('playing_as', None)