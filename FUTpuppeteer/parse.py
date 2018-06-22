from . import info, database
from .misc import Global, multi_log
import unicodedata
from selenium.common.exceptions import NoSuchElementException, TimeoutException


def remove_accents(string):
    if type(string) == str:
        string = string.encode(encoding='utf-8')
        string = string.decode(encoding='utf-8')
        norm_txt = unicodedata.normalize('NFD', string)
        shaved = ''.join(c for c in norm_txt if not unicodedata.combining(c))
        return unicodedata.normalize('NFC', shaved)
    else:
        return string


def item_parse(item_data, include_futbin_price=False):
    """Parser for item data. Returns nice dictionary.
    :params item_data: Item data received from ea servers.
    :params full: (optional) False if you're sniping and don't need extended info. Anyone really use this?
    """
    return_data = {}
    try:
        return_data = {
            'trade_id': str(item_data.get('tradeId')),
            'buy_now_price': item_data.get('buyNowPrice'),
            'trade_state': item_data.get('tradeState'),
            'bid_state': item_data.get('bidState'),
            'starting_bid': item_data.get('startingBid'),
            'id': str(item_data.get('itemData', {'id': None})['id'] or item_data.get('item', {'id': None})['id']),
            'offers': item_data.get('offers'),
            'current_bid': item_data.get('currentBid'),
            'time_left': item_data.get('expires'),  # seconds left
            'seller_established': item_data.get('sellerEstablished'),
            'seller_id': str(item_data.get('sellerId')),
            'seller_name': item_data.get('sellerName'),
            'watched': item_data.get('watched'),
            'timestamp': item_data.get('itemData').get('timestamp'),  # auction start
            'rating': item_data.get('itemData').get('rating'),
            'asset_id': str(item_data.get('itemData').get('assetId')),
            'resource_id': str(item_data.get('itemData').get('resourceId')),
            'item_state': item_data.get('itemData').get('itemState'),
            'rare_flag': item_data.get('itemData').get('rareflag'),
            'formation': item_data.get('itemData').get('formation'),
            'league': str(item_data.get('itemData').get('leagueId')),
            'league_name': remove_accents(Global.fifa_leagues.get(item_data.get('itemData').get('leagueId'))),
            'injury_type': item_data.get('itemData').get('injuryType'),
            'injury_games': item_data.get('itemData').get('injuryGames'),
            'last_sale_price': item_data.get('itemData').get('lastSalePrice'),
            'fitness': item_data.get('itemData').get('fitness'),
            'training': item_data.get('itemData').get('training'),
            'suspension': item_data.get('itemData').get('suspension'),
            'contract': item_data.get('itemData').get('contract'),
            'position': item_data.get('itemData').get('preferredPosition'),
            'play_style': item_data.get('itemData').get('playStyle'),  # used only for players
            'discard_value': item_data.get('itemData').get('discardValue'),
            'item_type': item_data.get('itemData').get('itemType'),
            'card_type': item_data.get('itemData').get('cardsubtypeid'),  # alias
            'card_subtype_id': str(item_data.get('itemData').get('cardsubtypeid')),  # used only for cards
            'owners': item_data.get('itemData').get('owners'),
            'untradeable': item_data.get('itemData').get('untradeable'),
            'morale': item_data.get('itemData').get('morale'),
            'stats_list': item_data.get('itemData').get('statsList'),  # what is this?
            'lifetime_stats': item_data.get('itemData').get('lifetimeStats'),
            'attribute_list': item_data.get('itemData').get('attributeList'),
            'team_id': str(item_data.get('itemData').get('teamid')),
            'team_name': remove_accents(Global.fifa_clubs.get(item_data.get('itemData').get('teamid'))),
            'assists': item_data.get('itemData').get('assists'),
            'lifetime_assists': item_data.get('itemData').get('lifetimeAssists'),
            'loyalty_bonus': item_data.get('itemData').get('loyaltyBonus'),
            'pile': item_data.get('itemData').get('pile'),
            'nation': str(item_data.get('itemData').get('nation')),
            'nation_name': remove_accents(Global.fifa_nations.get(item_data.get('itemData').get('nation'))),
            'year': item_data.get('itemData').get('resourceGameYear'),  # alias
            'resource_game_year': item_data.get('itemData').get('resourceGameYear'),
            'market_data_min_price': item_data.get('itemData').get('marketDataMinPrice'),
            'market_data_max_price': item_data.get('itemData').get('marketDataMaxPrice'),
            'count': item_data.get('count'),  # consumables only (?)
            'untradeable_count': item_data.get('untradeableCount'),  # consumables only (?)
            'resourceId': item_data.get('resourceId'),  # consumables only?
            'discardValue': item_data.get('discardValue'),  # consumables only?
            }
        if 'item' in item_data:  # consumables only (?)
            return_data.update({
                'card_asset_id': str(item_data.get('item').get('cardassetid')),
                'weight_rare': item_data.get('item').get('weightrare'),
                'gold': item_data.get('item').get('gold'),
                'silver': item_data.get('item').get('silver'),
                'bronze': item_data.get('item').get('bronze'),
                'consumables_contract_player': item_data.get('item').get('consumablesContractPlayer'),
                'consumables_contract_manager': item_data.get('item').get('consumablesContractManager'),
                'consumables_formation_player': item_data.get('item').get('consumablesFormationPlayer'),
                'consumables_formation_manager': item_data.get('item').get('consumablesFormationManager'),
                'consumables_position': item_data.get('item').get('consumablesPosition'),
                'consumables_training': item_data.get('item').get('consumablesTraining'),
                'consumables_training_player': item_data.get('item').get('consumablesTrainingPlayer'),
                'consumables_training_manager': item_data.get('item').get('consumablesTrainingManager'),
                'consumables_training_gk': item_data.get('item').get('consumablesTrainingGk'),
                'consumables_training_player_play_style': item_data.get('item').get('consumablesTrainingPlayerPlayStyle'),
                'consumables_training_gk_play_style': item_data.get('item').get('consumablesTrainingGkPlayStyle'),
                'consumables_training_manager_league_modifier': item_data.get('item').get('consumablesTrainingManagerLeagueModifier'),
                'consumables_healing': item_data.get('item').get('consumablesHealing'),
                'consumables_team_talks_player': item_data.get('item').get('consumablesTeamTalksPlayer'),
                'consumables_team_talks_team': item_data.get('item').get('consumablesTeamTalksTeam'),
                'consumables_fitness_player': item_data.get('item').get('consumablesFitnessPlayer'),
                'consumables_fitness_team': item_data.get('item').get('consumablesFitnessTeam'),
                'consumables': item_data.get('item').get('consumables'),
            })
        if return_data['item_type'] == 'player':
            return_data.update({'name': remove_accents(info.get_player_info(item_data.get('itemData').get('assetId'), False).get('name'))})
            if include_futbin_price:
                futbin_price = info.get_price(item_data.get('itemData').get('assetId'))
                return_data.update({
                    'futbin_price': futbin_price
                })
    except Exception as e:
        multi_log(message=e, level='error')
    return return_data


