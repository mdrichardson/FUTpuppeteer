from datetime import datetime, timedelta
from . import parse
from .misc import multi_log, Global
from .info import get_price
import requests as r
import sqlite3
from sqlite3 import Error
import os
import ast
import json
import re


#######################
# SETUP
#######################
def create_connection(db='user'):
    """ create a database connection to a SQLite database """
    try:
        if db == 'user':
            conn = sqlite3.connect(os.path.realpath('./data/user_db.sqlite'))
            conn.isolation_level = None
            return conn
        elif db == 'ea':
            conn = sqlite3.connect(os.path.realpath('./data/ea_db.sqlite'))
            conn.isolation_level = None
            return conn
    except Error as e:
        print(e)


def unpack_player_rows(rows):
    lists = ['specialities', 'traits']
    dicts = ['attributes', 'nation_info', 'club_info', 'image', 'special_images', 'league_info']
    bools = ['is_gk', 'is_special', 'is_loan']
    all_players = []
    for row in rows:
        d = dict(zip(row.keys(), row))
        for k, v in d.items():
            if type(v) is str and len(v) == 0:
                d[k] = None
            if k.lower() in lists:
                if not v:
                    d[k] = []
                else:
                    d[k] = ast.literal_eval(v)
            elif k.lower() in dicts:
                d[k] = ast.literal_eval(v)
            elif k.lower() in bools:
                if v == 1:
                    d[k] = True
                elif v == 0 or not v:
                    d[k] = False
                else:
                    print(k, v)
                    raise Exception('wrong bool')
        all_players.append(d)
    return all_players


def create_tables():
    conn_user = create_connection(db='user')
    conn_ea = create_connection(db='ea')
    cur_user = conn_user.cursor()
    cur_ea = conn_ea.cursor()
    credits = """ CREATE TABLE IF NOT EXISTS credits (
                                            credits INTEGER,
                                            time TEXT,
                                            bot_number INTEGER
                                        ); """
    buy_sell = """ CREATE TABLE IF NOT EXISTS buy_sell (
                                                name TEXT,
                                                amount INTEGER,
                                                time TEXT,
                                                strategy TEXT,
                                                type TEXT,
                                                quality TEXT,
                                                rare TEXT,
                                                image TEXT,
                                                asset_id TEXT,
                                                bot_number INTEGER,
                                                full_item TEXT,
                                                action TEXT,
                                                expected_profit NUMERIC,
                                                credit_impact NUMERIC                                                
                                            ); """
    market_monitor = """ CREATE TABLE IF NOT EXISTS market_monitor (
                                                    time TEXT,
                                                    name TEXT,
                                                    average_bid NUMERIC,
                                                    minimum_bin NUMERIC,
                                                    asset_id TEXT                                               
                                                ); """

    fifa_players = """ CREATE TABLE IF NOT EXISTS fifa_players ( resource_id text, curve integer, images text, color text, rating integer, icon_attributes text, 
    is_special INTEGER, gk_diving integer, gk_reflexes integer, sprint_speed integer, attributes text, volleys integer, foot text, traits text, stamina integer, 
    ball_control integer, club_info text, balance integer, common_name text, dribbling integer, skill_moves integer, marking integer, age integer, reactions integer, 
    potential integer, league text, league_info text, asset_id text, short_passing integer, nation text, nation_info text, first_name text, long_shots integer, long_passing integer, height integer, 
    attack_workrate text, jumping integer, positioning integer, name text, last_name text, standing_tackle integer, gk_kicking integer, finishing integer, 
    is_gk INTEGER, interceptions integer, quality text, defense_workrate text, heading_accuracy integer, penalties integer, specialities text, aggression integer, 
    crossing integer, vision integer, player_type text, composure integer, position text, sliding_tackle integer, gk_handling integer, strength integer, 
    free_kick_accuracy integer, shot_power integer, birth_date text, position_full text, weak_foot integer, agility integer, acceleration integer, weight integer, 
    club text, PRIMARY KEY(resource_id) ); """

    fifa_balls = """ CREATE TABLE IF NOT EXISTS fifa_balls (
                                                        id PRIMARY KEY,
                                                        name TEXT                                             
                                                    ); """

    fifa_clubs = """ CREATE TABLE IF NOT EXISTS fifa_clubs (
                                                            id PRIMARY KEY,
                                                            name TEXT                                             
                                                        ); """

    fifa_leagues = """ CREATE TABLE IF NOT EXISTS fifa_leagues (
                                                            id PRIMARY KEY,
                                                            name TEXT                                             
                                                        ); """

    fifa_nations = """ CREATE TABLE IF NOT EXISTS fifa_nations (
                                                            id PRIMARY KEY,
                                                            name TEXT                                             
                                                        ); """

    fifa_play_styles = """ CREATE TABLE IF NOT EXISTS fifa_play_styles (
                                                            id PRIMARY KEY,
                                                            name TEXT                                             
                                                        ); """

    fifa_stadiums = """ CREATE TABLE IF NOT EXISTS fifa_stadiums (
                                                            id PRIMARY KEY,
                                                            name TEXT                                             
                                                        ); """

    cur_user.execute(credits)
    cur_user.execute(buy_sell)
    cur_user.execute(market_monitor)
    cur_ea.execute(fifa_players)
    cur_ea.execute(fifa_balls)
    cur_ea.execute(fifa_clubs)
    cur_ea.execute(fifa_leagues)
    cur_ea.execute(fifa_nations)
    cur_ea.execute(fifa_play_styles)
    cur_ea.execute(fifa_stadiums)


