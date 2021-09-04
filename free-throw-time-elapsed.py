# Rebuilding Owen Phillips blog post in Python
# https://thef5.substack.com/p/how-to-pbp2?token=eyJ1c2VyX2lkIjoxMzE3MzQyLCJwb3N0X2lkIjozODgwNTQzNCwiXyI6InV3cXVIIiwiaWF0IjoxNjI3ODcwODA0LCJleHAiOjE2Mjc4NzQ0MDQsImlzcyI6InB1Yi00NzQzMCIsInN1YiI6InBvc3QtcmVhY3Rpb24ifQ.DD2gU-NmYH93ScbBGWCv3rw3ldhsAStQydOdM7MCbmA
import requests
import pandas as pd
import numpy as np
import io
from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguegamefinder
import matplotlib.pyplot as plt
from joypy import joyplot

headers  = {
    'Connection': 'keep-alive',
    'Accept': 'application/json, text/plain, */*',
    'x-nba-stats-token': 'true',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36',
    'x-nba-stats-origin': 'stats',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Referer': 'https://stats.nba.com/',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
}

play_by_play_url = "https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_0042000404.json"
response = requests.get(url=play_by_play_url, headers=headers).json()
play_by_play = response['game']['actions']
df = pd.DataFrame(play_by_play)

# get game logs from the reg season
gamefinder = leaguegamefinder.LeagueGameFinder(season_nullable='2020-21', 
                                              league_id_nullable='00', 
                                              season_type_nullable='Regular Season')
games = gamefinder.get_data_frames()[0]

# Get a list of distinct game ids 
game_ids = games['GAME_ID'].unique().tolist()

# create function that gets pbp logs from the 2020-21 season
def get_data(game_id):
    play_by_play_url = "https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_"+game_id+".json"
    response = requests.get(url=play_by_play_url, headers=headers).json()
    play_by_play = response['game']['actions']
    df = pd.DataFrame(play_by_play)
    df['gameid'] = game_id
    return df

# get data from all ids (takes awhile)
pbpdata = []
for game_id in game_ids:
    game_data = get_data(game_id)
    pbpdata.append(game_data)

df = pd.concat(pbpdata, ignore_index=True)

# calculate time elapsed between a free throw and whatever action came before it
df = df.sort_values(by=['gameid', 'orderNumber'])
df['dtm'] = df['timeActual'].astype('datetime64[s]')
df['ptm'] = df['dtm'].shift(1)
df['elp'] = (df['dtm'] - df['ptm']).astype('timedelta64[s]')
df['pact'] = df['actionType'].shift(1)
df['psub'] = df['subType'].shift(1)
df['pmake'] = df['shotResult'].shift(1)
df[df['actionType'] == "freethrow"] 
df[df['elp'] > 0]
df = df[['gameid',
                     'clock',
                     'actionNumber',
                     'orderNumber',
                     'subType',
                     'pact',
                     'psub',
                     'dtm',
                     'ptm',
                     'pmake',
                     'elp',
                     'personId',
                     'playerNameI',
                     'shotResult',
                     'period']]

###

# read in cleaned data from GitHub, if you want
url = "https://raw.githubusercontent.com/Henryjean/data/main/cleanpbplogs2021.csv"
response = requests.get(url).content
df = pd.read_csv(io.StringIO(response.decode('utf-8')))

# filter df down to free throw attempts
df = df[(
    ((df.subType == '2 of 2') & ((df.psub == '1 of 2') | (df.psub == 'offensive'))) |
    ((df.subType == '2 of 3') & ((df.psub == '1 of 3') | (df.psub == 'offensive'))) |
    ((df.subType == '3 of 3') & ((df.psub == '2 of 3') | (df.psub == 'offensive')))
    )]

# find average time elapsed between 1st and 2nd (or 2nd and 3rd) FTs when previous action was a FT 
# get the count so we can filter for those with > 50
df['avgtime'] = df.groupby(['playerNameI', 'personId']).elp.transform('mean')
df['count'] = df.groupby(['playerNameI', 'personId']).elp.transform('count')
df = df[df['count'] > 50]
df = df.sort_values(['avgtime', 'playerNameI'], ascending=True)

names = df['playerNameI'].unique().tolist()
plt.figure()

joyplot(
    data=df[['elp', 'avgtime', 'playerNameI']],
    by=('avgtime'),
    x_range=(0,40),
    labels=names,
    figsize=(12,8)
    )

plt.title('Real Time Elapsed Between Consecutive Free Throw Attempts', fontsize=20)
plt.show()