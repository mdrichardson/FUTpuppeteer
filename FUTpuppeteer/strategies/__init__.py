from FUTpuppeteer import info, database
from FUTpuppeteer.misc import multi_log, Global
from FUTpuppeteer.exceptions import Retry
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotVisibleException, StaleElementReferenceException, WebDriverException
from operator import itemgetter
from datetime import datetime
from random import uniform as rand


def retry_decorator(func):
    def func_wrapper(*args, **kwargs):
        while True:
            try:
                x = func(*args, **kwargs)
                break
            except Retry:
                pass
        return x
    return func_wrapper


step1_notified = False
step2_notified = False
normal_notified = False


@retry_decorator
def dynamic_profit(obj):
    global step1_notified
    global step2_notified
    global normal_notified
    adjustment = 1
    if obj.bin_settings['dynamic_profit']:
        if obj.bin_settings['dynamic_profit_after1'] <= obj.current_tradepile_size < obj.bin_settings['dynamic_profit_after2']:
            adjustment -= obj.bin_settings['dynamic_profit_steps'] * 2
            normal_notified = False
            if not step2_notified:
                multi_log(obj, 'Dynamic profit enabled. Profit buy_percent increased by {}%'.format(int(obj.bin_settings['dynamic_profit_steps'] * 200)), level='header')
                step2_notified = True
        elif obj.current_tradepile_size > obj.bin_settings['dynamic_profit_after2']:
            adjustment -= obj.bin_settings['dynamic_profit_steps']
            normal_notified = False
            if not step1_notified:
                multi_log(obj, 'Dynamic profit enabled. Profit buy_percent increased by {}%'.format(int(obj.bin_settings['dynamic_profit_steps'] * 100)), level='header')
                step1_notified = True
        else:
            if step1_notified or step2_notified:
                if normal_notified:
                    multi_log(obj, 'Profit buy_percent returned to normal', level='header')
                    step1_notified = False
                    step2_notified = False
    return adjustment


@retry_decorator
def housekeeping(obj):
    multi_log(obj, 'Housekeeping...', level='header')
    obj.check_unassigned()
    if obj.location != 'transfers':
        obj.go_to('transfers')
    obj.clear_sold()
    obj.relist_all()
    obj.clear_expired()
    obj.sell_transfer_targets_at_market()
    hour, day = database.get_profit(obj)
    multi_log(obj, 'Profit in last hour: {}  |  Profit in last 24 hours: {}  |  Credits: {}'.format(hour, day, obj.credits))  # TODO: Remove once GUI is implemented


@retry_decorator
def check_sleep(obj):
    sleep_interval = obj.settings['sleep_after_running_for_x_minutes'] * 60
    now = datetime.now()
    if (now - obj.last_sleep).seconds >= sleep_interval:
        sleep_average = obj.settings['sleep_average']
        sleep_spread = obj.settings['sleep_spread']
        sleep_time = rand(sleep_average - sleep_spread, sleep_average + sleep_spread) * 60
        multi_log(obj, 'Exceeded maximum active time.')
        obj.keep_alive(sleep_time)
        obj.clear_sold()
        obj.relist_all()
        obj.last_sleep = datetime.now()
    else:
        night_mode(obj)


def night_mode(obj):
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.explicit_start = True
    yaml.indent(mapping=4)
    yaml.preserve_quotes = True
    settings = obj.settings['night_mode']
    now = datetime.now()
    if settings['enabled'] and (now - settings['last_sleep']).seconds * 60 * 60 > 12:
        start = datetime(now.year, now.month, now.day, settings['start_hour'], 0, 0, 0)
        if now.hour >= settings['end_hour']:
            try:
                end = datetime(now.year, now.month, now.day + 1, settings['end_hour'], 0, 0, 0)
            except ValueError:
                end = datetime(now.year, now.month + 1, 1, settings['end_hour'], 0, 0, 0)
        else:
            end = datetime(now.year, now.month, now.day, settings['end_hour'], 0, 0, 0)
        if start <= now < end:
            with open(obj.config_file) as config:
                new_config = yaml.load(config)
                new_config['settings']['night_mode']['last_sleep'] = datetime.now()
                new_config['settings']['night_mode']['need_relist'] = True
            with open(obj.config_file, 'w') as update:
                yaml.dump(new_config, update)
            relist = settings['relist_for']
            active_transfers = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Active Transfers')]", gp_type='xpath',
                                                 get_price=False)
            if len(active_transfers) > 0:
                longest_time_left = active_transfers[-1]['time_left'] + 10
                multi_log(obj, '[Night Mode] Waiting until current transfers expire')
                obj.keep_alive(longest_time_left)  # Ensure all transfers are expired
            multi_log(obj, '[Night Mode] Relisting all transfers for {}'.format(relist))
            obj.relist_individually(at_market=False, duration=relist)
            sleep_time = (end - datetime.now()).seconds
            multi_log(obj, '[Night Mode] Sleeping until'.format(settings['end_hour']))
            obj.keep_alive(sleep_time)
            if settings['wait_for_enter']:
                obj.wait_for_enter()


