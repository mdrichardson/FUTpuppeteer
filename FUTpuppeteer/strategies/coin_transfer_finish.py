import os
import sys
from FUTpuppeteer.misc import multi_log, Global
from FUTpuppeteer.core import Session
from FUTpuppeteer import info
from datetime import datetime, timedelta
from time import sleep
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotVisibleException
import signal
from ruamel.yaml import YAML

yaml = YAML()
yaml.explicit_start = True
yaml.indent(mapping=4)
yaml.preserve_quotes = True
if len(sys.argv) != 3:
    print('Missing arguments in coin_finish_transfer.py. Have {}, need 2: gain_coins, lose_coins').format(len(sys.argv))
    sys.exit(1)
gain_coins = sys.argv[1]
lose_coins = sys.argv[2]

directory = os.path.dirname(os.path.abspath(__file__))
gain_config_file = '\\'.join(directory.split('\\')[:-2]) + '\config\\bot{}.yml'.format(gain_coins)
with open(gain_config_file) as config:
    gain_config = yaml.load(config)
settings = gain_config['coin_transfer']
remaining = []
sorted_players = result = sorted(settings['players'], key=lambda x: x['expires'])
for player in sorted_players:
    if str(player['lose_coins']) == str(lose_coins) and player['expires'] > datetime.now():
        remaining.append(player)
while len(remaining) > 0:
    for i, player in enumerate(remaining):
        asset_id = player['asset_id']
        base_id = info.get_base_id(asset_id)
        name = info.get_player_info(base_id, include_futbin_price=False)['name']
        bid_price = player['start_price']
        bin_price = player['bin_price']
        multi_log(None, 'Received coin transfer information. Waiting until {} is near expiration'.format(name))
        expires = player['expires']
        multi_log(None, '{} will expire at {}'.format(name, '{0:%H:%M on %m/%d}'.format(expires)))
        start = expires - timedelta(minutes=5)
        while True:
            now = datetime.now()
            if start <= now < expires:
                break
            else:
                t = (start - now).seconds
                while t > 0:
                    time = str(t).split('.')[0]
                    if t > 60:
                        minutes = int(t / 60)
                        seconds = str(t % 60).split('.')[0]
                        if len(seconds) == 1:
                            seconds = '0' + seconds
                        sys.stdout.write('\rPausing for: {}:{}s'.format(minutes, seconds))
                    else:
                        sys.stdout.write('\rPausing for: {}s'.format(time))
                    t -= 1
                    sys.stdout.flush()
                    sleep(1)
                sys.stdout.write('\r')
        multi_log(None, 'Transferring Coins...', level='header')
        lose_config_file = '\\'.join(directory.split('\\')[:-2]) + '\config\\bot{}.yml'.format(lose_coins)
        with open(lose_config_file) as config:
            gain_config = yaml.load(config)
            pids = gain_config['pid']
        notify = False
        for pid in pids:
            try:
                os.kill(pid, signal.SIGINT)
                notify = True
            except OSError:
                pass
        if notify:
            multi_log(None, 'Bot{} is currently running. Killing it so we can transfer coins...'.format(lose_coins))

        obj = Session(bot_number=lose_coins, delay_login=False, debug=True, headless=False)

        results = []
        multi_log(None, 'Searching for {} at {}/{}'.format(name, bid_price, bin_price))
        obj.search('Players', asset_id, quality='Special', min_buy=bid_price, max_bin=bin_price)
        while True:
            search_results = obj.__get_items__(get_price=False)
            for result in search_results:
                if result['start_price'] == bid_price and result['buy_now_price'] == bin_price:
                    results.append(result)
            try:
                nav_bar = obj.__get_class__('pagingContainer', as_list=False)
            except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                nav_bar = obj.__get_class__('mainHeader', as_list=False)
            try:
                next_btn = nav_bar.find_element_by_class_name('next')
                obj.__click_element__(next_btn)
                obj.keep_alive(Global.micro_max)
            except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                break
        if len(results) == 0:
            raise Exception('No results found for coin transfer')
        elif len(results) > 1:
            multi_log(None, 'Too many results. Try bidding on the appropriate one and press enter when done.', notify=True, level='warn')
        else:
            obj.bid(results[0], bid_price)
        # Monitor for completion
        obj.go_to('transfer_targets')
        done = False
        multi_log(None, 'Waiting for bid to expire...')
        check_won = False
        while not done:
            active_bids = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Active Bids')]", gp_type='xpath', get_price=False)
            for bid in active_bids:
                if bid['asset_id'] == asset_id:
                    if bid['bid_status'] == 'outbid':
                        multi_log(None, 'Somebody outbid us for the coin transfer. Free coins!', notify=True, level='green')
                        done = True
                        break
                    elif bid['bid_status'] == 'won':
                        multi_log(None, 'Coin transfer complete!', notify=True, level='green')
                        done = True
                        del remaining[i]
                        with open(gain_config_file) as config:
                            gain_config = yaml.load(config)
                        gain_config['coin_transfer']['players'] = [p for p in gain_config['coin_transfer']['players'] if p['asset_id'] != asset_id]
                        break
                    else:
                        expires = bid['time_left']
                        obj.keep_alive(int(expires) + 5)
            if len(active_bids) == 0:
                check_won = True
                break
        if check_won:
            obj.go_to('home')
            obj.go_to('transfer_targets')
            sleep(Global.small_min)
            won_items = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Won Items')]", gp_type='xpath', get_price=False)
            for bid in won_items:
                if bid['bid_status'] == 'won' and bid['asset_id'] == asset_id:
                    multi_log(None, 'Coin transfer complete!', notify=True, level='green')
                    obj.send_to_club(bid)
                    done = True
                    del remaining[i]
                    with open(gain_config_file) as config:
                        gain_config = yaml.load(config)
                    gain_config['coin_transfer']['players'] = [p for p in gain_config['coin_transfer']['players'] if p['asset_id'] != asset_id]
                    break
        break
    break

lose_config_file = '\\'.join(directory.split('\\')[:-2]) + '\config\\bot{}.yml'.format(lose_coins)
with open(lose_config_file) as config:
    gain_config = yaml.load(config)
    pids = gain_config['pid']
notify = False
for pid in pids:
    try:
        os.kill(pid, signal.SIGINT)
        notify = True
    except OSError:
        pass