def sbc_category_parse(set_data, skip_complete=True, skip_upgrades=True):
    sbc_categories = []
    for category in set_data:
        if skip_upgrades and category['name'] == 'UPGRADES':
            break
        category_name = remove_accents(category['name'])
        sbc_category = {
            'category_name': category_name,
            'sets': []
        }
        for cat in category['sets']:
            if cat['repeatable'] is False and cat['timesCompleted'] > 0 and skip_complete:
                break
            else:
                set_name = remove_accents(cat['name'])
                set_data = {
                    'set_name': set_name,
                    'challenges_count': cat['challengesCount'],
                    }
                if 'awards' in cat:
                    awards = parse_awards(cat['awards'])
                    set_data.update({'awards': awards})
                sbc_category['sets'].append(set_data)
        sbc_categories.append(sbc_category)
    return sbc_categories


def sbc_challenge_parse(obj, set_data, set_name, skip_complete=True):
    set_name = remove_accents(set_name)
    sbc_set = {
        'set_name': set_name,
        'challenges': []
    }
    for challenge in set_data:
        if challenge['repeatable'] is False and challenge['timesCompleted'] > 0 and skip_complete:
            break
        else:
            challenge_data = {
                'challenge_name': remove_accents(challenge['name']),
            }
            if 'awards' in challenge:
                challenge_data.update({'awards': parse_awards(challenge['awards'])})
            else:
                for category in obj.sbc_sets:
                    for sets in category['sets']:
                        if remove_accents(sets['set_name']).lower() == remove_accents(challenge['name']).lower():
                            cat_i = obj.sbc_sets.index(category)
                            set_i = obj.sbc_sets[cat_i]['sets'].index(sets)
                            challenge_data.update({
                                'awards': parse_awards(obj.sbc_sets[cat_i]['sets'][set_i]['awards']),
                            })
            sbc_set['challenges'].append(challenge_data) if challenge_data not in sbc_set['challenges'] else multi_log(message='Not appended: {}'
                                                                                                                       .format(challenge_data), level='debug')
    return sbc_set


