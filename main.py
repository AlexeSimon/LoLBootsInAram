import requests
import time

APIKEY = ""  # put your api key here
PUUID = ""  # put your summoner puuid here
game_queried = 600  # How many games to query, normals ; limit is 100 queries every 2 min for developer keys.


BASE = "https://europe.api.riotgames.com"
headers = {"X-Riot-Token": APIKEY}


# Find all game ids for provided puuid
def get_match_ids(start=0, count=100):
    url = BASE + "/lol/match/v5/matches/by-puuid/{}/ids?type=normal&start={}&count={}"

    match_ids = []
    while count > 0:
        match_ids.extend(requests.get(url.format(PUUID, start, 100 if count > 100 else count), headers=headers).json())
        start += 100
        count -= 100
    return match_ids


# Find items id that corresponds to boots
def get_boots():
    url = "http://ddragon.leagueoflegends.com/cdn/11.24.1/data/en_US/item.json"
    return [item[0] for item in requests.get(url).json().get("data").items() if "Boots" in item[1].get("tags")]


#BOOTS_IDS = get_boots()
BOOTS_IDS = ['1001', '2422', '3006', '3009', '3020', '3047', '3111', '3117', '3158']  # already computed


# Get aram matches as participants dtos
def get_arams_participants(matchIds):
    url = BASE + "/lol/match/v5/matches/{matchId}"
    arams = []
    for matchId in matchIds:
        while True:
            response = requests.get(url.format(matchId=matchId), headers=headers)
            if response.status_code == 200:
                break
            elif response.status_code == 429:
                print("Triggered request limit of 100 every 2 minutes. Waiting for 2 minutes...")
                time.sleep(120)
            elif response.status_code == 404:
                print("Match file not found. Skipping.")
                break
            else:
                print("unknown response : " + str(response.json()))
                break
        if "info" in response.json():
            if response.json().get("info").get("gameMode") == "ARAM":
                arams.extend(response.json().get("info").get("participants"))
    arams = list(filter(lambda participant: participant.get("puuid") == PUUID, arams))
    return arams


# Check if a participant dto contains boots in the item list
def check_for_boots(participant):
    items = [str(participant.get("item" + str(i))) for i in range(7)]
    if any(boot in items for boot in BOOTS_IDS):
        return True
    return False


# Game object for saving purposes
class GameBootsInfo:
    def __init__(self, champion, has_boots, did_win):
        self.champion = champion
        self.has_boots = has_boots
        self.did_win = did_win

    def __repr__(self) -> str:
        return "champion={}, has_boots={}, did_win={}".format(self.champion, self.has_boots, self.did_win)


# Champion object for saving purposes
class ChampionInfo:
    def __init__(self, champion, total=0, wins=0, bought_boots=0, wins_with_boots=0):
        self.champion = champion
        self.total = total
        self.wins = wins
        self.bought_boots = bought_boots
        self.wins_with_boots = wins_with_boots

    def __repr__(self):
        return "{} with {:.2f}% win rate across {} games (with boots: {:.2f}% across {} games or {:.2f} of total)".format(self.champion, 100*self.wins/self.total, self.total, 100*self.wins_with_boots/self.bought_boots if self.bought_boots != 0 else 0, self.bought_boots, 100*self.bought_boots/self.total)


# Turns participants list into GameBootsInfo list
def get_game_boots_info(participants):
    games_boots_info = []
    for participant in participants:
        games_boots_info.append(
            GameBootsInfo(champion=participant.get("championName"), has_boots=check_for_boots(participant),
                          did_win=bool(participant.get("win"))))
    return games_boots_info


# Compute win rate with and without boots
print("Aggregating {} games...".format(game_queried))
games_info = get_game_boots_info(get_arams_participants(get_match_ids(0, game_queried)))

total_aram_games = 0
total_aram_win = 0
total_aram_games_with_boots = 0
total_aram_games_without_boots = 0
total_aram_win_with_boots = 0
total_aram_win_without_boots = 0
champions = {}

for game in games_info:
    if game.champion not in champions:
        champions[game.champion] = ChampionInfo(game.champion, 0, 0)

    total_aram_games += 1
    champions[game.champion].total += 1

    if game.did_win:
        total_aram_win += 1
        champions[game.champion].wins +=1

    if game.has_boots:
        total_aram_games_with_boots += 1
        champions[game.champion].bought_boots += 1
    else:
        total_aram_games_without_boots += 1

    if game.has_boots and game.did_win:
        total_aram_win_with_boots += 1
        champions[game.champion].wins_with_boots += 1

    if not game.has_boots and game.did_win:
        total_aram_win_without_boots += 1


print("Quick boots stats:")
print("Played {} arams within the last {} games ({:.2f}% of all games are arams), with a win rate of {:.2f}%.".format(total_aram_games, game_queried, 100 * total_aram_games / game_queried, 100 * total_aram_win / total_aram_games))
print("Boots: {:.2f}% win rate across {} aram games with boots. Boots bought in {:.2f}% of all aram games.".format(100 * total_aram_win_with_boots / total_aram_games_with_boots, total_aram_games_with_boots, 100 * total_aram_games_with_boots / total_aram_games))
print("No Boots: {:.2f}% win rate across {} aram games without boots. Boots not bought in {:.2f}% of all aram games.".format(100 * total_aram_win_without_boots / total_aram_games_without_boots, total_aram_games_without_boots, 100 * total_aram_games_without_boots / total_aram_games))

print("\nWriting champions.csv ...\n")
with open("champions.csv", "w+") as f:
    f.write("Champion; total arams; total wins; games with boots; wins with boots\n")
    for champion in champions.values():
        f.write("\"{}\";{};{};{};{}\n".format(champion.champion, champion.total, champion.wins, champion.bought_boots, champion.wins_with_boots))

print("Done.")
