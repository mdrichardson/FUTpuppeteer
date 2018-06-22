from FUTpuppeteer import info
from FUTpuppeteer.misc import multi_log, Global
from . import retry_decorator, common_hunt, common_wait_to_expire


@retry_decorator
def futbin_market(obj):
    obj.current_strategy = 'Futbin Market'
    temp_settings = obj.strategy_settings['futbin_market']
    down_markets = temp_settings['down_markets']
    up_markets = temp_settings['up_markets']
    min_price = temp_settings['min_price']
    max_price = temp_settings['max_price']
    remove_keys = ['down_markets', 'up_markets', 'min_price', 'max_price']
    settings = {k: v for k, v in temp_settings.items() if k not in remove_keys}
    total_bids = 0

    def buy_and_search(target_player, group, total_b):
        bids = 0
        futbin_price = info.get_price(target_player['asset_id'], obj)
        if target_player['change'] >= 10 and futbin_price > 0:
            if (group == 'down' and obj.credits > target_player['futbin_price'] and target_player['futbin_price'] * 1.2 >= futbin_price) \
                    or (group == 'up' and obj.credits > target_player['futbin_price']):
                hunt_criteria = {
                    'search_type': 'Players',
                    'player': target_player['asset_id'],
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
                if group == 'down':
                    max_bin = futbin_price * (1 - (target_player['change'] / 200))
                else:
                    max_bin = futbin_price * (1 - (target_player['change'] / 300))
                bids += common_hunt(obj, hunt_criteria=hunt_criteria, name=info.get_player_info(hunt_criteria['player'], False)['name'],
                                    strategy='futbin_market_{}'.format(group), price=max_bin, **settings)
        return bids

    multi_log(obj, 'Futbin Market...', level='title')
    # Go through player lists
    have_markets = []
    # Snipe down players and sell just below previous BIN
    for down_market in down_markets:
        multi_log(obj, 'Getting information for {} market...'.format(down_market))
        market_data = info.get_futbin_market(obj, down_market, min_price, max_price)
        have_markets.append({'name': down_market, 'market_data': market_data})
        if obj.url not in obj.driver.current_url:
            obj.driver.get(obj.url)
            obj.location = 'home'
            obj.rate_limit()
        obj.__get_xpath__('//*[@id="user-coin"]/div/span[2]', timeout=Global.large_max)
        if 40 < market_data['momentum'] <= 60:
            for player in market_data['down_players']:
                total_bids += buy_and_search(player, 'down', total_bids)
                if total_bids > 0:
                    common_wait_to_expire(obj=obj, strategy='futbin_market_down')
        else:
            multi_log(obj, message='{} market momentum of {} is too poor for down-hunting. Skipping...'.format(down_market, market_data['momentum']))
    # Snipe up players below previous BIN and sell just below current BIN
    have_market_names = []
    for have_market in have_markets:
        have_market_names.append(have_market['name'])
    for up_market in up_markets:
        if up_market in have_market_names:
            for have_market in have_markets:
                if have_market['name'] == up_market:
                    market_data = have_market['market_data']
                    break
        else:
            market_data = info.get_futbin_market(obj, up_market, min_price, max_price)
        if obj.url not in obj.driver.current_url:
            obj.driver.get(obj.url)
            obj.location = 'home'
            obj.rate_limit()
        obj.__get_xpath__('//*[@id="user-coin"]/div/span[2]', timeout=Global.large_max)
        if 40 < market_data['momentum'] <= 75:
            for player in market_data['up_players']:
                num_bids = buy_and_search(player, 'up', total_bids)
                if num_bids == 'limit':
                    common_wait_to_expire(obj=obj, strategy='futbin_market_up')
                else:
                    total_bids += num_bids
            if total_bids > 0:
                common_wait_to_expire(obj=obj, strategy='futbin_market_up')
        else:
            multi_log(obj, message='{} market momentum of {} is too poor for up-hunting. Skipping...'.format(up_market, market_data['momentum']))