def parse_awards(awards):
    return_data = []
    for award in awards:
        if 'isUntradeable' in award:
            untradeable = 'isUntradeable'
        else:
            untradeable = 'is_untradeable'
        award_data = {
            'type': award.get('type'),
            'count': award.get('count'),
            'is_untradeable': award[untradeable],
        }
        if award.get('type') == 'item':
            award_data.update({
                'type': 'player',
                'id': str(award.get('itemData').get('id')),
                'loan': award.get('loan'),
            })
        elif award.get('type') == 'coins':
            award_data.update({'value': award.get('value')})
        elif award.get('type') == 'pack':
            if 'pack_type' in award:
                award_data.update({'pack_type': award.get('pack_type')})
            else:
                award_data.update({'pack_type': get_pack_type(award.get('value'))})
        return_data.append(award_data)
    return return_data


def get_pack_type(pack_id):
    if pack_id == 202:
        pack = 'Jumbo Silver Pack'
    elif pack_id == 205:
        pack = 'Premium Silver Jumbo'
    elif pack_id == 300:
        pack = 'Gold Pack'
    elif pack_id == 302:
        pack = 'Jumbo Gold'
    elif pack_id == 304:
        pack = 'Premium Gold Pack'
    elif pack_id == 306:
        pack = 'Premium Gold Jumbo'
    elif pack_id == 402:
        pack = 'Rare Consumable Pack'
    elif pack_id == 403:
        pack = 'Rare Gold Players Pack'
    elif pack_id == 404:
        pack = 'Mega Pack'
    elif pack_id == 405:
        pack = 'Rare Player Pack'
    elif pack_id == 406:
        pack = 'Jumbo Rare Player Pack'
    elif pack_id == 412:
        pack = 'Rare Mega Pack'
    elif pack_id == 500:
        pack = 'Gold Players Pack'
    elif pack_id == 502:
        pack = 'Premium Gold Players Pack'
    elif pack_id == 506:
        pack = 'Silver Players Premium'
    elif pack_id == 513:
        pack = 'Prime Gold Players'
    elif pack_id == 515:
        pack = 'Electrum Players Pack'
    elif pack_id == 516:
        pack = 'Premium Electrum Players'
    elif pack_id == 517:
        pack = 'Prime Electrum Players'
    elif pack_id == 808:
        pack = 'Two Rare Gold Players Pack'
    elif pack_id == 819:
        pack = 'Two Silver Players Pack'
    elif pack_id == 820:
        pack = 'Three Common Gold Players Pack'
    else:
        pack = 'Unknown Pack: {}'.format(pack_id)
    return pack


def price_parse(price):
    if not price:
        return price
    price = str(price).lower()
    thousand = False
    million = False
    if 'k' in price:
        thousand = True
    elif 'm' in price:
        million = True
    try:
        price = price.replace(',', '')
        price = price.replace(' ', '')
        price = price.replace('$', '')
        price = price.replace('(', '')
        price = price.replace(')', '')
        price = price.replace('+', '')
        price = price.replace('-', '')
        price = price.replace('k', '')
        price = price.replace('m', '')
    except (TypeError, ValueError):
        pass
    if '.' in price and thousand:
        price = (int(price.split('.')[0]) * 1000) + (int(price.split('.')[-1]) * 100)
    elif '.' in price and million:
        price = (int(price.split('.')[0]) * 1000000) + (int(price.split('.')[-1]) * 100000)
    elif million:
        price = int(price) * 100000
    elif thousand:
        price = int(price) * 1000
    else:
        price = int(round(float(price)))
    return price