# noinspection PyUnboundLocalVariable
@retry_decorator
def common_snipe(obj, name, snipe_criteria, strategy, price=0, max_item_buys=10, max_tries=10, max_futbin_update=60*60*24*3, max_results=5,
                 use_buy_percent=False, min_profit=300, sell_price=None, max_prp=None, sell_acquired_if_full=True, prices_dict=None):
    """
    snipe_criteria = {
        'search_type': 'Players',
        'player': player_id,
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
    """
    def sell_players(o, b):
        if prices_dict:
            o.go_to('unassigned')
        finished_items = o.__get_items__(get_price=True)
        for item in finished_items:
            if sell_acquired_if_full:
                if strategy != 'acquire':
                    # Sell bought players
                    if b > 0:
                        if snipe_criteria['player']:
                            if item['resource_id'] == str(snipe_criteria['player']) and item['bid_status'] == 'won':
                                if not sell_price:
                                    sell_tier = info.get_tier(item['futbin_price'])
                                    bin_price = info.round_down(item['futbin_price'] * o.bin_settings[sell_tier]['sell_percent'], Global.rounding_tiers[tier])
                                else:
                                    bin_price = sell_price
                                player_tier = info.get_tier(bin_price)
                                start_price = bin_price - o.bin_settings[player_tier]['spread']
                                sell_result = o.sell(item, start_price, bin_price)
                                if sell_result == 'full':
                                    common_deal_with_full_transfer_list(o, strategy)
                        elif (not include or item['resource_id'] in include) and item['bid_status'] == 'won':
                            player_tier = info.get_tier(item['futbin_price'])
                            if not sell_price:
                                bin_price = info.round_down(item['futbin_price'] * o.bin_settings[player_tier]['sell_percent'], Global.rounding_tiers[tier])
                            else:
                                bin_price = sell_price
                            start_price = bin_price - o.bin_settings[player_tier]['spread']
                            sell_result = o.sell(item, start_price, bin_price)
                            if sell_result == 'full':
                                common_deal_with_full_transfer_list(o, strategy)
                else:
                    if item['bid_status'] == 'won':
                        send_result = o.send_to_club(item=item, strategy='acquire')
                        if send_result == 'owned':
                            futbin_price = info.get_price(item['resource_id'], o)
                            player_tier = info.get_tier(futbin_price)
                            bin_price = info.round_down(item['futbin_price'] * o.bin_settings[player_tier]['sell_percent'], Global.rounding_tiers[tier])
                            spread = o.bin_settings[player_tier]['spread']
                            sell_result = o.sell(item=item, start_price=bin_price - spread, bin_price=bin_price)
                            if sell_result == 'full':
                                common_deal_with_full_transfer_list(o, strategy)
                        o.keep_alive(Global.micro_min)
                        return bought
            elif snipe_criteria['player'] and item['resource_id'] == str(snipe_criteria['player']) and item['bid_status'] == 'won':
                obj.send_to_transfer_list(item)
                o.keep_alive(Global.micro_max)

    def buy_results(search_results, bought, let_items_refresh, price, max_bin):
        if 0 < len(search_results) <= max_results:
            if len(search_results) > 0 and strategy == 'acquire':
                sorted_results = sorted(search_results, key=itemgetter('buy_now_price'))
                search_results = sorted_results
            else:
                sorted_results = search_results[::-1]
                search_results = sorted_results
            for result in search_results:
                if prices_dict:
                    try:
                        price = prices_dict[result['resource_id']]
                    except KeyError:
                        break
                    if not use_buy_percent:
                        max_bin = info.round_down((price * 0.95 * dynamic_profit(obj) * obj.bin_settings[tier]['sell_percent']) - min_profit,
                                                  Global.rounding_tiers[tier])
                    else:
                        max_bin = info.round_down((price * profit_buy_percent * dynamic_profit(obj)), Global.rounding_tiers[tier])
                if bought < max_item_buys and result['buy_now_price'] <= max_bin and len(search_results) <= max_results \
                        and (snipe_criteria['search_type'].lower() != 'players' or
                             ((not include and snipe_criteria['player'] == result['resource_id']) or (include and result['resource_id'] in include)) or
                             (not include and not snipe_criteria['player'])):
                    # Buy
                    try:
                        if not sell_price:
                            result_bought = obj.buy_now(result, strategy=strategy, expected_profit=((price * 0.95 * obj.bin_settings[tier]['sell_percent'])
                                                                                                    - result['buy_now_price']))
                        else:
                            result_bought = obj.buy_now(result, strategy=strategy, expected_profit=((sell_price * 0.95 * obj.bin_settings[tier]['sell_percent'])
                                                                                                    - result['buy_now_price']))
                        if result_bought:
                            bought += 1
                            let_items_refresh = obj.settings['pause_after_successful_snipe']
                            if bought % 5 == 0:
                                sell_players(obj, bought)
                        else:
                            if let_items_refresh == 0:
                                let_items_refresh = obj.settings['pause_after_unsuccessful_snipe']
                            multi_log(obj, '[{}]: Got out-sniped for: {}'.format(strategy, result['item_name']), level='warn')
                    except Exception as e:
                        multi_log(obj, '[{}]: Snipe BUY error: {}'.format(strategy, e), level='error')
                        continue
                else:
                    multi_log(obj, 'SNIPE PRICING ERROR: STRATEGY: {} | bought: {} | max: {} | r[bnp]: {} | max: {} | len(res): {} |\
                                   crit[type]: {} | player: {} | result: {}'.format(strategy, bought, max_item_buys, result['buy_now_price'], max_bin,
                                                                                    len(search_results),
                                                                                    snipe_criteria['search_type'], snipe_criteria['player'],
                                                                                    result['resource_id']), level='debug')
        return bought, let_items_refresh


    check_sleep(obj)
    include = snipe_criteria.get('include', [])
    if not include:
        include = []
    if (snipe_criteria['player'] and int(snipe_criteria['player']) <= 300000) or (snipe_criteria['quality'] and snipe_criteria['quality'].lower() == 'special'):
        if include:
            special_ids = {}
            for i in include:
                add_ids = info.get_special_ids(i)
                for k, v in add_ids.items():
                    special_ids[k] = v
        elif snipe_criteria['player']:
            special_ids = info.get_special_ids(snipe_criteria['player'])
        for s in list(special_ids.values()):
            include.append(s)
    bought = 0
    if not prices_dict:
        if snipe_criteria['player'] and price == 0:
            price_data = info.get_price(snipe_criteria['player'], obj=obj, return_updated=True, return_prp=True)
            if price_data == 0:
                return 0
            price = price_data[0]
            updated = price_data[1]
            prp = price_data[2]
        else:
            # TODO: Update this when implementing non-player searches
            prp = None
            updated = None
    else:
        if not price:
            price = max(list(prices_dict.values()))
        updated = None
        prp = None
        max_results = 9999999
    if obj.get_credits() > price and (not updated or updated <= max_futbin_update) and (not max_prp or prp <= max_prp):
        tier = info.get_tier(price)
        profit_buy_percent = obj.bin_settings[tier]['buy_percent']
        if strategy != 'acquire' and strategy != 'price_fix':
            if not use_buy_percent:
                max_bin = info.round_down((price * 0.95 * dynamic_profit(obj) * obj.bin_settings[tier]['sell_percent']) - min_profit, Global.rounding_tiers[tier])
            else:
                max_bin = info.round_down((price * profit_buy_percent * dynamic_profit(obj)), Global.rounding_tiers[tier])
        else:
            max_bin = price
        multi_log(obj, '[{}]: Sniping for {} at {}.'.format(strategy.title(), name, max_bin))
        i = max_tries
        reset = True
        while i > 0:
            let_items_refresh = 0
            if i == max_tries:
                search_results = obj.search(max_bin=max_bin, reset=reset, **snipe_criteria)
                reset = False
            elif i == 1:
                search_results = obj.search(max_bin=max_bin, **snipe_criteria)
            else:
                search_results = obj.search(max_bin=max_bin, reset=reset, **snipe_criteria)
                reset = False
            if not prices_dict:
                bought, let_items_refresh = buy_results(search_results, bought, let_items_refresh, price, max_bin)
            else:
                while True:
                    try:
                        nav_bar = obj.__get_class__('pagingContainer', as_list=False)
                    except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                        nav_bar = obj.__get_class__('mainHeader', as_list=False)
                    try:
                        next_btn = nav_bar.find_element_by_class_name('next')
                        obj.__click_element__(next_btn)
                        obj.keep_alive(Global.micro_min)
                    except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                        break
                search_results = obj.__get_items__(get_price=False)
                bought, let_items_refresh = buy_results(search_results, bought, let_items_refresh, price, max_bin)
                while search_results[1]['time_left'] > 58 * 60:
                    try:
                        nav_bar = obj.__get_class__('pagingContainer', as_list=False)
                    except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                        nav_bar = obj.__get_class__('mainHeader', as_list=False)
                    try:
                        prev_btn = nav_bar.find_element_by_class_name('prev')
                        obj.__click_element__(prev_btn)
                        obj.keep_alive(Global.micro_min)
                    except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                        break
                    search_results = obj.__get_items__(get_price=False)
                    bought, let_items_refresh = buy_results(search_results, bought, let_items_refresh, price, max_bin)
            i -= 1
            if len(search_results) > max_results:
                multi_log(obj, 'Too many results returned. Max BIN is probably set too high')
                return 'too many'
            elif len(search_results) == 0 and i == 0:
                multi_log(obj, 'No good deals found', level='yellow')
            if bought > 0:
                sell_players(obj, bought)
            if bought >= max_item_buys:
                return bought
            if let_items_refresh > 0:
                multi_log(obj, 'Pausing to ensure we don\'t try bidding on the same items', level='debug')
                obj.keep_alive(let_items_refresh)  # Making sure server refreshes results so we don't try buying it again. Can throw an error otherwise
                reset = True
    print(' ')
    return bought


