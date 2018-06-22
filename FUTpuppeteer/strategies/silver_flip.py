from FUTpuppeteer import info
from FUTpuppeteer.misc import multi_log, Global
from . import retry_decorator, common_hunt, common_fight, common_wait_to_expire
from selenium.common.exceptions import ElementNotVisibleException, TimeoutException, NoSuchElementException
from ruamel.yaml import YAML
from datetime import datetime, timedelta

yaml = YAML()
yaml.explicit_start = True
yaml.indent(mapping=4)
yaml.preserve_quotes = True
need_relisting = False


@retry_decorator
def silver_flip(obj):
    def check_transfer_targets():
        if obj.location != 'transfer_targets':
            obj.go_to('transfer_targets')
        multi_log(obj, 'Waiting on last bid to expire')
        while True:
            max_expire = 0
            watched_items = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Watched Items')]", gp_type='xpath', get_price=False)
            if len(watched_items) == 0:
                break
            for item in watched_items:
                if item['time_left'] > max_expire:
                    max_expire = item['time_left']
            obj.keep_alive(max_expire + 5)
        expired_bids = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Expired Items')]", gp_type='xpath', get_price=False)
        expired = {}
        for expired_bid in expired_bids:
            if expired_bid['asset_id'] not in list(expired.keys()):
                expired[expired_bid['asset_id']] = {
                    'bid_amounts': 0,
                    'num_results': 0
                }
            expired[expired_bid['asset_id']]['bid_amounts'] += expired_bid['current_bid']
            expired[expired_bid['asset_id']]['num_results'] += 1
        return_players = []
        for asset, data in expired.items():
            futbin_price = info.get_price(asset)
            tier = info.get_tier(futbin_price)
            rounding = Global.rounding_tiers[tier]
            average_bid = info.round_down(data['bid_amounts'] / data['num_results'], rounding)
            coins_from_sale = futbin_price * 0.95
            potential_profit = coins_from_sale - average_bid
            if settings['use_buy_percent'] and potential_profit >= coins_from_sale - (futbin_price * obj.bin_settings['buy_percent']):
                return_players.append({'asset_id': asset, 'name': info.get_player_info(asset, False)['name'], 'bid': average_bid, 'futbin': futbin_price})
            elif potential_profit >= settings['min_profit']:
                return_players.append({'asset_id': asset, 'name': info.get_player_info(asset, False)['name'], 'bid': average_bid, 'futbin': futbin_price})
        for player_data in return_players:
            name = info.get_player_info(player_data['asset_id'], False)['name']
            multi_log(obj, '{}\'s Average Bid: {}  |  Futbin price: {}'.format(name, player_data['bid'], player_data['futbin']))
        obj.clear_expired()
        return return_players

    obj.current_strategy = 'Silver Flip'
    temp_settings = obj.strategy_settings['silver_flip']
    min_price = temp_settings['min_price']
    max_price = temp_settings['max_price']
    max_results = temp_settings['max_results']
    market_monitor = temp_settings['market_monitor']
    players = temp_settings['players']
    remove_keys = ['max_iterations', 'min_price', 'max_price', 'market_monitor', 'players', 'max_results']
    settings = {k: v for k, v in temp_settings.items() if k not in remove_keys}
    multi_log(obj, 'Silver Flipping...', level='title')
    # Get market information
    bid_players = []
    if len(players) == 0 or market_monitor['refresh']:
        obj.strategy_settings['silver_flip']['players'] = []
        for league in market_monitor['leagues']:
            iterations = 0
            multi_log(obj, 'Getting market data for {}.'.format(league))
            while iterations < market_monitor['iterations']:
                full = False
                bid_results = obj.search(search_type='Players', quality='Silver', league=league, min_buy=min_price, max_buy=max_price)
                iterations += 1
                for bid_result in bid_results:
                    if bid_result['time_left'] <= market_monitor['max_time_left'] and bid_result['current_bid'] != bid_result['start_price']:
                        bid_result['element'].click()
                        obj.keep_alive(Global.micro_min)
                        err = obj.__check_for_errors__()
                        if err == 'limit':
                            full = True
                            break
                        side_panel = obj.__get_class__('DetailView', as_list=False)
                        try:
                            side_panel.find_element_by_class_name('watch').click()
                            err = obj.__check_for_errors__()
                            if err == 'limit':
                                full = True
                                break
                        except (ElementNotVisibleException, TimeoutException, NoSuchElementException):
                            pass
                while not full:
                    try:
                        nav_bar = obj.__get_class__('pagingContainer', as_list=False)
                    except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                        nav_bar = obj.__get_class__('mainHeader', as_list=False)
                    try:
                        next_btn = nav_bar.find_element_by_class_name('next')
                        obj.__click_element__(next_btn)
                        bid_results = obj.__get_items__()
                        least_time_left = 99999999
                        for bid_result in bid_results:
                            if bid_result['time_left'] <= market_monitor['max_time_left'] and bid_result['current_bid'] != bid_result['start_price']:
                                bid_result['element'].click()
                                obj.keep_alive(Global.micro_max)
                                err = obj.__check_for_errors__()
                                if err == 'limit':
                                    full = True
                                    break
                                side_panel = obj.__get_class__('DetailView', as_list=False)
                                try:
                                    side_panel.find_element_by_class_name('watch').click()
                                    err = obj.__check_for_errors__()
                                    if err == 'limit':
                                        full = True
                                        break
                                except (ElementNotVisibleException, TimeoutException, NoSuchElementException):
                                    pass
                            if bid_result['time_left'] < least_time_left:
                                least_time_left = bid_result['time_left']
                    except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                        break
                    if full or least_time_left > market_monitor['max_time_left']:
                        break
                temp_players = check_transfer_targets()
                for temp_player in temp_players:
                    if temp_players not in players:
                        bid_players.append(temp_player)
    else:
        with open(obj.config_file) as config:
            old_config = yaml.load(config)
            bid_players = old_config['strategy_settings']['silver_flip']['players']
    # Get BIN info if futbin update is too late
    for bid_player in bid_players:
        max_bin, update = info.get_price(bid_player['asset_id'], obj, return_updated=True)
        tier = info.get_tier(max_bin)
        rounding = Global.rounding_tiers[tier]
        now = datetime.now()
        last_update = bid_player.get('last_update', None)
        if last_update:
            difference = (now - last_update).seconds
        else:
            difference = (now - now - timedelta(hours=99)).seconds
        if update > settings['max_futbin_update'] and update < difference:
            multi_log(obj, 'Price data for {} out of date. Getting current price...'.format(info.get_player_info(bid_player['asset_id'])['name']))
            num_results = 0
            total_bins = 0
            bin_with_results = []
            while num_results < 3:
                bin_results = obj.search(search_type='Players', player=bid_player['asset_id'], max_bin=max_bin)
                if len(bin_results) > max_results:
                    if total_bins == 0:
                        min_bin = 999999
                        for bin_result in bin_results:
                            if bin_result['buy_now_price'] < min_bin:
                                min_bin = bin_result['buy_now_price'] - Global.rounding_tiers[tier]
                            max_bin = min_bin
                        continue
                    else:
                        for bin_result in bin_results:
                            if bin_result['buy_now_price'] not in bin_with_results:
                                total_bins += bin_result['buy_now_price']
                                num_results += 1
                        if len(bin_results) > 0:
                            bin_with_results.append(max_bin)
                elif len(bin_results) == 0:
                    max_bin += rounding * 2
                else:
                    for bin_result in bin_results:
                        if bin_result['buy_now_price'] not in bin_with_results:
                            total_bins += bin_result['buy_now_price']
                            num_results += 1
                            max_bin += rounding
                    if len(bin_results) > 0:
                        bin_with_results.append(max_bin)
            minimum_bin = info.round_down(total_bins / num_results, rounding)
            bid_player['minimum_bin'] = minimum_bin
            bid_player['last_update'] = datetime.now()
        else:
           bid_player['minimum_bin'] = max_bin
        coins_from_sale = bid_player['minimum_bin'] * 0.95
        potential_profit = coins_from_sale - bid_player['bid']
        current_players = []
        if bid_player['asset_id'] not in current_players:
            current_players.append(bid_player['asset_id'])
            if settings['use_buy_percent']:
                if potential_profit >= coins_from_sale - (bid_player['minimum_bin'] * obj.bin_settings['buy_percent']):
                    players.append(bid_player)
            else:
                if potential_profit >= settings['min_profit']:
                    players.append(bid_player)
    with open(obj.config_file) as config:
        new_config = yaml.load(config)
        new_config['strategy_settings']['silver_flip']['players'] = players
    with open(obj.config_file, 'w') as update:
        yaml.dump(new_config, update)
    total_bids = 0
    # Search and bid
    for player in players:
        futbin_price = player['minimum_bin']
        if futbin_price > 0:
            if obj.get_credits() > futbin_price and min_price <= futbin_price <= max_price:
                hunt_criteria = {
                    'search_type': 'Players',
                    'player': player['asset_id'],
                    'quality': None,
                    'position': None,
                    'chem_style': None,
                    'nation': None,
                    'league': None,
                    'club': None,
                    'min_bin': None,
                    'include': None,
                    'exclude': None,
                }
                num_bids = common_hunt(obj=obj, name=info.get_player_info(hunt_criteria['player'], False)['name'], price=futbin_price, hunt_criteria=hunt_criteria,
                                       strategy='silver_flip', **settings)
                if num_bids == 'limit':
                    common_wait_to_expire(obj=obj, strategy='hunt')
                else:
                    total_bids += num_bids

    if total_bids > 0:
        if not settings['use_max_buy']:
            common_fight(obj=obj, strategy='silver_flip', settings=settings)
        else:
            common_wait_to_expire(obj=obj, strategy='silver_flip')
