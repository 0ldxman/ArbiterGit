import datetime

from ArbCombat.Battlefield import Battle, BattleObject, Round, Layer
from ArbCombat.Actor import Actor
#from ArbBattle import Actor
import pprint

time = datetime.datetime.now()
pprint.pprint(Actor(185).process_shot(0))

print(datetime.datetime.now() - time)