def parse_item_list(items, get_price=False, obj=None):
    """
    Takes a WebElement list and turns parses the data into a list of dicts of the items
    :param items: WebElement <li>. Probably generated by `obj.__get_class__('listFUTItem', as_list=True)`
    :param get_price: Set to True to include futbin price of players
    :param obj: Session/bot object. Necessary to get platform for Futbin price
    :return: list of dicts of items from list
    """
    prices = {}
    if not obj and get_price:
        raise Exception('Error parsing item list. Must provide obj if getting futbin price')
    return_data = []
    players = {}
    for item in items:
        item_name = remove_accents(item.find_element_by_class_name('name').text)
        classes = item.find_element_by_xpath('.//div/div[1]/div[1]').get_attribute('class').split(' ')
        if 'rare' in classes:
            rare = True
        else:
            rare = False
        if 'bronze' in classes:
            quality = 'bronze'
        elif 'silver' in classes:
            quality = 'silver'
        elif 'gold' in classes:
            quality = 'gold'
        else:
            quality = None
        time_left = item.find_element_by_class_name('time').text.lower()
        if '<' in time_left:
            minus = True
        else:
            minus = False
        if time_left:
            if 'second' in time_left:
                time_left = int(time_left.split(' ')[0].replace('<', ''))
            elif 'minute' in time_left:
                time_left = 60 * int(time_left.split(' ')[0].replace('<', ''))
            elif 'hour' in time_left:
                time_left = 3600 * int(time_left.split(' ')[0].replace('<', ''))
            elif 'day' in time_left:
                time_left = 3600 * 24 * int(time_left.split(' ')[0].replace('<', ''))
            elif 'expire' in time_left:
                time_left = 0
            elif 'process' in time_left:
                time_left = 0
            else:
                time_left = 0
        if minus and time_left > 0:
            time_left -= 1
        try:
            start_price_area = item.find_element_by_class_name('auctionStartPrice')
            start_price = price_parse(start_price_area.find_element_by_class_name('value').get_attribute("innerHTML"))
            current_bid_area = item.find_element_by_xpath(".//*[contains(text(), 'Bid')]")
            cb_parent = current_bid_area.find_element_by_xpath('..')
            current_bid = price_parse(cb_parent.find_element_by_class_name('value').text)
            buy_now_area = item.find_element_by_xpath(".//*[contains(text(), 'Buy Now')]")
            bn_parent = buy_now_area.find_element_by_xpath('..')
            buy_now_price = price_parse(bn_parent.find_element_by_class_name('value').text)
        except NoSuchElementException:
            start_price = None
            current_bid = None
            buy_now_price = None
            pass
        item_data = {
            'item_name': item_name,
            'item_type': '',
            'element': item,
            'quality': quality,
            'rare': rare,
            'start_price': start_price,
            'current_bid': current_bid,
            'buy_now_price': buy_now_price,
            'time_left': time_left,
            'image': str(item.find_element_by_class_name('photo').get_attribute('src'))
        }
        if 'expired' in classes:
            item_data['expired'] = True
        else:
            item_data['expired'] = False
        if 'loan' in classes:
            item_data['loan'] = True
        else:
            item_data['loan'] = False
        if 'winning' in classes:
            item_data['bid_status'] = 'winning'
        elif 'outbid' in classes:
            item_data['bid_status'] = 'outbid'
        elif 'won' in classes:
            item_data['bid_status'] = 'won'
        else:
            item_data['bid_status'] = None
        item_data['asset_id'] = 0
        if any(s in classes for s in ['player', 'staff', 'badge', 'ball']):
            asset_id = str(item.find_element_by_class_name('photo').get_attribute('src').split('/')[-1].split('.')[0].replace('p', ''))
            item_data['asset_id'] = asset_id
            item_data['resource_id'] = asset_id
            if 'player' in classes:
                color = None
                colors = ['award_winner', 'europe_motm', 'fut_champions_gold', 'fut_champions_silver', 'fut_mas', 'gotm', 'halloween', 'legend',
                          'marquee', 'motm', 'ones_to_watch', 'purple', 'rare_bronze', 'rare_gold', 'rare_silver', 'sbc_base', 'sbc_premium', 'totw_gold',
                          'totw_silver', 'toty']
                for clr in colors:
                    for c in classes:
                        if clr == c:
                            color = c
                            break
                if not color:
                    standard = ['bronze', 'silver', 'gold']
                    for c in classes:
                        for s in standard:
                            if c.lower() == s.lower():
                                color = s
                                break
                    if 'rare' in classes:
                        color = 'rare_' + color
                    elif 'TOTW' in classes:
                        color = 'totw_' + color
                    elif 'OTW' in classes:
                        color = 'ones_to_watch'
                    elif 'eumotm' in classes:
                        color = 'europe_motm'
                rating = item.find_element_by_xpath('.//div/div[1]/div[1]/div[4]/div[1]').text
                club_id = str(item.find_element_by_class_name('badge').get_attribute('src').split('/')[-1].split('.')[0])
                search_data = (asset_id, rating, color, club_id)
                if players.get(search_data, None):
                    item_data = players[search_data]
                else:
                    if int(asset_id) > 300000:
                        additional_data = database.get_player_info(asset_id, id_type='resource', return_all=False)
                    else:
                        additional_data = database.get_player_info(asset_id, id_type='base', rating=rating, color=color, club=club_id, return_all=False)
                    if not additional_data:
                        print('No player: ', search_data)
                    elif additional_data == 'multiple':
                        print('Multiple results: ', search_data)
                    for k, v in additional_data.items():
                        item_data[k] = v
                    players[search_data] = item_data
                item_data['item_type'] = 'player'
                item_data['chemistry_style'] = item.find_element_by_xpath('.//div/div[1]/div[1]/div[5]').text
                item_data['position'] = item.find_element_by_xpath('.//div/div[1]/div[1]/div[4]/div[2]').text
                if get_price:
                    try:
                        item_data['futbin_price'] = prices[item_data['resource_id']]
                    except KeyError:
                        item_data['futbin_price'] = info.get_price(item_data['resource_id'], obj=obj)
                        prices[item_data['resource_id']] = item_data['futbin_price']
            elif 'staff' in classes:
                item_data['item_type'] = 'staff'
                item_data['staff_type'] = item.find_element_by_xpath('.//div/div[1]/div[1]/div[2]').get_attribute('class').split(' ')[-1]
                item_data['details'] = item.find_element_by_class_name('itemDesc')
            elif 'badge' in classes:
                item_data['item_type'] = 'badge'
                item_data['team_id'] = str(item.find_element_by_class_name('photo').get_attribute('src').split('/')[-1].split('.')[0])
                item_data['team_name'] = remove_accents(Global.fifa_clubs.get(item_data['team_id']))
                item_data['nation'] = str(item.find_element_by_class_name('flag').get_attribute('src').split('/')[-1].split('.')[0])
                item_data['nation_name'] = remove_accents(Global.fifa_nations.get(item_data['nation']))
            elif 'ball' in classes:
                item_data['item_type'] = 'ball'
        elif 'stadium' in classes:
            item_data['item_type'] = 'stadium'
        elif 'kit' in classes:
            item_data['item_type'] = 'kit'
            item_data['team_id'] = str(item.find_element_by_class_name('badge').get_attribute('src').split('/')[-1].split('.')[0])
            item_data['team_name'] = remove_accents(Global.fifa_clubs.get(item_data['team_id'])),
            item_data['nation'] = str(item.find_element_by_class_name('flag').get_attribute('src').split('/')[-1].split('.')[0])
            item_data['nation_name'] = remove_accents(Global.fifa_nations.get(item_data['nation']))
            item_data['details'] = item.find_element_by_class_name('itemDesc').text
        elif 'pack' in classes:
            item_data['item_type'] = 'pack'
        elif 'consumable' in classes:
            if 'Contracts' in item_name:
                item_data['item_type'] = 'contract'
                item_data['bronze'] = item.find_element_by_class_name('bronzeBoost').text.split('+')[-1]
                item_data['silver'] = item.find_element_by_class_name('silverBoost').text.split('+')[-1]
                item_data['gold'] = item.find_element_by_class_name('goldBoost').text.split('+')[-1]
                item_data['contract_type'] = item.find_element_by_xpath('.//div/div[1]/div[1]/div[3]').get_attribute('class').split(' ')[-1]
            elif 'Fitness' in item_name:
                item_data['item_type'] = 'fitness'
            elif 'Coins' in item_name:
                item_data['item_type'] = 'coins'
                item_data['value'] = item_name.split(' ')[0]
            else:
                src = str(item.find_element_by_class_name('photo').get_attribute('src'))
                if 'training' in src:
                    if 'gkattrib' not in src:
                        item_data['item_type'] = 'training'
                    else:
                        item_data['item_type'] = 'gk_training'
                    item_data['details'] = item.find_element_by_class_name('itemDesc').text
                elif 'healing' in src:
                    item_data['item_type'] = 'healing'
                    item_data['details'] = item.find_element_by_class_name('itemDesc').text
                else:
                    multi_log(message='parse_item_list error. '.format(item_name), level='error')
        elif 'chemistryStyle' in classes:
            item_data['item_type'] = 'chem_style'
        else:
            multi_log(message='parse_item_list error. '.format(item_name), level='error')
        if item not in return_data:
            return_data.append(item_data)
    return return_data