#######################
# EA DATABASE
#######################
def add_player_to_db(player, from_futbin=False):
    conn = create_connection(db='ea')
    cur = conn.cursor()
    club_name = player['club_info']['name']
    for k, v in player.items():
        if type(v) is list or type(v) is dict:
            player[k] = str(v)
        elif type(v) is bool:
            if v:
                player[k] = 1
            else:
                player[k] = 0
    columns = ', '.join(player.keys())
    placeholders = ', '.join('?' * len(player))
    if not from_futbin:
        sql = 'INSERT or UPDATE INTO fifa_players ({}) VALUES ({})'.format(columns, placeholders)
    else:
        sql = 'INSERT INTO fifa_players ({}) VALUES ({})'.format(columns, placeholders)
    try:
        cur.execute(sql, tuple(player.values()))
        print('Added or Updated: Name: {}  |  Res_ID: {}  |  Rating: {}  |  Club: {}  |  Color: {}'.format(player['name'], player['resource_id'], player['rating'], club_name, player['color']))
    except sqlite3.IntegrityError:
        if from_futbin:
            sql = 'UPDATE fifa_players SET futbin_id = ? WHERE resource_id = ?'
            try:
                cur.execute(sql, (player['futbin_id'], player['resource_id']))
                print('Updated: Name: {}  |  Res_ID: {}  |  Rating: {}  |  Club: {}  |  Color: {}'.format(player['name'], player['resource_id'], player['rating'],
                                                                                                          club_name, player['color']))
            except Exception as e:
                print('Error: "{}" while adding player futbin_id to database'.format(e))
                print(player)
        else:
            pass
    except Exception as e:
        print('Error: "{}" while adding player to database'.format(e))
        print(player)


def get_all_db_players():
    """
    Query all rows in the players table
    :param conn: the Connection object
    :return:
    """
    conn = create_connection(db='ea')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM fifa_players")
    rows = cur.fetchall()
    return unpack_player_rows(rows)