@retry_decorator
def common_hunt(obj, name, hunt_criteria, strategy, price=0, max_item_bids=10, max_futbin_update=259200, min_time_left=30, max_time_left=420,
                use_buy_percent=True, min_profit=250, fight=False, use_max_buy=True, max_prp=None, sell_acquired_if_full=True, prices_dict=None):
    """
    hunt_criteria = {
        'search_type': 'Players',
        'player': player_id,
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
    """
    def bid_on_results(results, num_bids, max_buy):
        if len(results) > 0:
            to_bid = []
            for r in results:
                if min_time_left <= r['time_left'] <= max_time_left and (r['current_bid'] + Global.rounding_tiers[tier] <= max_buy or
                                                                           (r['current_bid'] == r['start_price'] and r['start_price'] <= max_buy)) and \
                        (hunt_criteria['search_type'].lower() != 'players' or ((not include and hunt_criteria['player'] == r['resource_id'])
                                                                               or (r['resource_id'] in include))):
                        to_bid.append(r)
            if len(to_bid) == 0:
                multi_log(obj, 'Nothing worth bidding on', level='yellow')
            else:
                if use_max_buy:
                    sorted_bids = sorted(to_bid, key=itemgetter('time_left'))
                else:
                    sorted_bids = sorted(to_bid, key=itemgetter('current_bid'))
                for item in sorted_bids:
                    try:
                        futbin_price, updated = info.get_price(item['resource_id'], return_updated=True)
                        if updated > max_futbin_update:
                            continue
                        result_tier = info.get_tier(futbin_price)
                        result_buy_percent = obj.bin_settings[result_tier]['buy_percent']
                        if strategy != 'acquire' and strategy != 'price_fix':
                            if not use_buy_percent:
                                max_buy = info.round_down((futbin_price * 0.95 * dynamic_profit(obj) * obj.bin_settings[result_tier]['sell_percent']) - min_profit,
                                                          Global.rounding_tiers[result_tier])
                            else:
                                max_buy = info.round_down((futbin_price * result_buy_percent * dynamic_profit(obj)), Global.rounding_tiers[result_tier])
                    except (KeyError, TypeError):
                        continue
                    if num_bids < max_item_bids:
                        if use_max_buy:
                            my_bid = max_buy
                        elif strategy == 'acquire' and not use_max_buy:
                            my_bid = max_buy - (2 * obj.bin_settings[result_tier]['spread'])
                        else:
                            my_bid = min(max_buy, item['current_bid'] + Global.rounding_tiers[result_tier])
                        if item['current_bid'] + Global.rounding_tiers[result_tier] <= my_bid or (item['current_bid'] == item['start_price']
                                                                                           and item['current_bid'] <= my_bid):
                            try:
                                bid_result = obj.bid(item, my_bid)
                                if bid_result == 'limit':
                                    return 'limit'
                                elif bid_result:
                                    num_bids += 1
                                    if num_bids >= max_item_bids:
                                        break
                            except StaleElementReferenceException:
                                pass
                            except Exception as e:
                                multi_log(obj, '[{}]: Hunt BID error: {}'.format(strategy, e), level='error')
                                continue
                        else:
                            multi_log(obj, 'HUNT PRICING ERROR: STRATEGY: {} | r[bnp]: {} | max: {} | len(res): {} |\
                                           crit[type]: {} | player: {} | result: {}'.format(strategy, item['buy_now_price'], my_bid, len(search_results),
                                                                                            hunt_criteria['search_type'], hunt_criteria['player'],
                                                                                            item['resource_id']), level='debug')
        return num_bids

    check_sleep(obj)
    include = hunt_criteria.get('include', [])
    if not include:
        include = []
    if (hunt_criteria.get('player', False) and int(hunt_criteria['player']) <= 300000) and (hunt_criteria['quality'] and hunt_criteria['quality'].lower() == 'special'):
        special_ids = info.get_special_ids(hunt_criteria['player'])
        for s in list(special_ids.values()):
            if int(s) >= 300000:
                include.append(s)
        include.append(info.get_base_id(hunt_criteria['player']))
        include.append(hunt_criteria.get('player', None))
    else:
        bids = 0
    if hunt_criteria.get('player', False) and price == 0:
        price_data = info.get_price(hunt_criteria['player'], obj=obj, return_updated=True, return_prp=True)
        if price_data == 0:
            return 0
        price = price_data[0]
        updated = price_data[1]
        prp = price_data[2]
    else:
        updated = None
        prp = None
    if obj.get_credits() > price and (not updated or updated <= max_futbin_update) and (not max_prp or prp <= max_prp):
        tier = info.get_tier(price)
        profit_buy_percent = obj.bin_settings[tier]['buy_percent']
        if hunt_criteria.get('max_buy', None):
            price = hunt_criteria['max_buy']
            hunt_criteria = {k: v for k, v in hunt_criteria.items() if k != 'max_buy'}
        else:
            price = info.round_down(price, Global.rounding_tiers[tier])
        if strategy != 'acquire' and strategy != 'price_fix' and 'consumable' not in strategy:
            if not use_buy_percent:
                max_buy = info.round_down((price * 0.95 * dynamic_profit(obj) * obj.bin_settings[tier]['sell_percent']) - min_profit, Global.rounding_tiers[tier])
            else:
                max_buy = info.round_down((price * profit_buy_percent * dynamic_profit(obj)), Global.rounding_tiers[tier])
        else:
            max_buy = price
        multi_log(obj, '[{}]: Hunting for {} at {}.'.format(strategy.title(), name, max_buy))
        longest_time_left = 0
        hunt_criteria = {k: v for k, v in hunt_criteria.items() if k != 'max_buy'}
        search_results = obj.search(max_buy=max_buy, **hunt_criteria)
        while longest_time_left < min_time_left:
            if len(search_results) == 0:
                multi_log(obj, 'Nothing worth bidding on', level='yellow')
                break
            else:
                longest_time_left = search_results[-1]['time_left']
                if longest_time_left < min_time_left:
                    try:
                        nav_bar = obj.__get_class__('pagingContainer', as_list=False)
                    except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                        nav_bar = obj.__get_class__('mainHeader', as_list=False)
                    try:
                        next_btn = nav_bar.find_element_by_class_name('next')
                        obj.__click_element__(next_btn)
                        obj.keep_alive(Global.micro_max)
                        search_results = obj.__get_items__(get_price=True)
                    except (ElementNotVisibleException, NoSuchElementException, TimeoutException, StaleElementReferenceException):
                        break
                else:
                    break
        bids = bid_on_results(search_results, bids, max_buy)
        if bids == 'limit':
            return 'limit'
        elif type(bids) is str:
            return bids
        while bids < max_item_bids and longest_time_left <= max_time_left:
            try:
                nav_bar = obj.__get_class__('pagingContainer', as_list=False)
            except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                nav_bar = obj.__get_class__('mainHeader', as_list=False)
            try:
                next_btn = nav_bar.find_element_by_class_name('next')
                errors = obj.__check_for_errors__()
                if errors == 'limit':
                    return 'limit'
                obj.__click_element__(next_btn)
                obj.keep_alive(Global.micro_max)
                search_results = obj.__get_items__(get_price=True)
                least_time_left = search_results[0]['time_left']
                longest_time_left = search_results[-1]['time_left']
                if least_time_left > max_time_left:
                    break
                amt_bids = bid_on_results(search_results, bids, max_buy)
                if amt_bids == 'limit':
                    return 'limit'
                else:
                    try:
                        bids += amt_bids
                    except TypeError:
                        pass
                if longest_time_left > max_time_left:
                    break
            except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                break

    print(' ')
    if fight:
        common_fight(obj, strategy, use_buy_percent, min_profit)
    return bids