def create_futbin_url(obj, filter_dict):
    og_link = 'https://www.futbin.com/18/players?page=1'
    if 'pc' in obj.platform:
        platform = 'pc'
    elif 'xbox' in obj.platform:
        platform = 'xbox'
    else:
        platform = 'ps'
    if 'sort' not in og_link:
        base_url = og_link + '&sort={}_price&order=asc'.format(platform)
    else:
        base_url = og_link
    if filter_dict.get('max_price', None) and 'price=' not in base_url:
        base_url = base_url + '&{}_price=250-{}'.format(platform, filter_dict['max_price'])
    if filter_dict.get('quality', None) and 'version' not in base_url:
        if filter_dict['quality'].lower() == 'special':
            base_url = base_url + '&version=all_specials'
        else:
            base_url = base_url + '&version={}'.format(filter_dict['quality'].lower())
    if filter_dict.get('position', None) and 'position' not in base_url:
        base_url = base_url + '&position={}'.format(filter_dict['position'])
    if filter_dict.get('nation', None) and 'nation' not in base_url:
        for key, name in Global.fifa_nations.items():
            if filter_dict['nation'].lower() == name.lower():
                nation_id = key
                base_url = base_url + '&nation={}'.format(nation_id)
                break
    if filter_dict.get('league', None) and 'league' not in base_url and not filter_dict.get('club', None) and 'club' not in base_url:
        got_league = False
        if remove_accents(filter_dict['league']).lower() == 'meiji yasuda j1 league':
            filter_dict['league'] = 'Meiji Yasuda J1'
        for key, name in Global.fifa_leagues.items():
            if filter_dict['league'].lower() == name.lower():
                league_id = key
                base_url = base_url + '&league={}'.format(league_id)
                got_league = True
                break
        if not got_league:
            from fuzzywuzzy import process
            league = process.extractOne(filter_dict['league'], list(Global.fifa_leagues.values()))[0]
            for key, name in Global.fifa_leagues.items():
                if league.lower() == name.lower():
                    league_id = key
                    base_url = base_url + '&league={}'.format(league_id)
                    break
    if filter_dict.get('club', None) and 'club' not in base_url:
        got_club = False
        for key, name in Global.fifa_clubs.items():
            if filter_dict['club'].lower() == name.lower():
                club_id = key
                base_url = base_url + '&club={}'.format(club_id)
                got_club = True
                break
        if not got_club:
            from fuzzywuzzy import process
            print('Looking for {}'.format(filter_dict['club']))
            club = process.extractOne(filter_dict['club'], list(Global.fifa_clubs.values()))[0]
            print('Got {}'.format(club))
            for key, name in Global.fifa_clubs.items():
                if club.lower() == name.lower():
                    club_id = key
                    base_url = base_url + '&club={}'.format(club_id)
                    break
    return base_url