def update_player_data(player_id=None):
    if not player_id:
        print('Updating player database. This will take close to an hour.')
    all_players = {}
    page = 1
    previous_players = []
    while True:
        if page % 50 == 0 and not player_id:
            print('Currently on page {} (of approximately 750) of database'.format(page))
        if not player_id:
            players = r.get('https://www.easports.com/fifa/ultimate-team/api/fut/item?page={}'.format(page)).json()['items']
        else:
            try:
                players = r.get('http://www.easports.com/fifa/ultimate-team/api/fut/item?jsonParamObject=%7B%22id%22:{}%7D'.format(player_id)).json()['items']
            except json.decoder.JSONDecodeError:
                try:
                    players = r.get('http://www.easports.com/fifa/ultimate-team/api/fut/item?jsonParamObject=%7B%22baseid%22:{}%7D'.format(player_id)).json()['items']
                except json.decoder.JSONDecodeError:
                    return None
            if not players:
                return None
        if players == previous_players or not players or page > 1100:
            break
        for player in players:
            attributes = {}
            for attribute in player['attributes']:
                if attribute['name'] == 'fut.attribute.PAC':
                    attributes['pace'] = attribute['value']
                elif attribute['name'] == 'fut.attribute.SHO':
                    attributes['shooting'] = attribute['value']
                elif attribute['name'] == 'fut.attribute.PAS':
                    attributes['passing'] = attribute['value']
                elif attribute['name'] == 'fut.attribute.DRI':
                    attributes['dribbling'] = attribute['value']
                elif attribute['name'] == 'fut.attribute.DEF':
                    attributes['defense'] = attribute['value']
                elif attribute['name'] == 'fut.attribute.PHY':
                    attributes['physical'] = attribute['value']
            all_players[str(player['baseId'])] = {
                'asset_id': str(player['baseId']),
                # SKILLS
                'acceleration': player['acceleration'],
                'aggression': player['aggression'],
                'agility': player['agility'],
                'balance': player['balance'],
                'ball_control': player['ballcontrol'],
                'composure': player['composure'],
                'crossing': player['crossing'],
                'curve': player['curve'],
                'dribbling': player['dribbling'],
                'finishing': player['finishing'],
                'free_kick_accuracy': player['freekickaccuracy'],
                'heading_accuracy': player['headingaccuracy'],
                'interceptions': player['interceptions'],
                'jumping': player['jumping'],
                'long_passing': player['longpassing'],
                'long_shots': player['longshots'],
                'marking': player['marking'],
                'penalties': player['penalties'],
                'positioning': player['positioning'],
                'potential': player['potential'],
                'reactions': player['reactions'],
                'short_passing': player['shortpassing'],
                'shot_power': player['shotpower'],
                'sliding_tackle': player['slidingtackle'],
                'sprint_speed': player['sprintspeed'],
                'stamina': player['stamina'],
                'standing_tackle': player['standingtackle'],
                'strength': player['strength'],
                'vision': player['vision'],
                'volleys': player['volleys'],
                'weak_foot': player['weakFoot'],
                'gk_diving': player['gkdiving'],
                'gk_handling': player['gkhandling'],
                'gk_kicking': player['gkkicking'],
                'gk_reflexes': player['gkreflexes'],
                # SKILL INFO
                'attributes': attributes,
                'attack_workrate': player['atkWorkRate'],
                'defense_workrate': player['defWorkRate'],
                'foot': player['foot'],
                'icon_attributes': player['iconAttributes'],
                'skill_moves': player['skillMoves'],
                'specialities': player['specialities'],
                'traits': player['traits'],
                # CARD INFO
                'color': player['color'],
                'is_special': player['isSpecialType'],
                'position': player['position'],
                'position_full': player['positionFull'],
                'quality': player['quality'],
                'rating': player['rating'],
                'resource_id': str(player['id']),
                # PLAYER INFO
                'age': player['age'],
                'birth_date': player['birthdate'],
                'club_info': {
                    'image_urls': player['club']['imageUrls'],
                    'name': player['club']['name'],
                    'abbreviated_name': player['club']['abbrName'],
                },
                'club': str(player['club']['id']),
                'common_name': player['commonName'],
                'first_name': player['firstName'],
                'height': player['height'],
                'images': {
                    'large': player['headshot']['largeImgUrl'],
                    'medium': player['headshot']['medImgUrl'],
                    'small': player['headshot']['smallImgUrl'],
                },
                'is_gk': player['isGK'],
                'last_name': player['lastName'],
                'league': str(player['league']['id']),
                'league_info': {
                    'name': player['league']['name'],
                    'abbreviated_name': player['league']['abbrName']
                },
                'name': player['name'],
                'nation': str(player['nation']['id']),
                'nation_info': {
                    'image_urls': player['nation']['imageUrls'],
                    'name': player['nation']['name'],
                    'abbreviated_name': player['nation']['abbrName']
                },
                'player_type': player['playerType'],
                'weight': player['weight'],
            }
            if len(players) == 1:
                result = add_player_to_db(all_players[str(player['baseId'])])
                return result
            else:
                add_player_to_db(all_players[str(player['baseId'])])
        page += 1
        if player_id:
            break
    if not player_id:
        print('Player database updated')