@retry_decorator
def common_fight(obj, strategy, use_buy_percent=None, min_profit=100):
    def get_bids(price_to_get):
        bids = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Active Bids')]", gp_type='xpath', get_price=price_to_get)
        to_fight = []
        for b in bids:
            if not b['expired'] and b['time_left'] > 5:
                to_fight.append(b)
        return to_fight
    
    multi_log(obj, 'Fighting for bids...', level='header')
    obj.go_to('transfer_targets')
    fight_bids = get_bids(True)
    prices = {}
    for bid in fight_bids:
        prices[bid['resource_id']] = info.get_price(bid['resource_id'], obj, False)
    min_expire = 9999999
    while len(fight_bids) > 0:
        fight_bids = get_bids(False)
        for bid in fight_bids[:]:
            if bid['time_left'] < min_expire:
                min_expire = bid['time_left']
            if not bid['expired'] and bid['bid_status'] == 'outbid' and 3 < bid['time_left'] <= 60:
                tier = info.get_tier(bid['current_bid'])
                profit_buy_percent = obj.bin_settings[tier]['buy_percent']
                max_bin = prices[bid['resource_id']]
                if strategy != 'acquire':
                    if not use_buy_percent:
                        max_buy = info.round_down((max_bin * 0.95 * dynamic_profit(obj) - min_profit * obj.bin_settings[tier]['sell_percent']),
                                                  Global.rounding_tiers[tier])
                    else:
                        max_buy = info.round_down((max_bin * profit_buy_percent * dynamic_profit(obj)), Global.rounding_tiers[tier])
                else:
                    max_buy = max_bin
                my_bid = bid['current_bid'] + Global.rounding_tiers[tier]
                if my_bid <= max_buy:
                    obj.bid(item=bid, amount=my_bid)
        common_process_transfer_targets(obj, strategy)
        obj.keep_alive(5)
    multi_log(obj, 'There are 0 remaining bids to fight for. Processing...')
    common_process_transfer_targets(obj, strategy)