def parse_futbin_players_table(obj, url, all_results, ignore_untradeable=True, fast=True):
    players = []
    db_players = {}
    try:
        table = obj.__get_xpath__('//*[@id="repTb"]', timeout=Global.large_max)
    except TimeoutException:
        obj.keep_alive(10)
        obj.driver.get(url)
        table = obj.__get_xpath__('//*[@id="repTb"]', timeout=Global.large_max)
    tbody = table.find_element_by_tag_name('tbody')
    for row in tbody.find_elements_by_xpath('.//tr'):
        r_data = row.find_elements_by_xpath('.//td')
        if 'no results' in r_data[0].text.lower():
            if len(all_results) == 0:
                multi_log(message='Table is empty. Did you use the right URL?', level='warn')
            return []
        link = row.find_element_by_class_name('player_name_players_table').get_attribute('href')
        if 'pc' in obj.platform:
            relevant_price = 6
        elif 'xbox' in obj.platform:
            relevant_price = 5
        else:
            relevant_price = 4
        try:
            classes = row.find_element_by_class_name('player_img').get_attribute('class')
            other = row.find_element_by_class_name('players_club_nation')
            club_id = other.find_element_by_xpath('.//a[1]').get_attribute('href').split('=')[-1]
            nation_id = other.find_element_by_xpath('.//a[2]').get_attribute('href').split('=')[-1]
            league_id = other.find_element_by_xpath('.//a[3]').get_attribute('href').split('=')[-1]
            price = int(price_parse(r_data[relevant_price].text))
            asset_id = r_data[0].find_element_by_tag_name('img').get_attribute('src').split('/')[-1].split('.')[0].replace('p', '')
            if int(asset_id) > 300000:
                asset_id = info.get_base_id(asset_id)
            rating = row.find_elements_by_tag_name('td')[1].text
            ignore_quality = ['sbc']
            color, quality = futbin_to_ea_color(classes, return_quality=True)
            if (ignore_untradeable and color not in ignore_quality) or not ignore_untradeable:
                player = {
                    'price': price,
                }
                search_data = (asset_id, rating, color, club_id)
                if db_players.get(search_data, None):
                    player = db_players[search_data]
                    player['price'] = price
                else:
                    futbin_id = str(link.split('/')[-2])
                    if fast:
                        player.update({
                            'position': row.find_element_by_xpath('.//td[3]').text,
                            'quality': quality,
                            'color': color,
                            'nation': str(nation_id),
                            'league': str(league_id),
                            'club': str(club_id),
                            'asset_id': asset_id,
                            'name': r_data[0].find_element_by_xpath('./a').text,
                            'rating': rating,
                        })
                    else:
                        additional_data = database.get_player_info(futbin_id, id_type='futbin', return_all=False)
                        if not additional_data:
                            multi_log(obj, '{} futbin_id not in local database. Attempting to find by other id'.format(search_data))
                            if int(asset_id) > 300000:
                                additional_data = database.get_player_info(asset_id, id_type='resource', return_all=False)
                            else:
                                additional_data = database.get_player_info(asset_id, id_type='base', rating=rating, color=color, club=club_id, return_all=False)
                            if additional_data:
                                database.add_futbin_player_to_db(link)
                                if additional_data != 'multiple':
                                    multi_log(obj, '{} found. Updating with futbin_id'.format(search_data))
                                else:
                                    additional_data = database.get_player_info(futbin_id, id_type='futbin', return_all=False)
                            elif not additional_data:
                                import requests as r
                                from lxml import html
                                page = r.get(link)
                                tree = html.fromstring(page.content)
                                resource_id = tree.xpath('//*[@id="page-info"]')[0].get('data-player-resource')
                                multi_log(obj, '{} not in local database at all. Attempting to add from futbin'.format(search_data))
                                database.add_futbin_player_to_db(link)
                                additional_data = database.get_player_info(resource_id, return_all=False)
                        if additional_data and additional_data != 'multiple':
                            for k, v in additional_data.items():
                                player[k] = v
                            db_players[search_data] = player
                        else:
                            multi_log(obj, 'Unable to find or add {} in/to database'.format(search_data), level='warn')
                players.append(player)
        except IndexError as e:
            print(e)
    return players


