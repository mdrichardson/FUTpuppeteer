from FUTpuppeteer import info, database, actions
from FUTpuppeteer.misc import multi_log, Global
from . import retry_decorator, check_sleep
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotVisibleException, WebDriverException

@retry_decorator
def market_monitor(obj):
    def check_transfer_targets(return_data):
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
            if expired_bid['asset_id'] in settings['players']:
                if expired_bid['asset_id'] not in list(expired.keys()):
                    expired[expired_bid['asset_id']] = {
                        'bid_amounts': 0,
                        'num_results': 0
                    }
                expired[expired_bid['asset_id']]['bid_amounts'] += expired_bid['current_bid']
                expired[expired_bid['asset_id']]['num_results'] += 1
        for asset, data in expired.items():
            return_data[asset]['average_bid'] = info.round_down(data['bid_amounts'] / data['num_results'], rounding)
        for return_asset, return_info in return_data.items():
            name = info.get_player_info(return_asset, False)['name']
            multi_log(obj, '{}\'s Average Bid: {}'.format(name, return_info['average_bid']))
            database.save_market_data(obj, name, return_info['asset_id'], return_info['average_bid'], return_info['minimum_bin'])
        obj.clear_expired()
        return {}, 0

    check_sleep(obj)
    obj.current_strategy = 'Market Monitor'
    settings = obj.strategy_settings['market_monitor']
    multi_log(obj, 'Monitoring Market...', level='title')
    obj.clear_expired()
    cumulative_bids = 0
    return_data = {}
    for player in settings['players']:
        return_data[player] = {
            'asset_id': player,
            'minimum_bin': 0,
            'average_bid': 0
        }
        num_results = 0
        total_bins = 0
        player_info = info.get_player_info(player, include_futbin_price=True)
        name = player_info['name']
        futbin_price = player_info['futbin_price']
        tier = info.get_tier(futbin_price)
        rounding = Global.rounding_tiers[tier]
        max_bin = futbin_price - (rounding * 2)
        search_criteria = {
            'search_type': 'Players',
            'player': player,
        }
        multi_log(obj, 'Getting market data for {}. Futbin price: {}'.format(name, futbin_price))
        # Get bin info
        bin_with_results = []
        while num_results < settings['min_results']:
            bin_results = actions.search(obj=obj, max_bin=max_bin, **search_criteria)
            if len(bin_results) > settings['max_results']:
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
            else:
                for bin_result in bin_results:
                    if bin_result['buy_now_price'] not in bin_with_results:
                        total_bins += bin_result['buy_now_price']
                        num_results += 1
                if len(bin_results) > 0:
                    bin_with_results.append(max_bin)
            max_bin += rounding
        minimum_bin = info.round_down(total_bins / num_results, rounding)
        multi_log(obj, '{}\'s Average Minimum BIN: {}'.format(name, minimum_bin))
        return_data[player]['minimum_bin'] = minimum_bin
        # Get bid info
        max_buy = max(minimum_bin + (5 * rounding), futbin_price + (3 * rounding))
        num_results = 0
        bid_results = actions.search(obj=obj, max_buy=max_buy, **search_criteria)
        for bid_result in bid_results:
            if bid_result['time_left'] <= 300 and (bid_result['current_bid'] != bid_result['start_price'] or bid_result['current_bid'] <=
                                                   (futbin_price - (5 * rounding))) and num_results < settings['min_results']:
                try:
                    bid_result['element'].click()
                except WebDriverException:
                    try:
                        obj.__click_xpath__(".//*[contains(text(), 'OK')]")
                    except TimeoutException:
                        pass
                    check_transfer_targets(return_data)
                obj.keep_alive(Global.micro_min)
                side_panel = obj.__get_class__('DetailView', as_list=False)
                try:
                    side_panel.find_element_by_class_name('watch').click()
                    num_results += 1
                    cumulative_bids += 1
                except (ElementNotVisibleException, TimeoutException, NoSuchElementException):
                    pass
                except WebDriverException:
                    obj.__click_xpath__(".//*[contains(text(), 'OK')]")
                    check_transfer_targets(return_data)
            elif num_results >= settings['min_results']:
                break
    check_transfer_targets(return_data)



