# -*- coding: utf-8 -*-
"""
FUTpuppeteer.info
~~~~~~~~~~~~~~~~~~~~~
This module implements the puppetSniper's methods to get and return information.
"""
import requests
import math
import re
import json
import requests as r
from . import parse
from .misc import Global, multi_log
from selenium.common.exceptions import NoSuchElementException
from retrying import retry
from datetime import datetime
from ruamel.yaml import YAML

yaml = YAML()
yaml.explicit_start = True
yaml.indent(mapping=4)
yaml.preserve_quotes = True
need_relisting = False


###################################################
#
# General Information
#
###################################################
def get_player_info(player_id, include_futbin_price=True):
    """
    Returns player information as a dict using player_id
    Note: Can't seem to get team/league info without using way too many server hits
    :param player_id: str or int: Must use EA's player ID # found in data/Global.fifa_players.json
    :param include_futbin_price: bool: Looks up the futbin price for the player. Recommend setting False if using for a large number of players
    """
    player_id = str(player_id)
    try:
        if Global.fifa_players[player_id]['surname']:
            name = Global.fifa_players[player_id]['surname']
        else:
            name = '{} {}'.format(Global.fifa_players[player_id]['first_name'], Global.fifa_players[player_id]['last_name'])
        nation_name = Global.fifa_players[player_id]['nation_name']
        rating = int(Global.fifa_players[player_id]['rating'])
    except KeyError:
        try:
            temp_id = get_base_id(player_id)
            name = '{} {}'.format(Global.fifa_players[temp_id]['first_name'], Global.fifa_players[temp_id]['last_name'])
            nation_name = Global.fifa_players[temp_id]['nation_name']
            rating = int(Global.fifa_players[temp_id]['rating'])
        except KeyError:
            name = 'Unable to locate {} in Global.fifa_players'.format(player_id)
            rating = 0
            nation_name = ''
    link = 'https://www.easports.com/fifa/ultimate-team/fut/database/player/{}'.format(player_id)
    img = 'https://fifa17.content.easports.com/fifa/fltOnlineAssets/B1BA185F-AD7C-4128-8A64-746DE4EC5A82/2018/fut/items/images/players/html5/134x134/{}.png' \
        .format(player_id)
    player = {
        'name': name,
        'asset_id': player_id,
        'link': link,
        'image': img
    }
    if include_futbin_price:
        futbin_price = get_price(player_id)
        tier = get_tier(futbin_price)
        player.update({'futbin_price': futbin_price, 'tier': tier})
    if nation_name:
        player.update({'nation_name': nation_name, 'rating': rating})
    return player


def get_base_id(special_id):
    if not special_id:
        return special_id
    special_id = int(special_id)
    resource_id = special_id + 0xC4000000  # 3288334336
    version = 0
    while resource_id > 0x01000000:  # 16777216
        version += 1
        if version == 1:
            resource_id -= 0x80000000  # 2147483648  # 0x50000000  # 1342177280 ?  || 0x2000000  # 33554432
        elif version == 2:
            resource_id -= 0x03000000  # 50331648
        else:
            resource_id -= 0x01000000  # 16777216
    return str(resource_id)


def get_id_from_name(name):
    for player, info in Global.fifa_players.items():
        if parse.remove_accents(name) == info['first_name'] + info['last_name'] or parse.remove_accents(name) == info['surname']:
            return str(info['id'])
        elif parse.remove_accents(name) == info['last_name']:
            return str(info['id'])
        elif parse.remove_accents(name) == info['first_name']:
            return str(info['id'])
    multi_log(message='Unable to find {}'.format(name), level='warn')
    return None


def get_special_ids(base_id):
    ids = {}
    players = r.get(
        'https://www.easports.com/uk/fifa/ultimate-team/api/fut/item?jsonParamObject=%7B%22page%22:1,%22baseid%22:{},%22position%22:%22LF,CF,RF,ST,LW,LM,CAM,CDM,CM,RM,RW,LWB,LB,CB,RB,RWB%22%7D'.format(
            base_id)).json()
    for item in players['items']:
        color = item.get('color', None)
        if color not in list(ids.keys()) and color:
            ids[color] = item.get('id')
    return ids


