from FUTpuppeteer import actions, info
from FUTpuppeteer.misc import multi_log, Global
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from retrying import retry
from datetime import datetime
from . import retry_decorator, check_sleep


@retry_decorator
def bpm(obj):
    check_sleep(obj)
    obj.current_strategy = 'BPM'
    settings = obj.strategy_settings['bpm']
    quick_sell_types = settings['quick_sell_types']
    min_sell_types = settings['min_sell_types']
    club_types = settings['club_types']
    now = datetime.now()
    day = now.weekday()
    if day >= 4 and settings['adjust_for_weekend_league']:
        multi_log(obj, 'It\'s the weekend. Min-selling all healing, fitness, and contracts due to weekend-league demand')
        for thing in ['contract', 'fitness', 'healing']:
            if thing not in min_sell_types:
                min_sell_types.append(thing)
                for i, t in enumerate(club_types[:]):
                    if t == thing:
                        club_types.pop(i)
        print('club: {}, min: {}'.format(club_types, min_sell_types))

    def process_items(items):
        for item in items:
            if item['item_type'] == 'player':
                price = item['futbin_price']
                tier = info.get_tier(price)
                bin_price = max(250, info.round_down(price * obj.bin_settings[tier]['sell_percent'], Global.rounding_tiers[tier]))
                if bin_price > 350:
                    start_price = bin_price - obj.bin_settings[tier]['spread']
                    actions.sell(obj, item, start_price, bin_price)
                else:
                    actions.send_to_club(obj, item, strategy='bpm')
            elif item['item_type'] == 'fitness' and 'squad' in item['item_name'].lower():
                if settings['keep_squad_fitness']:
                    actions.send_to_club(obj, item, strategy='bpm')
                else:
                    actions.sell(obj, item, 500, 800)
            elif item['item_type'] == 'healing':
                if any(s in item['item_name'].lower() for s in ['all', 'upper', 'foot', 'leg', 'knee', 'arm']):
                    if 'all' in item['item_name'].lower():
                        actions.sell(obj, item, 250, 500)
                    else:
                        actions.sell(obj, item, 150, 200)
                else:
                    actions.send_to_club(obj, item, strategy='bpm')
            elif min_sell_types and item['item_type'] in min_sell_types:
                actions.sell(obj, item, 150, 200)
            elif club_types and item['item_type'] in club_types:
                if item['item_type'] == 'fitness' and 'squad' in item['item_name'].lower():
                    actions.sell(obj, item, 300, 500)
                elif item['quality'] != 'bronze' and item['item_type'] != 'staff':
                    actions.sell(obj, item, 150, 200)
                else:
                    actions.send_to_club(obj, item, strategy='bpm')
            elif quick_sell_types and item['item_type'] in quick_sell_types:
                if item['item_type'] == 'training' and 'all' in item['item_name'].lower():
                    actions.sell(obj, item, 200, 400)
                else:
                    multi_log(obj, 'Will quick sell {} at the end'.format(item['item_name']))
            elif item['item_type'].lower != 'coins' :
                item['element'].click()
                obj.driver.find_element_by_xpath(".//*[contains(text(), 'Redeem')]").click()
            else:
                multi_log(obj, 'NEW ITEM IN BPM: {}'.format(item), level='warn', notify=True, icon_url=item['image'])
            obj.keep_alive(Global.micro_max)
        try:
            obj.keep_alive(Global.small_max)
            obj.driver.find_element_by_xpath(".//*[contains(text(), 'Quick Sell') and (contains(text(), 'Item'))]").click()
            multi_log(obj, 'Quick selling remaining items')
            obj.keep_alive(Global.small_max)
            modal = obj.__get_class__('ui-dialog-type-message', as_list=False)
            modal.find_element_by_xpath(".//*[contains(text(), 'Ok')]").click()
            obj.location = 'store'
        except Exception as e:
            multi_log(obj, e, level='error')
        obj.keep_alive(Global.small_max)

    def check_unassigned():
        page_title = obj.__get_class__('pageTitle', as_list=False).text.lower()
        if page_title != 'unassigned':
            obj.__check_for_errors__()
            try:
                modal = obj.__get_class__('ui-dialog-type-message', as_list=False)
                modal.find_element_by_xpath(".//*[contains(text(), 'Take Me There')]").click()
                obj.__check_for_errors__()
                items = obj.__get_items__(get_price=True)
                process_items(items)
            except (NoSuchElementException, TimeoutException):
                pass
            try:
                while obj.__get_xpath__('//*[@id="UnassignedTile"]', timeout=Global.micro_max):
                    obj.go_to('unassigned')
                    items = obj.__get_items__(get_price=True)
                    process_items(items)
            except (NoSuchElementException, TimeoutException):
                pass

    @retry(wait_fixed=250, stop_max_attempt_number=3)
    def get_items():
        items = actions.buy_pack(obj, 'Bronze', 'Bronze Pack', send_all_to_club=False, quick_sell_duplicates=True, sell_duplicate_players=True)
        process_items(items)

    multi_log(obj, 'Bronze Pack Method...', level='title')
    check_unassigned()
    get_items()
    check_unassigned()
    return 0