def get_player_info(player_id, id_type='base', rating=None, color=None, club=None, return_all=False, return_any=False):
    """
        Get player info for closest db match
        :param conn: the Connection object
        :return:
        """
    conn = create_connection(db='ea')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    variables = [player_id]
    if int(player_id) > 300000:
        id_type = 'resource'
    if id_type == 'base':
        command = "SELECT * FROM fifa_players WHERE asset_id = ?"
        if rating and not color or (rating and color.lower() != 'marquee' and color.lower() != 'ones_to_watch'):
            variables.append(int(rating))
            command += ' and rating = ?'
        if color:
            variables.append(color)
            command += ' and color = ?'
        if club:
            variables.append(str(club))
            command += ' and club = ?'
    elif id_type == 'resource':
        command = "SELECT * FROM fifa_players WHERE resource_id = ?"
    else:
        command = "SELECT * FROM fifa_players WHERE futbin_id = ?"

    cur.execute(command, variables)

    rows = cur.fetchall()
    all_players = unpack_player_rows(rows)
    if len(all_players) == 0:
        return None
    if return_all:
        return all_players
    if id_type in ['resource', 'futbin']:
        return all_players[0]
    matches = []
    ignore_colors_if_multiple = ['fut_champions']
    for player in all_players:
        if len(all_players) == 1 or (not rating and not color and not club) and player['asset_id'] == player['resource_id']:
            return player
        else:
            if rating and int(player['rating']) != int(rating):
                continue
            if color and player['color'] != color:
                continue
            if club and str(player['club']) != str(club):
                continue
            matches.append(player)
    if len(matches) == 0:
        return None
    elif len(matches) > 1 and not return_any:
        for i, player in enumerate(matches):
            for color in ignore_colors_if_multiple:
                if color in player['color']:
                    del matches[i]
        if len(matches) == 1:
            return matches[0]
        else:
            if int(player_id) < 300000:
                for match in matches:
                    if int(match['resource_id']) < 300000:
                        return match
            print('Unable to narrow down to a single player match. Use more criteria (rating, color, club). Used: {} {} {} {}'.format(player_id, rating, color, club))
            print('Returning most of the results for: {}'.format(matches[0]['name']))
            most_expensive = (0, 0)
            for i, match in enumerate(matches):
                futbin_price = get_price(match['resource_id'])
                if futbin_price > most_expensive[0]:
                    most_expensive = (futbin_price, i)
            return matches[most_expensive[1]]
    else:
        return matches[0]