def get_tier(price):
    """
    Returns tier based off player price
    :param price: int: Player price
    """
    if 0 <= price < 1000:
        tier = '0000to0001'
    elif 1000 <= price < 5000:
        tier = '0001to0005'
    elif 5000 <= price < 10000:
        tier = '0005to0010'
    elif 10000 <= price < 30000:
        tier = '0010to0030'
    elif 30000 <= price < 50000:
        tier = '0030to0050'
    elif 50000 <= price < 100000:
        tier = '0050to0100'
    elif 100000 <= price < 250000:
        tier = '0100to0250'
    elif 250000 <= price < 500000:
        tier = '0250to0500'
    elif 500000 <= price < 2000000:
        tier = '0500to2000'
    elif price >= 2000000:
        tier = '2000plus'
    else:
        raise Exception('BIN price too high. Price:', price)
    return tier


###################################################
#
# PRICING
#
###################################################
# noinspection PyBroadException,PyUnboundLocalVariable
def get_price(player_id, obj=None, return_updated=False, return_prp=False, source='futbin'):
    """
    Gets Futbin price based off appropriate platform for player from player id
    :param player_id: str: Use EA's player ID
    :param obj: Object: use your bot's Object to auto-get platform. Otherwise, defaults to pc
    :param return_updated: bool: returns how long ago price was updated, in seconds. It then returns a tuple: (price, updated)
    """
    player_id = str(player_id)
    if obj is None:
        platform = 'ps'
    else:
        if 'pc' in obj.platform:
            platform = 'pc'
        elif 'xbox' in obj.platform:
            platform = 'xbox'
        else:
            platform = 'ps'
    try:
        if source == 'futbin':
            data = requests.get('https://www.futbin.com/18/playerPrices?player=' + player_id).json()
            data = data[player_id]
            prices = [data['prices'][platform]['LCPrice'], data['prices'][platform]['LCPrice2'],
                      data['prices'][platform]['LCPrice3'], data['prices'][platform]['LCPrice4'],
                      data['prices'][platform]['LCPrice5']]
            updated = str(data['prices'][platform]['updated']).lower()
            if 'hour' in updated:
                updated = int(updated.split(' ')[0]) * 60 * 60
            elif 'min' in updated:
                updated = int(updated.split(' ')[0]) * 60
            elif 'sec' in updated:
                updated = int(updated.split(' ')[0])
            elif 'never' in updated:
                updated = 999999999999999999
            else:
                updated = 999999999999999999
            prp = int(data['prices'][platform]['PRP'])
        elif source == 'futhead':
            if platform == 'xbox':
                platform = 'xb'
            data = requests.get('http://www.futhead.com/prices/api/?year=18&id=' + player_id).json()
            try:
                data = data[player_id]
                prices = data[platform + 'LowFive']
                s = int(data[platform + 'Time']) / 1000.0
                updated = (datetime.now() - datetime.fromtimestamp(s)).seconds
                prp = 50
            except KeyError:
                prices = [0]
                updated = 999999
                prp = 0
        temp_prices = []
        for price in prices:
            price = parse.price_parse(price)
            if price != 0:
                temp_prices.append(price)
        if len(temp_prices) == 0:
            return 0
        prices = sorted(temp_prices, key=int)
        weighted_price = 0
        for i, price in enumerate(prices):
            if i == 0:
                weighted_price += price * 3
            elif i == 1:
                weighted_price += price * 2
            elif i == 2:
                weighted_price += price * 1
            else:
                weighted_price += price
        if len(prices) == 5:
            bin_price = weighted_price / 8
        elif len(prices) == 4:
            bin_price = weighted_price / 7
        elif len(prices) == 3:
            bin_price = weighted_price / 6
        elif len(prices) == 2:
            bin_price = weighted_price / 5
        elif len(prices) == 1:
            bin_price = weighted_price / 3
        bin_price = int(bin_price)
        tier = get_tier(bin_price)
        bin_price = round_down(bin_price, Global.rounding_tiers[tier])
        if bin_price < 200:
            multi_log(message='Something wrong with futbin pricing: {}'.format(prices), level='error')
            bin_price = 0
    except requests.exceptions.RequestException:
        multi_log(message='Futbin Unreachable', level='error')
        return 0
    except (json.decoder.JSONDecodeError, TypeError):
        multi_log(message='Unable to get price for {}'.format(player_id), level='error')
        return 0
    if not return_updated and not return_prp:
        return bin_price
    elif return_updated and not return_prp:
        return bin_price, updated
    elif not return_updated and return_prp:
        return bin_price, prp
    elif return_updated and return_prp:
        return bin_price, updated, prp
    if not return_updated:
        return bin_price

    return bin_price, updated