@retry_decorator
def common_process_transfer_targets(obj, strategy, remaining_players=None, acquired=None, sell_price=None, sell_acquired_if_full=True):
    if obj.location != 'transfer_targets':
        obj.go_to('transfer_targets')
    winnings = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Won Items')]", gp_type='xpath', get_price=True)
    for won in winnings:
        send_result = ''
        if strategy == 'acquire':
            acquired.append((won['item_name'], won['current_bid']))
            for i, player_id in enumerate(remaining_players):
                if str(player_id) == str(won['resource_id']):
                    remaining_players.pop(i)
                    break
            send_result = obj.send_to_club(item=won, strategy='acquire')
            multi_log(obj=obj, message='Won {} for {}'.format(won['item_name'], won['current_bid']), level='green', notify=True, title='Item won',
                      icon_url=won['image'])
        if strategy != 'acquire' or send_result == 'owned' and sell_acquired_if_full:
            if not sell_price:
                futbin_price = won['futbin_price']
            elif type(sell_price) is dict:
                futbin_price = sell_price[won['item_name']]
            else:
                futbin_price = sell_price
            tier = info.get_tier(futbin_price)
            if strategy != 'price_fix':
                futbin_price = info.round_down(futbin_price * obj.bin_settings[tier]['sell_percent'], Global.rounding_tiers[tier])
            else:
                for num, pf_player in obj.strategy_settings['price_fix']['players'].items():
                    if str(pf_player['resource_id']) == str(won['resource_id']):
                        futbin_price = pf_player['sell_price']
                        break
            start_price = futbin_price - obj.bin_settings[tier]['spread']
            multi_log(obj=obj, message='Won {} for {}'.format(won['item_name'], won['current_bid']), level='green', notify=True, title='Item won',
                      icon_url=won['image'])
            database.bought_sold(obj, won, 'bought', strategy, won['current_bid'], expected_profit=((futbin_price * 0.95 * obj.bin_settings[tier]['sell_percent'])
                                                                                                    - won['current_bid']))
            try:
                sell_result = obj.sell(won, start_price, futbin_price)
                if sell_result == 'full':
                    common_deal_with_full_transfer_list(obj, strategy)
            except TimeoutException:
                try:
                    obj.__get_xpath__("//*[contains(text(), 'Transfer list full')]")
                    common_deal_with_full_transfer_list(obj, strategy)
                except TimeoutException:
                    pass
        elif send_result == 'owned' and not sell_acquired_if_full:
            obj.send_to_transfer_list(won)
    obj.clear_expired()
    return remaining_players, acquired