def add_futbin_player_to_db(futbin_link):
    from lxml import html

    def get_stat(stat, main=False):
        if main:
            return tree.xpath('//*[@id="main-{}-val-0"]/div[3]'.format(stat))[0].text_content()
        else:
            return tree.xpath('//*[@id="sub-{}-val-0"]/div[3]'.format(stat))[0].text_content()

    def parse_workrate(wr):
        atk, dfns = wr.split('/')[0], wr.split('/')[-1]
        wrs = [atk, dfns]
        for i, w in enumerate(wrs):
            if w == 'H':
                wrs[i] = 'High'
            elif w == 'M':
                wrs[i] = 'Medium'
            else:
                wrs[i] = 'Low'
        return wrs[0], wrs[1]

    page = r.get(futbin_link)
    tree = html.fromstring(page.content)
    attributes = {
        'pace': get_stat('pace', True),
        'shooting': get_stat('shooting', True),
        'passing': get_stat('passing', True),
        'dribbling': get_stat('dribblingp', True),
        'defense': get_stat('defending', True),
        'physical': get_stat('heading', True),
    }
    atk_wr, def_wr = parse_workrate(tree.xpath('//*[@id="Player-card"]/div[9]/div')[0].text_content())
    specialities = [s.text_content()[1:] for s in tree.xpath('//*[@id="specialities_content"]//div')]
    traits = [t.text_content()[1:] for t in tree.xpath('//*[@id="traits_content"]//div')]
    color = parse.futbin_to_ea_color(tree.xpath('//*[@id="Player-card"]')[0].get('class'))
    specials = ['futmas', 'sbc', 'award-winner', 'icon', 'sbc_premium', 'toty', 'otw', 'if', 'halloween', 'purple', 'marquee', 'promo', 'award_winner',
                'europe_motm', 'fut_champions_gold', 'fut_champions_silver', 'fut_mas', 'gotm', 'halloween', 'legend', 'marquee', 'motm',
                'ones_to_watch', 'purple', 'sbc_base', 'sbc_premium', 'totw_gold', 'totw_silver', 'toty', 'motm_eu', 'fut-bd', 'stpatrick']
    rating = tree.xpath('//*[@id="Player-card"]/div[1]')[0].text_content()
    quality = 'gold' if int(rating) >= 75 else 'silver' if int(rating) >= 60 else 'bronze'
    position = tree.xpath('//*[@id="Player-card"]/div[3]')[0].text_content()
    try:
        age = tree.xpath('//*[@id="info_content"]/table/tr[16]/td/a')[0].text_content()
        if 'years' not in age:
            age = tree.xpath('//*[@id="info_content"]/table/tr[15]/td/a')[0].text_content()
    except IndexError:
        age = tree.xpath('//*[@id="info_content"]/table/tr[15]/td/a')[0].text_content()
    age = age.split(' years')[0][-2:]
    try:
        player = {
            'asset_id': str(tree.xpath('//*[@id="page-info"]')[0].get('data-baseid')),
            # SKILLS
            'acceleration': get_stat('acceleration'),
            'aggression': get_stat('aggression'),
            'agility': get_stat('agility'),
            'balance': get_stat('balance'),
            'ball_control': get_stat('ballcontrol'),
            'composure': get_stat('composure'),
            'crossing': get_stat('crossing'),
            'curve': get_stat('curve'),
            'dribbling': get_stat('dribbling'),
            'finishing': get_stat('finishing'),
            'free_kick_accuracy': get_stat('freekickaccuracy'),
            'heading_accuracy': get_stat('headingaccuracy'),
            'interceptions': get_stat('interceptions'),
            'jumping': get_stat('jumping'),
            'long_passing': get_stat('longpassing'),
            'long_shots': get_stat('longshotsaccuracy'),
            'marking': get_stat('marking'),
            'penalties': get_stat('penalties'),
            'positioning': get_stat('positioning'),
            'potential': 0,
            'reactions': get_stat('reactions'),
            'short_passing': get_stat('shortpassing'),
            'shot_power': get_stat('shotpower'),
            'sliding_tackle': get_stat('slidingtackle'),
            'sprint_speed': get_stat('sprintspeed'),
            'stamina': get_stat('stamina'),
            'standing_tackle': get_stat('standingtackle'),
            'strength': get_stat('strength'),
            'vision': get_stat('vision'),
            'volleys': get_stat('volleys'),
            'weak_foot': tree.xpath('//*[@id="Player-card"]/div[8]/div[1]')[0].text_content().replace(' ', ''),
            'gk_diving': get_stat('pace', True),
            'gk_handling': get_stat('shooting', True),
            'gk_kicking': get_stat('passing', True),
            'gk_reflexes': get_stat('dribblingp', True),
            # SKILL INFO
            'attributes': attributes,
            'attack_workrate': atk_wr,
            'defense_workrate': def_wr,
            'foot': tree.xpath('//*[@id="info_content"]/table/tr[8]/td')[0].text_content(),
            'icon_attributes': None,
            'skill_moves': tree.xpath('//*[@id="info_content"]/table/tr[5]/td')[0].text_content(),
            'specialities': specialities,
            'traits': traits,
            # CARD INFO
            'color': color,
            'is_special': True if color in specials else False,
            'position': position,
            'position_full': tree.xpath('//*[@id="Player-card"]/div[3]')[0].text_content(),
            'quality': quality,
            'rating': rating,
            'resource_id': str(tree.xpath('//*[@id="page-info"]')[0].get('data-player-resource')),
            'futbin_id': str(futbin_link.split('/')[-2]),
            # PLAYER INFO
            'age': age,
            'birth_date': None,
            'club_info': {
                'image_urls': [tree.xpath('//*[@id="player_club"]')[0].get('src')],
                'name': tree.xpath('//*[@id="info_content"]/table/tr[2]/td/a')[0].text_content(),
                'abbreviated_name': tree.xpath('//*[@id="info_content"]/table/tr[2]/td/a')[0].text_content(),
            },
            'club': str(tree.xpath('//*[@id="player_club"]')[0].get('src').split('/')[-1].split('.')[0]),
            'common_name': tree.xpath('//*[@id="Player-card"]/div[2]')[0].text_content(),
            'first_name': tree.xpath('//*[@id="info_content"]/table/tr[1]/td')[0].text_content().split(' ')[0],
            'height': tree.xpath('//*[@id="info_content"]/table/tr[9]/td')[0].text_content().split('cm')[0],
            'images': {
                'large': tree.xpath('//*[@id="player_pic"]')[0].get('src'),
                'medium': tree.xpath('//*[@id="player_pic"]')[0].get('src'),
                'small': tree.xpath('//*[@id="player_pic"]')[0].get('src'),
            },
            'is_gk': True if position == 'GK' else False,
            'last_name': tree.xpath('//*[@id="info_content"]/table/tr[1]/td')[0].text_content().split(' ')[-1],
            'league': str(tree.xpath('//*[@id="info_content"]/table/tr[4]/td/img')[0].get('src').split('/')[-1].split('.')[0]),
            'league_info': {
                'name': tree.xpath('//*[@id="info_content"]/table/tr[4]/td/a')[0].text_content(),
                'abbreviated_name': tree.xpath('//*[@id="info_content"]/table/tr[4]/td/a')[0].text_content(),
            },
            'name': tree.xpath('//*[@id="Player-card"]/div[2]')[0].text_content(),
            'nation': str(tree.xpath('//*[@id="player_nation"]')[0].get('src').split('/')[-1].split('.')[0]),
            'nation_info': {
                'image_urls': [tree.xpath('//*[@id="player_nation"]')[0].get('src')],
                'name': tree.xpath('//*[@id="info_content"]/table/tr[3]/td/a')[0].text_content(),
                'abbreviated_name': tree.xpath('//*[@id="info_content"]/table/tr[3]/td/a')[0].text_content(),

            },
            'player_type': tree.xpath('//*[@id="info_content"]/table/tr[11]/td')[0].text_content(),
            'weight': tree.xpath('//*[@id="info_content"]/table/tr[10]/td')[0].text_content(),
        }
    except Exception as e:
        print(e)
    add_player_to_db(player, from_futbin=True)