@retry(wait_fixed=500, stop_max_attempt_number=3)
def get_futbin_market(obj, market, min_price=0, max_price=1000000000):
    return_data = {
        'momentum': 0,
        'up_players': [],
        'down_players': []
    }
    # Get top growing players
    futbin_url = 'https://www.futbin.com/market/{}'.format(market)
    if obj.logged_in:
        obj.new_tab(futbin_url)
    else:
        obj.driver.get(futbin_url)
    obj.keep_alive(Global.small_max)
    obj.location = 'futbin'
    if 'ps' in obj.platform:
        obj.driver.find_element_by_xpath('//*[@id="ps4_hover"]').click()
    elif 'xbox' in obj.platform:
        obj.driver.find_element_by_xpath('//*[@id="xone_hover"]').click()
    else:
        obj.driver.find_element_by_xpath('//*[@id="pc_hover"]').click()

    def get_table(heading):
        players = []
        header = obj.__get_xpath__("//th[contains(text(), '{}')]".format(heading))
        table = header.find_element_by_xpath('../../..')
        tbody = table.find_element_by_tag_name('tbody')
        for row in tbody.find_elements_by_xpath('.//tr'):
            r_data = row.find_elements_by_xpath('.//td')
            if r_data[0].text == 'No Results were found':
                multi_log(message='{} table is empty'.format(heading), level='warn')
                return None
            try:
                name = parse.remove_accents(r_data[0].find_element_by_tag_name('a').text)
                price = parse.price_parse(r_data[0].text.split('(')[1].split(')')[0])
                if '+' in r_data[1].text:
                    change = r_data[1].text.split('+')[1].split('.')[0]
                    positive = True
                else:
                    change = r_data[1].text.split('-')[1].split('.')[0]
                    positive = False
                link = r_data[0].find_element_by_tag_name('a').get_attribute('href')
                image = r_data[0].find_element_by_tag_name('img').get_attribute('src')
                player_id = image.split('/')[-1].split('.')[0].replace('p', '')
            except NoSuchElementException:
                multi_log(message='Trouble getting table', level='warn')
                return None
            player = {
                'name': name,
                'futbin_price': int(price),
                'change': int(change),
                'asset_id': str(player_id),
                'positive': positive,
                'link': link,
                'image': image
            }
            if min_price < player['futbin_price'] <= max_price:
                players.append(player)
        # Get market momentum
        momentum = obj.driver.find_element_by_class_name('liquidFillGaugeText').text.split('.')[0]
        return_data['momentum'] = int(momentum)
        if heading == 'Top Up':
            return_data['up_players'] = players
        elif heading == 'Top Down':
            return_data['down_players'] = players
    tables = ['Top Up', 'Top Down']
    for data in tables:
        get_table(data)
    while obj.driver.window_handles[-1] != obj.driver.window_handles[0]:
        obj.close_tab()
    if not obj.logged_in:
        obj.__login__()
    if return_data['up_players'] or return_data['down_players']:
        multi_log(obj, 'Got market info for {} market'.format(market))
    return return_data


@retry(wait_fixed=500, stop_max_attempt_number=3)
def get_futbin_cheapest_sbc(obj, min_price=0, max_price=1000000000):
    return_data = []
    # Get players
    futbin_url = 'https://www.futbin.com/stc/cheapest?min_price={}&max_price={}'.format(min_price, max_price)
    if obj.logged_in:
        obj.new_tab(futbin_url)
    else:
        obj.driver.get(futbin_url)
    obj.keep_alive(Global.small_max)
    obj.location = 'futbin'
    player_rows = obj.__get_class__('top-stc-players-row')
    for row in player_rows:
        try:
            return_data.append(row.find_element_by_tag_name('img').get_attribute('src').split('/')[-1].split('.')[0])
        except AttributeError as e:
            pass
    while obj.driver.window_handles[-1] != obj.driver.window_handles[0]:
        obj.close_tab()
    if not obj.logged_in:
        obj.__login__()
    if return_data:
        multi_log(obj, 'Got cheapest SBC info')
    return return_data


###################################################
#
# MISCELLANEOUS
#
###################################################
def round_down(x, to):
    float(to)
    return int(math.floor(x / to)) * to


def set_config_variables(obj):
    with open(obj.config_file, 'r', encoding='utf-8') as stream:
        config = yaml.load(stream)
    setattr(obj, 'config', config)
    for setting in config:
        setattr(obj, setting, config[setting])