def parse_futbin_tables(obj, starting_url, ignore_untradeable=True, fast=True):
    all_results = []
    previous_results = None
    duplicate_count = 0
    while True:
        results = parse_futbin_players_table(obj, starting_url, all_results, ignore_untradeable=ignore_untradeable, fast=fast)
        if previous_results == results:
            break
        else:
            previous_results = results
        for result in results:
            if result not in all_results:
                all_results.append(result)
            else:
                duplicate_count += 1
        if 'page=' in starting_url:
            current_page = int(starting_url.split('?page=')[1].split('&')[0])
            next_page = current_page + 1
            base_url_list = starting_url.replace('?page={}'.format(current_page), '').split('/players')
            next_page_url = base_url_list[0] + '/players?page={}'.format(next_page) + base_url_list[-1]
            starting_url = next_page_url
        else:
            next_page_url = starting_url.split('?')[0] + '?page=2' + starting_url.split('?')[-1]
            starting_url = next_page_url
        # obj.driver.get(next_page_url)
        try:
            obj.__click_xpath__('//*[@id="next"]')
        except (NoSuchElementException, TimeoutException):
            break
        obj.keep_alive(Global.small_max)
        if len(results) == 0 or duplicate_count > 100:
            break
    return all_results


def club_fix(club):
    if remove_accents(club).lower() == 'olympique de marseille':
        club = 'OM'
    elif remove_accents(club).lower() == 'kawasaki frontale':
        club = 'Kawasaki-F'
    elif remove_accents(club).lower() == 'borussia dortmund':
        club = 'Dortmund'
    elif remove_accents(club).lower() == 'borussia mÃ¶nchengladbach' or remove_accents(club).lower() == 'borussia mapnchengladbach':
        club = 'M\'gladbach'
    elif remove_accents(club).lower() == 'tsg 1899 hoffenheim':
        club = 'Hoffenheim'
    elif remove_accents(club).lower() == 'hertha bsc':
        club = 'Berlin'
    elif remove_accents(club).lower() == 'montpellier ha(c)rault sc':
        club = 'Montpellier HSC'
    elif remove_accents(club).lower() == 'paris saint-germain':
        club = 'Paris'
    elif remove_accents(club).lower() == 'orlando city soccer club':
        club = 'Orlando City'
    elif remove_accents(club).lower() == 'as monaco football club sa':
        club = 'AS Monaco'
    elif remove_accents(club).lower() == 'manchester united':
        club = 'Manchester Utd'
    elif remove_accents(club).lower() == 'rb leipzig':
        club = 'Leipzig'
    elif remove_accents(club).lower() == 'galatasaray sk':
        club = 'Galatasaray'
    elif remove_accents(club).lower() == 'borussia monchengladbach':
        club = 'M\'gladbach'
    elif remove_accents(club).lower() == 'besiktas jk':
        club = 'Beşiktaş'
    elif remove_accents(club).lower() == 'fc schalke 04':
        club = 'Schalke'
    return club