def get_ea_name_from_id(ea_db, thing, type='id'):
    conn = create_connection(db='ea')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    thing = str(thing)
    if type == 'id':
        search = 'id'
    else:
        search = 'name'
    command = "SELECT name FROM {} WHERE {} = ?".format(ea_db, search)
    cur.execute(command, (thing, ))
    print(ea_db, thing)
    try:
        result = cur.fetchone()[0]
        print('got it: ', result)
        return result
    except TypeError:
        return None


def save_ea_db(db, id, name):
    conn = create_connection(db='ea')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    command = "INSERT or REPLACE INTO {} (id, name) VALUES (?, ?)".format(db)
    cur.execute(command, (id, name))


def update_ea_data():
    players = r.get('https://fifa18.content.easports.com/fifa/fltOnlineAssets/B1BA185F-AD7C-4128-8A64-746DE4EC5A82/2018/fut/items/web/players.json').json()
    misc = r.get('https://www.easports.com/fifa/ultimate-team/web-app/loc/en_US.json')
    misc = misc.text
    # Parse data in misc
    nations_data = re.findall('"search.nationName.nation([0-9]+)": "(.+)"', misc)
    for i in nations_data:
        Global.fifa_nations[int(i[0])] = i[1]
        save_ea_db('fifa_nations', i[0], i[1])
    leagues_data = re.findall('"global.leagueFull.%s.league([0-9]+)": "(.+)"' % 2018, misc)
    for i in leagues_data:
        Global.fifa_leagues[int(i[0])] = i[1]
        save_ea_db('fifa_leagues', i[0], i[1])
    teams_data = re.findall('"global.teamFull.%s.team([0-9]+)": "(.+)"' % 2018, misc)
    for i in teams_data:
        Global.fifa_clubs[int(i[0])] = i[1]
        save_ea_db('fifa_clubs', i[0], i[1])
    stadium_data = re.findall('"global.stadiumFull.%s.stadium([0-9]+)": "(.+)"' % 2018, misc)
    for i in stadium_data:
        Global.fifa_stadiums[int(i[0])] = i[1]
        save_ea_db('fifa_stadiums', i[0], i[1])
    balls_data = re.findall('"BallName_([0-9]+)": "(.+)"', misc)
    for i in balls_data:
        Global.fifa_balls[int(i[0])] = i[1]
        save_ea_db('fifa_balls', i[0], i[1])
    play_styles_data = re.findall('"playstyles.%s.playstyle([0-9]+)": "(.+)"' % 2018, misc)
    for i in play_styles_data:
        Global.fifa_play_styles[int(i[0])] = i[1]
        save_ea_db('fifa_play_styles', i[0], i[1])

    # Save it all
    with open('data/fifa_nations.json', 'w', encoding='utf-8') as nations:
        nations.write(json.dumps(Global.fifa_nations, indent=2, ensure_ascii=False))
    with open('data/fifa_leagues.json', 'w', encoding='utf-8') as leagues:
        leagues.write(json.dumps(Global.fifa_leagues, indent=2, ensure_ascii=False))
    with open('data/fifa_clubs.json', 'w', encoding='utf-8') as teams:
        teams.write(json.dumps(Global.fifa_clubs, indent=2, ensure_ascii=False))
    with open('data/fifa_stadiums.json', 'w', encoding='utf-8') as stadiums:
        stadiums.write(json.dumps(Global.fifa_stadiums, indent=2, ensure_ascii=False))
    with open('data/fifa_balls.json', 'w', encoding='utf-8') as balls:
        balls.write(json.dumps(Global.fifa_balls, indent=2, ensure_ascii=False))
    with open('data/fifa_play_styles.json', 'w', encoding='utf-8') as play_styles:
        play_styles.write(json.dumps(Global.fifa_play_styles, indent=2, ensure_ascii=False))
    # Parse Players data, add nation, league, team names, and save
    for i in players['Players'] + players['LegendsPlayers']:
        Global.fifa_players[i['id']] = {'asset_id': str(i['id']),
                                        'first_name': parse.remove_accents(i['f']),
                                        'last_name': parse.remove_accents(i['l']),
                                        'surname': parse.remove_accents(i.get('c')),
                                        'rating': i['r'],
                                        'nationality': i['n'],
                                        'nation_name': parse.remove_accents(Global.fifa_nations.get(i['n']))
                                        }
    with open('data/fifa_players.json', 'w', encoding='utf-8') as players:
        players.write(json.dumps(Global.fifa_players, indent=2, ensure_ascii=False))