@retry_decorator
def common_wait_to_expire(obj, strategy, remaining_players=None, acquired=None, sell_price=None, sell_acquired_if_full=True):
    max_expire = 0
    obj.go_to('transfer_targets')
    bids = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Active Bids')]", gp_type='xpath', get_price=False)
    for bid in bids:
        if bid['time_left'] > max_expire:
            max_expire = bid['time_left']
    multi_log(obj, 'Waiting on last bid to expire...')
    if max_expire > 60:
        multi_log(obj, 'Will check every 30 seconds to see if we\'re outbid on everything.')
    while True:
        active_bids = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Active Bids')]", gp_type='xpath', get_price=False)
        winning = 0
        for bid in active_bids:
            if bid['bid_status'] == 'outbid':
                try:
                    bid['element'].click()
                    side_panel = obj.__get_class__('DetailView', as_list=False)
                    side_panel.find_element_by_class_name('watch').click()
                    obj.keep_alive(Global.micro_min)
                except (StaleElementReferenceException, WebDriverException):
                    pass
            else:
                if bid['time_left'] > max_expire:
                    max_expire = bid['time_left']
                winning += 1
        if winning == 0:
            break
        remaining_players, acquired = common_process_transfer_targets(obj, strategy, remaining_players, acquired, sell_price, sell_acquired_if_full)
        obj.keep_alive(30)
        if obj.location != 'home':
            obj.go_to('home')
        if obj.location != 'transfer_targets':
            obj.go_to('transfer_targets')
    remaining_players, acquired = common_process_transfer_targets(obj, strategy, remaining_players, acquired, sell_price, sell_acquired_if_full)
    return remaining_players, acquired


@retry_decorator
def common_deal_with_full_transfer_list(obj, strategy=None):
    current_location = obj.location
    multi_log(obj, 'Clearing out transfer list to make room for more transfers...')
    obj.clear_sold()
    while True:
        if strategy == 'acquire':
            break
        min_expire = 99999
        active_transfers = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Active Transfers')]", gp_type='xpath',
                                             get_price=False)
        if len(active_transfers) == 0:
            break
        for transfer in active_transfers:
            if transfer['time_left'] < min_expire:
                min_expire = transfer['time_left']
        multi_log(obj, 'Waiting on next transfer to expire...')
        obj.keep_alive(min_expire + 15)
        obj.clear_sold()
        obj.go_to('home')
    multi_log(obj, 'Transfer list is clear. Attempting to resume...')
    obj.go_to(current_location)