def league_fix(league):
    if remove_accents(league).lower() == 'meiji yasuda j1 league':
        league = 'Meiji Yasuda J1'
    return league


def nation_fix(nation):
    if remove_accents(nation).lower() == 'republic of ireland':
        nation = 'Ireland'
    return nation


def futbin_to_ea_color(classes, return_quality=False):
    specials = ['futmas', 'sbc', 'award-winner', 'icon', 'sbc_premium', 'toty', 'otw', 'if', 'halloween', 'purple', 'marquee', 'promo', 'award_winner',
                'europe_motm', 'fut_champions_gold', 'fut_champions_silver', 'fut_mas', 'gotm', 'halloween', 'legend', 'marquee', 'motm',
                'ones_to_watch', 'purple', 'sbc_base', 'sbc_premium', 'totw_gold', 'totw_silver', 'toty', 'motm_eu', 'fut-bd', 'stpatrick']
    classes = [x.lower() for x in classes.split(' ') if x != '']
    color = None
    quality = None
    for s in specials:
        for c in classes:
            if s == c:
                color = s
                break
    if not color:
        for q in ['bronze', 'silver', 'gold']:
            for c in classes:
                if q == c:
                    quality = q
                    if 'non-rare' in classes:
                        color = q
                    else:
                        color = 'rare_' + q
                    break
    if not quality:
        quality = 'special'
    if color == 'otw':
        color = 'ones_to_watch'
    elif color == 'futmas':
        color = 'fut_mas'
    elif color == 'promo':
        color = 'gotm'
    elif color == 'motm_eu':
        color = 'europe_motm'
    elif color == 'fut-bd':
        color = 'fut_birthday'
    elif color == 'icon':
        color = 'legend'
    elif color == 'stpatrick':
        color = 'st_patricks'
    elif color == 'award-winner':
        color = 'award_winner'
    if 'if' in classes:
        if 'gold' in classes:
            color = 'totw_gold'
        elif 'silver' in classes:
            color = 'totw_silver'
    if not return_quality:
        return color
    else:
        return color, quality