#######################
# USER DATABASE
#######################
def bought_sold(obj, item, action, strategy, amount, expected_profit=0):
    if Global.use_database:
        conn = create_connection(db='user')
        cur = conn.cursor()

        if strategy == '':
            strategy = 'unknown'

        name = item['item_name']
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        item_type = item['item_type']
        quality = item['quality']
        rare = item['rare']
        image = item.get('image')
        asset_id = item.get('asset_id')
        bot_number = obj.bot_number
        if action == 'bought':
            credit_impact = -int(amount)
        else:
            credit_impact = abs(int(amount))

        sql = """INSERT INTO buy_sell (action, name, amount, time, strategy, type, quality, rare, image, asset_id, bot_number, full_item, expected_profit, credit_impact)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
        values = (action, name, amount, time, strategy, item_type, quality, rare, image, asset_id, bot_number, str(item), expected_profit, credit_impact)
        try:
            cur.execute(sql, values)
        except Exception as e:
            multi_log(obj, 'Buy_sell database error: {}'.format(e), level='error')
            pass
        multi_log(obj, message='Added to database: {}'.format(item), level='debug')


def save_credits(obj):
    if Global.use_database:
        conn = create_connection(db='user')
        cur = conn.cursor()

        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        get_last = """SELECT time from credits WHERE bot_number = (?) ORDER BY time DESC LIMIT 1;"""
        cur.execute(get_last, (obj.bot_number, ))
        try:
            last_time = datetime.strptime(cur.fetchone()[0], '%Y-%m-%d %H:%M:%S')
        except TypeError:
            time = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
            last_time = time - timedelta(hours=100)
        time = datetime.now()
        if ((time - last_time).seconds / 60) > 30:
            time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            sql = """INSERT INTO credits(credits, time, bot_number)
                             VALUES (?, ?, ?) ;"""
            values = (obj.credits, time, obj.bot_number)
            try:
                cur.execute(sql, values)
            except Exception as e:
                multi_log(obj, 'Credits BIN error: {}'.format(e), level='error')
                pass
            multi_log(obj, message='Saved credits: {}'.format(obj.credits), level='debug')


def save_market_data(obj, name, asset_id, average_bid=None, minimum_bin=None):
    if Global.use_database:
        conn = create_connection(db='user')
        cur = conn.cursor()
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        sql = """INSERT INTO market_monitor(time, name, average_bid, minimum_bin, asset_id)
                         VALUES (?, ?, ?, ?, ?) ;"""
        values = (time, name, average_bid, minimum_bin, asset_id)
        try:
            cur.execute(sql, values)
        except Exception as e:
            multi_log(obj, 'Market Data error: {}'.format(e), level='error')
            pass
        cur.close()
        multi_log(obj, message='Saved market data: {} {} {}'.format(name, average_bid, minimum_bin), level='debug')


def get_profit(obj):
    if Global.use_database:
        conn = create_connection(db='user')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        def money_parse(money):
            if type(money) is int:
                return money
            elif not money:
                return 0
            else:
                money = str(money)
                return int(money.replace('$', '').replace(',', '').replace('(', '').replace(')', '').split('.')[0])

        end = datetime.now()
        start = (end - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        end = end.strftime('%Y-%m-%d %H:%M:%S')
        bot_number = obj.bot_number

        cur.execute("""SELECT *
                       FROM buy_sell
                       WHERE time BETWEEN
                           ? AND ? AND bot_number = ?;""", (start, end, bot_number))

        hour_rows = cur.fetchall()
        hour_profit = 0
        for i, row in enumerate(hour_rows):
            hour_profit += money_parse(row[-2])
        end = datetime.now()
        start = (end - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        end = end.strftime('%Y-%m-%d %H:%M:%S')

        cur.execute("""SELECT *
                           FROM buy_sell
                           WHERE time BETWEEN
                               ? AND ? AND bot_number = ?;""", (start, end, bot_number))

        day_rows = cur.fetchall()
        day_profit = 0
        for row in day_rows:
            day_profit += money_parse(row[-2])

        return hour_profit, day_profit
    else:
        return 0, 0
