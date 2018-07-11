from selenium.common.exceptions import TimeoutException, ElementNotVisibleException, NoSuchElementException, StaleElementReferenceException, WebDriverException
from time import sleep
from . import parse, info, database
from .misc import Global, multi_log
from retrying import retry
import requests


#############################
#       BUYING
#############################
def buy_now(obj, item, expected_profit, strategy=''):
    obj.__click_element__(item['element'])
    sidebar = obj.__get_xpath__('/html/body/section/article/section/section[2]/div/div')
    obj.__check_for_errors__()
    sidebar.find_element_by_xpath(".//*[contains(text(), 'Buy Now for')]").click()
    obj.rate_limit(immediate=True)
    sleep(Global.micro_min)
    result = obj.__check_for_errors__()
    if not result:
        return False
    try:
        modal = obj.__get_class__('ui-dialog-type-message', as_list=False)
        modal.find_element_by_xpath(".//*[contains(text(), 'Ok')]").click()
        sleep(Global.micro_max)
        result = obj.__check_for_errors__()
        if not result:
            return False
        multi_log(obj=obj, message='Bought {} at {}'.format(item['item_name'], item['buy_now_price']), level='green', notify=True, title='Bought Player',
                  icon_url=item['image'], link=info.get_player_info(item['asset_id'], include_futbin_price=False)['link'])
        database.bought_sold(obj, item, 'bought', strategy, item['buy_now_price'], expected_profit=expected_profit)
        return True
    except TimeoutException as e:
        obj.__check_for_errors__()
        multi_log(obj, 'Buy now error: {}'.format(e), level='debug')
        return False
    except WebDriverException:
        sleep(Global.micro_max)
        modal = obj.__get_class__('ui-dialog-type-message', as_list=False)
        modal.find_element_by_xpath(".//*[contains(text(), 'Ok')]").click()
        sleep(Global.micro_max)
        result = obj.__check_for_errors__()
        if not result:
            return False
        multi_log(obj=obj, message='Bought {} at {}'.format(item['item_name'], item['buy_now_price']), level='green', notify=True, title='Bought Player',
                  icon_url=item['image'], link=info.get_player_info(item['asset_id'], include_futbin_price=False)['link'])
        database.bought_sold(obj, item, 'bought', strategy, item['buy_now_price'], expected_profit=expected_profit)
        return True

@retry(wait_fixed=500, stop_max_attempt_number=3)
def bid(obj, item, amount):
    amount = str(amount)
    multi_log(obj, 'Bidding on {} at {}'.format(item['item_name'], amount))
    obj.__click_element__(item['element'])
    sidebar = obj.__get_class__('DetailView', as_list=False)
    price_box = sidebar.find_element_by_tag_name('input')
    obj.__type_element__(price_box, amount)
    obj.__check_for_errors__()
    # Ensure bid amount is correct and didn't change due to updated item status
    obj.__click_element__(sidebar)
    sleep(Global.micro_min)
    obj.rate_limit(immediate=True)
    if price_box.get_attribute('value') > amount:
        multi_log(obj, 'Attempted to bid {}, but item updated and amount changed'.format(amount))
        return False
    sidebar.find_element_by_xpath("//*[contains(text(), 'Make Bid')]").click()
    result = obj.__check_for_errors__()
    if result == 'limit':
        return 'limit'
    sleep(Global.micro_min)
    try:
        modal = obj.__get_xpath__('/html/body/div[1]/section/div/footer', timeout=Global.micro_min)
        result = obj.__check_for_errors__()
        if not result:
            return False
        if result == 'limit':
            return 'limit'
        modal.find_element_by_xpath("//*[contains(text(), 'Ok')]").click()
        result = obj.__check_for_errors__()
        if not result:
            return False
        if result == 'limit':
            return 'limit'
        multi_log(obj=obj, message='Bid on {} at {}'.format(item['item_name'], item['buy_now_price']), level='green')
        return True
    except TimeoutException:
        pass
    obj.__check_for_errors__()
    sleep(0.5)
    return True


@retry(wait_fixed=500, stop_max_attempt_number=3)
def buy_pack(obj, category, pack_type, send_all_to_club=False, quick_sell_duplicates=False, sell_duplicate_players=True):
    obj.rate_limit()
    if obj.location != 'store':
        obj.go_to('store')
    try:
        obj.__click_xpath__("//*[contains(text(), '{}')]".format(category.upper()))
        obj.keep_alive(Global.small_min)
    except TimeoutException:
        raise Exception('Unacceptable Pack Category')
    try:
        header = obj.__get_xpath__("//h1[text()='{}']".format(pack_type.upper()))
        parent = header.find_element_by_xpath('../..')
        obj.__check_for_errors__()
        parent.find_element_by_xpath(".//button[contains(@class, 'cCoins')]").click()
        obj.keep_alive(Global.small_min)
        modal = obj.__get_class__('ui-dialog-type-message', as_list=False)
        obj.__check_for_errors__()
        modal.find_element_by_xpath("//*[contains(text(), 'Ok')]").click()
        obj.keep_alive(Global.small_max)
        obj.location = 'unassigned'
    except TimeoutException:
        raise Exception('Unacceptable Pack Type')
    except NoSuchElementException:
        pass
    if send_all_to_club:
        obj.rate_limit()
        obj.__click_xpath__('//*[@id="Unassigned"]/section/header/div')
        obj.keep_alive(Global.small_min)
    try:
        if sell_duplicate_players:
            duplicate_players = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'DUPLICATES')]", gp_type='xpath',
                                                  get_price=True)
            for dupe in duplicate_players:
                if dupe['item_type'] == 'player':
                    price = dupe['futbin_price']
                    tier = info.get_tier(price)
                    bin_price = max(250, info.round_down(price * 0.9, Global.rounding_tiers[tier]))
                    if bin_price > 300:
                        start_price = bin_price - obj.bin_settings[tier]['spread']
                        sell(obj, dupe, start_price, bin_price)
                        sleep(Global.micro_min)
                    else:
                        multi_log(obj, 'Duplicate: {} is only worth {} and not worth listing. Will quick sell at the end'.format(dupe['item_name'], bin_price))
        if quick_sell_duplicates:
            try:
                duplicate_section = obj.__get_xpath__("//*[contains(text(), 'DUPLICATES')]", timeout=Global.small_min)
                duplicate_grandparent = duplicate_section.find_element_by_xpath('../..')
                obj.__check_for_errors__()
                duplicate_grandparent.find_element_by_class_name('coin-btn').click()
                obj.keep_alive(Global.small_min)
                modal = obj.__get_class__('ui-dialog-type-message', as_list=False)
                obj.__check_for_errors__()
                modal.find_element_by_xpath(".//*[contains(text(), 'Ok')]").click()
                obj.keep_alive(Global.small_min)
            except (ElementNotVisibleException, TimeoutException, NoSuchElementException) as e:
                multi_log(obj, 'BPM Quick Sell error: {}'.format(e), level='debug')
                pass
    except (ElementNotVisibleException, TimeoutException, NoSuchElementException):
        pass
    obj.keep_alive(Global.small_max)
    items = obj.__get_items__(get_price=True)
    return_items = items[:]
    for i, item in enumerate(items):
        if 'coins' in item['item_name'].lower():
            obj.__check_for_errors__()
            item['element'].click()
            obj.keep_alive(Global.micro_max)
            obj.__click_xpath__("//*[contains(text(), 'Redeem Coins')]")
            obj.keep_alive(Global.micro_max)
            multi_log(obj, 'Redeemed {}'.format(item['item_name']), level='green')
            return_items.pop(i)
            break
        elif 'Pack' in item['item_name'] and item['item_type'] != 'player':
            obj.__check_for_errors__()
            item['element'].click()
            obj.keep_alive(Global.micro_max)
            obj.__click_xpath__("//*[contains(text(), 'Redeem Pack')]")
            multi_log(obj, 'Redeemed {}'.format(item['item_name']), level='green')
            return_items.pop(i)
            break
    return return_items


#############################
#       SELLING
#############################
@retry(wait_fixed=500, stop_max_attempt_number=3)
def sell(obj, item, start_price, bin_price, duration='1 Hour'):
    if start_price < 150 or bin_price < 200:
        if item['quality'].lower() == 'bronze':
            start_price = 150
            bin_price = 200
        else:
            if bin_price != 0:
                multi_log(obj, 'Pricing Error: Start_price: {}  |  BIN_price: {}'.format(start_price, bin_price), level='error')
            return
    obj.rate_limit()
    element = item['element']
    try:
        obj.__check_for_errors__()
        obj.__click_element__(element)
        obj.__check_for_errors__()
    except StaleElementReferenceException:
        player_list = obj.driver.find_elements_by_class_name('listFUTItem')
        for e in player_list:
            if parse.remove_accents(e.find_element_by_class_name('name').text) == item['item_name']:
                e.click()
                break
    # Check if transfer list is full
    try:
        current_location = obj.location
        obj.driver.find_element_by_xpath("//*[contains(text(), 'Transfer List Full')]")
        multi_log(obj, 'Transfer list is full', level='warn')
        obj.go_to(current_location)
        return 'full'
    except (TimeoutException, ElementNotVisibleException, NoSuchElementException):
        pass
    try:
        obj.__click_xpath__("//*[contains(text(), 'List on Transfer Market')]")
        auction_panel = obj.__get_class__('ui-layout-right', as_list=False)
        sleep(Global.small_min)
        bid_section = auction_panel.find_element_by_xpath(".//*[contains(text(), 'Start Price')]")
        bid_grandparent = bid_section.find_element_by_xpath('../..')
        bid_input = bid_grandparent.find_element_by_tag_name('input')
        bin_section = auction_panel.find_element_by_xpath(".//*[contains(text(), 'Buy Now Price')]")
        bin_grandparent = bin_section.find_element_by_xpath('../..')
        bin_input = bin_grandparent.find_element_by_tag_name('input')
        duration_dropdown = auction_panel.find_element_by_class_name('drop-down-select')
        obj.__type_element__(bid_input, start_price)
        obj.__type_element__(bin_input, bin_price)
    except (NoSuchElementException, TimeoutException):
        return
    if duration_dropdown.text != duration:
        obj.__click_element__(duration_dropdown)
        duration_list = duration_dropdown.find_element_by_tag_name('ul')
        duration = duration_list.find_element_by_xpath("//*[contains(text(), '{}')]".format(duration))
        obj.__click_element__(duration)
        sleep(Global.micro_min)
    submit = auction_panel.find_element_by_xpath("//*[contains(text(), 'List Item')]")
    obj.__click_element__(submit)
    multi_log(obj=obj, message='Listed {} at {}/{}'.format(item['item_name'], start_price, bin_price), level='green', notify=True, title='Listed Item',
              icon_url=item['image'], link=info.get_player_info(item['asset_id'], include_futbin_price=False)['link'])
    sleep(Global.micro_max)


def quick_sell(obj, item, strategy=''):
    obj.rate_limit()
    element = item['element']
    obj.__check_for_errors__()
    element.click()
    side_panel = obj.__get_xpath__('/html/body/section/section/section/section[2]/div/div/div[3]')
    sell_button = side_panel.find_element_by_xpath(".//*[contains(text(), 'Quick Sell')]")
    obj.__click_element__(sell_button)
    modal = obj.__get_xpath__('/html/body/div[1]/section/div/footer/a[2]')
    obj.__check_for_errors__()
    modal.find_element_by_xpath("//*[contains(text(), 'Ok')]").click()
    multi_log(obj, 'Quick-sold {}'.format(item['item_name']), level='info')
    database.bought_sold(obj, item, 'sold', strategy, 1, 1)


@retry(wait_fixed=500, stop_max_attempt_number=3)
def relist_item(obj, item, start_price, bin_price, duration='1 Hour'):
    obj.rate_limit()
    element = item['element']
    try:
        obj.__check_for_errors__()
        obj.__click_element__(element)
    except StaleElementReferenceException:
        player_list = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Unsold Items')]", gp_type='xpath', get_price=False)
        for e in player_list:
            if parse.remove_accents(e['element'].find_element_by_class_name('name').text) == item['item_name']:
                e['element'].click()
                break
    try:
        obj.__click_xpath__("//*[contains(text(), 'Re-list Item')]")
        auction_panel = obj.__get_class__('ui-layout-right', as_list=False)
        sleep(Global.small_min)
        bid_section = auction_panel.find_element_by_xpath(".//*[contains(text(), 'Start Price')]")
        bid_grandparent = bid_section.find_element_by_xpath('../..')
        bid_input = bid_grandparent.find_element_by_tag_name('input')
        bin_section = auction_panel.find_element_by_xpath(".//*[contains(text(), 'Buy Now Price')]")
        bin_grandparent = bin_section.find_element_by_xpath('../..')
        bin_input = bin_grandparent.find_element_by_tag_name('input')
        duration_dropdown = auction_panel.find_element_by_class_name('drop-down-select')
        sleep(Global.micro_min)
        obj.__type_element__(bid_input, int(start_price))
        sleep(Global.micro_min)
        obj.__type_element__(bin_input, int(bin_price))
    except NoSuchElementException:
        return
    obj.__click_element__(duration_dropdown)
    sleep(Global.micro_min)
    duration_list = duration_dropdown.find_element_by_tag_name('ul')
    duration_selection = duration_list.find_element_by_xpath(".//*[contains(text(), '{}')]".format(duration))
    obj.__click_element__(duration_selection)
    sleep(Global.micro_min)
    submit = auction_panel.find_element_by_xpath(".//*[contains(text(), 'List Item')]")
    obj.__click_element__(submit)
    sleep(Global.micro_min)


#############################
#       HOUSEKEEPING
#############################
@retry(wait_fixed=500, stop_max_attempt_number=3)
def send_to_club(obj, item, strategy=''):
    obj.rate_limit()
    element = item['element']
    try:
        obj.__check_for_errors__()
        element.click()
    except StaleElementReferenceException:
        player_list = obj.driver.find_elements_by_class_name('listFUTItem')
        for e in player_list:
            if parse.remove_accents(e.find_element_by_class_name('name').text) == item['item_name']:
                e.click()
                break
    side_panel = obj.__get_class__('DetailView', as_list=False)
    try:
        send_button = side_panel.find_element_by_xpath(".//*[contains(text(), 'Send to My Club')]")
        obj.__click_element__(send_button)
        if item.get('futbin_price', 0) > 0:
            multi_log(obj, 'Sent {} to club. Worth: {}'.format(item['item_name'], item.get('futbin_price')), level='info')
        else:
            multi_log(obj, 'Sent {} to club'.format(item['item_name']), level='info')
    except NoSuchElementException:
        multi_log(obj, 'Already have {}.'.format(item['item_name']))
        return 'owned'
    if strategy == 'bpm':
        database.bought_sold(obj, item, 'bought', 'bpm', 99)


@retry(wait_fixed=500, stop_max_attempt_number=3)
def send_to_transfer_list(obj, item):
    obj.rate_limit()
    element = item['element']
    try:
        obj.__check_for_errors__()
        element.click()
    except StaleElementReferenceException:
        player_list = obj.driver.find_elements_by_class_name('listFUTItem')
        for e in player_list:
            if parse.remove_accents(e.find_element_by_class_name('name').text) == item['item_name']:
                e.click()
                break
    side_panel = obj.__get_class__('DetailView', as_list=False)
    send_button = side_panel.find_element_by_xpath(".//*[contains(text(), 'Send to Transfer List')]")
    obj.__click_element__(send_button)
    if item.get('futbin_price', 0) > 0:
        multi_log(obj, 'Sent {} to transfer list. Worth: {}'.format(item['item_name'], item.get('futbin_price')), level='info')
    else:
        multi_log(obj, 'Sent {} to transfer list'.format(item['item_name']), level='info')


@retry(wait_fixed=500, stop_max_attempt_number=3)
def relist_all(obj):
    if obj.settings['night_mode']['need_relist'] and obj.settings['night_mode']['enabled']:
        multi_log(obj, '[Day Mode] Relisting all transfers for 1 Hour')
        at_market = obj.settings['night_mode']['relist_at_market_for_day_mode']
        obj.relist_individually(at_market=at_market, duration='1 Hour')
    else:
        if obj.location != 'transfer_list':
            obj.go_to('transfer_list')
        try:
            obj.rate_limit()
            obj.__click_xpath__("//*[contains(text(), 'Re-list All')]", timeout=Global.small_min*2)
            obj.__click_xpath__("//*[contains(text(), 'Yes')]", timeout=Global.small_min*2)
            multi_log(obj, 'Items re-listed')
            obj.go_to('transfers')
        except TimeoutException:
            pass


@retry(wait_fixed=500, stop_max_attempt_number=3)
def clear_sold(obj):
    check_sold(obj)
    if obj.location != 'transfer_list':
        obj.go_to('transfer_list')
        sleep(obj.micro_min)
    try:
        obj.rate_limit()
        sold_items = obj.__get_xpath__("//*[contains(text(), 'Sold Items')]", timeout=Global.small_min*2)
        sold_parent = sold_items.find_element_by_xpath('..')
        sold_parent.find_element_by_class_name('section-header-btn').click()
        element = obj.driver.find_element_by_tag_name('body')
        obj.driver.execute_script("return arguments[0].scrollIntoView(true);", element)
        multi_log(obj, 'Sold items cleared')
    except (TimeoutException, ElementNotVisibleException):
        pass


@retry(wait_fixed=500, stop_max_attempt_number=3)
def check_sold(obj):
    if obj.location != 'transfer_list':
        obj.go_to('transfer_list')
        sleep(obj.micro_max)
    try:
        obj.__get_xpath__("//*[contains(text(), 'Sold Items')]")
    except (NoSuchElementException, TimeoutException):
        multi_log(obj, 'No sold elements')
        return []
    sold_items = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Sold Items')]", gp_type='xpath', get_price=False)
    for item in sold_items:
        multi_log(obj=obj, message='Sold {} for {}'.format(item['item_name'], item['current_bid']), level='green', notify=True, title='Item sold',
                  icon_url=item['image'], link=info.get_player_info(item['asset_id'], include_futbin_price=False)['link'])
        database.bought_sold(obj, item, 'sold', '', item['current_bid'])
    return sold_items


@retry(wait_fixed=500, stop_max_attempt_number=3)
def clear_expired(obj):
    if obj.location != 'transfer_targets':
        obj.go_to('transfer_targets')
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
    for asset, data in expired.items():
        tier = info.get_tier(data['bid_amounts'] / data['num_results'])
        rounding = Global.rounding_tiers[tier]
        expired[asset]['average_bid'] = info.round_down(data['bid_amounts'] / data['num_results'], rounding)
    for return_asset, return_info in expired.items():
        name = info.get_player_info(return_asset, False)['name']
        database.save_market_data(obj, name, return_asset, average_bid=return_info['average_bid'])
    try:
        obj.__check_for_errors__()
        obj.driver.find_element_by_xpath("//*[contains(text(), 'Clear Expired')]").click()
        element = obj.driver.find_element_by_tag_name('body')
        obj.driver.execute_script("return arguments[0].scrollIntoView(true);", element)
        multi_log(obj, 'Expired items cleared')
    except (NoSuchElementException, TimeoutException, ElementNotVisibleException, StaleElementReferenceException):
        pass


def apply_consumables_to_squad(obj, squad_name, consumable, level, rare=False, amount=1, include_subs=False, include_reserves=False):
    multi_log(obj, 'Applying {} {} {} to {} squad. Rare: {} | Subs: {} | Reserves: {}'.format(amount, level.title(), consumable.title(), squad_name.title(), rare,
                                                                                              include_subs, include_reserves))
    consumable = consumable.title()
    if consumable == 'Contract':
        consumable = 'Contracts'
    if obj.location != 'squad':
        obj.go_to('squads')
    if squad_name.lower() == 'active':
        obj.driver.find_element_by_class_name('mySquad').click()
    else:
        obj.__click_xpath__("//*[contains(text(), 'Squad Management')]")
        obj.location = 'squad_management'
        squads = obj.__get_class__('listFUTSquad', as_list=True)
        for squad in squads:
            if squad.find_element_by_tag_name('h1').text.lower() == squad_name.lower():
                obj.__click_element__(squad)
                sleep(1)
                side_panel = obj.__get_class__('squadDetailView', as_list=False)
                side_panel.find_element_by_xpath("//*[contains(text(), 'Open')]").click()
                break
    sleep(Global.small_min)
    players = obj.__get_class__('squadSlot', as_list=True)
    subs_open = False
    for player in players:
        player_amount = amount
        index = int(player.get_attribute('index'))
        if index <= 10 or (include_subs and 10 < index <= 17) or (include_reserves and 17 < index <= 22):
            if 10 < index <= 17 and not subs_open:
                obj.__click_xpath__("//*[contains(text(), 'SUBS')]")
                subs_open = True
            elif 17 < index <= 22:
                if subs_open:
                    obj.__click_xpath__("//*[contains(text(), 'SUBS')]")
                    subs_open = False
                obj.__click_xpath__("//*[contains(text(), 'RESERVES')]")
            obj.__click_element__(player)
            player.click()
            side_panel = obj.__get_class__('FUINavigationContent', as_list=False)
            try:
                side_panel.find_element_by_xpath("//*[contains(text(), 'Apply Consumable')]").click()
                options = obj.__get_class__('FUINavigationContent', as_list=False)
                sleep(Global.small_min)
                if 'squad' in consumable.lower():
                    options.find_element_by_xpath("//*[contains(text(), '{}')]".format(consumable)).click()
                else:
                    options.find_element_by_xpath("//*[contains(text(), '{}') and not(contains(text(), 'Squad')]".format(consumable)).click()
            except (TimeoutException, NoSuchElementException, ElementNotVisibleException):
                multi_log(obj, 'Consumable: {} is not an option'.format(consumable))
                return
            while player_amount > 0:
                items = obj.__get_items__(p_element='searchResults', p_type='class')
                use = None
                for item in items:
                    if (item['rare'] and rare) or (not item['rare'] and not rare) and item['quality'] == level.lower() and 'squad' not in item['item_name'].lower():
                        use = item
                        break
                try:
                    use['element'].find_element_by_tag_name('button').click()
                except TypeError:
                    multi_log(obj, 'Item doesn\'t exist or can\'t be used', level='warn')
                player_amount -= 1
                sleep(Global.micro_min)
    obj.location = 'club'


def futbin_login(obj, url):
    if obj.user['login_to_futbin']:
        try:
            button = obj.driver.find_element_by_xpath("//*[contains(text(), 'Login')]")
            button.click()
            obj.driver.execute_script("arguments[0].click()", button)
            obj.__type_xpath__('//*[@id="Email"]', obj.user['email'])
            obj.__type_xpath__('//*[@id="Password"]', obj.user['password'])
            obj.driver.find_element_by_class_name('form-submit-block').click()
            sleep(Global.small_max)
            try:
                obj.driver.find_element_by_xpath("//*[contains(text(), 'Login')]")
                multi_log(obj, 'Futbin User doesn\'t exist. Creating...')
                obj.driver.get('https://www.futbin.com/account/register')
                sleep(Global.small_max)
                obj.__type_xpath__('//*[@id="Email"]', obj.user['email'])
                obj.__type_xpath__('//*[@id="Username"]', obj.user['email'].split('@')[0].replace('+', ''))
                obj.__type_xpath__('//*[@id="Password"]', obj.user['password'])
                obj.__type_xpath__('//*[@id="PasswordConfirm"]', obj.user['password'])
                obj.driver.find_element_by_class_name('submit_register').click()
                multi_log(obj, 'Account registered. Visit verification link from email in bot\'s browser window')
                obj.wait_for_enter()
            except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                pass
            obj.keep_alive(Global.med_min)
            obj.driver.get(url)
        except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
            multi_log(obj, 'Either already logged into Futbin or unable to do so', level='debug')


def futbin_club_import(obj):
    multi_log(obj, 'Importing club into Futbin...')
    obj.new_tab('https://www.futbin.com/user/club')
    obj.location = 'futbin'
    obj.driver.switch_to.window(obj.driver.window_handles[-1])
    sleep(Global.small_max)
    futbin_login(obj, 'https://www.futbin.com/user/club')
    button = obj.driver.find_element_by_xpath("//*[@id='myclub']")
    obj.__click_element__(button)
    sleep(Global.small_max)
    obj.driver.execute_script("arguments[0].click()", button)
    obj.driver.switch_to.window(obj.driver.window_handles[0])
    obj.driver.get(obj.url)
    obj.driver.switch_to.window(obj.driver.window_handles[0])
    obj.__disable_click_shield__()
    obj.keep_alive(Global.med_max)
    obj.location = 'home'
    try:
        obj.go_to('transfer_list')
        obj.go_to('players')
    except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
        obj.driver.get(obj.url)
        obj.keep_alive(Global.large_max)
    while True:
        try:
            nav_bar = obj.__get_class__('pagingContainer', as_list=False)
        except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
            nav_bar = obj.__get_class__('mainHeader', as_list=False)
        try:
            next_btn = nav_bar.find_element_by_class_name('next')
            obj.__click_element__(next_btn)
        except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
            break
    try:
        obj.__click_element__(obj.__get_class__('searchAction', as_list=False))
    except TimeoutException:
        obj.driver.get(obj.url)
        sleep(Global.med_max)
    obj.__click_xpath__("//*[contains(text(), 'Untradeables Only')]")
    obj.__click_element__(obj.driver.find_element_by_class_name('call-to-action'))
    obj.keep_alive(Global.micro_min)
    while True:
        try:
            nav_bar = obj.__get_class__('pagingContainer', as_list=False)
        except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
            nav_bar = obj.__get_class__('mainHeader', as_list=False)
        try:
            next_btn = nav_bar.find_element_by_class_name('next')
            obj.__click_element__(next_btn)
        except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
            multi_log(obj, 'Done getting club players')
            break
    obj.driver.switch_to.window(obj.driver.window_handles[-1])
    sleep(Global.micro_max)
    obj.location = 'futbin'
    button = obj.driver.find_element_by_xpath("//*[@id='myclub']")
    obj.__click_element__(button)
    obj.driver.execute_script("arguments[0].click()", button)
    obj.keep_alive(Global.med_max)
    obj.driver.get('https://www.futbin.com/stc/analyze')
    obj.keep_alive(Global.small_max)
    button = obj.__get_class__('club-scan-btn', as_list=False)
    obj.__click_element__(button)
    obj.driver.execute_script("arguments[0].click()", button)
    obj.driver.switch_to.window(obj.driver.window_handles[0])
    multi_log(obj, 'Done importing club')
    obj.location = 'players'


#############################
#       SEARCH
#############################
@retry(wait_fixed=500, stop_max_attempt_number=2)
def search(obj, search_type='Players', player=None, item=None, rating=None, quality=None, position=None, chem_style=None, nation=None, league=None, club=None, min_buy=None,
           max_buy=None, min_bin=None, max_bin=None, start_page=0, include=None, exclude=None, reset=True):
    """
    Conduct a search in the transfer market and return results as a list of dicts. Try to make sure every string is as close to what it shows
    on the web app html source as possible
    :param reset:
    :param obj: Session/bot object
    :param search_type: str: Accepts 'Players', 'Staff', 'Club Items', 'Consumables'
    :param player: int or str: Either str of the player name or player id from fifa_players.json. If using name str, use full name if possible
    :param rating: int or str: Use if there are several players/cards close to same name but different ratings. 'Ronaldinho', for example
    :param quality: str: Gold, Silver, Bronze, Special
    :param position: str: Ensure this matches the web app html source
    :param chem_style: str: Ensure this matches the web app html source
    :param nation: str: Ensure this matches the web app html source
    :param league: str: Ensure this matches the web app html source
    :param club: str: Ensure this matches the web app html source
    :param min_buy: int
    :param max_buy: int
    :param min_bin: int
    :param max_bin: int
    :param start_page: int: starts at 0 as first page. Only returns results of start_page
    :param include: list of ints: List of player ids to include in results. If empty, returns all (except excluded)
    :param exclude: list of ints: List of player ids to exclude from results. If empty, excludes none (unless included isn't empty)
    :param reset: bool: click the reset button for the search to reset all inputs
    :return:
    """
    # Search
    # TODO: Test other search types
    def get_initials(word):
        words = word.split()
        letters = [word[0] for word in words]
        return "".join(letters)

    obj.__check_for_errors__()
    args = [search_type, player, rating, quality, position, chem_style, nation, league, club, min_buy, max_buy,
            min_bin, max_bin, start_page, include, exclude]
    multi_log(obj, 'Searching for {}'.format(args), level='debug')
    if 'search' not in obj.__get_class__('pageTitle', as_list=False, timeout=Global.med_max).text.lower():
        obj.location = 'xxx'
        obj.go_to('search')
    elif 'search' not in obj.location or 'club' in obj.location:
        obj.go_to('search')
    elif obj.location == 'search_results':
        header = obj.__get_class__('mainHeader', as_list=False)
        obj.__check_for_errors__()
        header.find_element_by_xpath('.//a[1]').click()
        obj.__check_for_errors__()
        obj.location = 'search'
    obj.rate_limit()
    search_type = search_type.title()
    if '_{}'.format(search_type) not in obj.location:
        try:
            menu_container = obj.__get_class__('menuContainer', as_list=False)
        except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
            obj.location = 'xxx'
            obj.go_to('search')
            sleep(Global.small_max)
            menu_container = obj.__get_class__('menuContainer', as_list=False)
            obj.__check_for_errors__()
        menu_container.find_element_by_xpath(".//*[contains(text(), '{}')]".format(search_type)).click()
        obj.location = 'search_{}'.format(search_type)
    search_panel = obj.__get_class__('filters-container-parent', as_list=False, timeout=Global.large_max)
    button_bar = obj.__get_class__('tabletButtons', as_list=False)
    search_prices = search_panel.find_element_by_class_name('searchPrices')
    # Ensure we didn't lose the name
    if not reset and player:
        obj.__click_element__(search_panel)
        sleep(Global.micro_min)
        name_box = search_panel.find_element_by_class_name('textInput')
        if len(name_box.get_attribute('value')) == 0:
            reset = True
    if reset:
        obj.__click_element__(button_bar.find_element_by_xpath(".//*[contains(text(), 'Reset')]"))
        sleep(Global.micro_min/2)
        if player:
            name_list = []
            if type(player) is not int:
                player = str(player)
            if type(player) is int or (type(player) is str and any(n in player for n in '1234567890')):
                have_id = True
                if int(player) >= 300000:
                    quality = 'Special'
                try:
                    db_player = Global.fifa_players[player]
                except KeyError:
                    try:
                        player = info.get_base_id(player)
                        db_player = Global.fifa_players[player]
                    except KeyError:
                        multi_log(obj, 'No player with id {} in fifa_players.json'.format(player), level='error')
                        return 'no_name'
                name_list = [db_player['first_name'], db_player['last_name'], db_player['surname']]
                temp_names = []
                for name in name_list:
                    if name:
                        temp_names.append(name)
                name_list = temp_names
                if len(name_list) == 3:
                    name_list = [name_list[2], name_list[0] + ' ' + name_list[1], name_list[0] + ' ' + name_list[2],
                                 name_list[1] + ' ' + name_list[2], name_list[1] + ' ' + name_list[0], name_list[1],
                                 name_list[2] + ' ' + name_list[0], name_list[2] + ' ' + name_list[1], name_list[0]]
                elif len(name_list) == 2:
                    name_list = [name_list[0] + ' ' + name_list[1], name_list[1] + ' ' + name_list[0], name_list[1], name_list[0]]
                if not rating and int(player) < 300000:
                    try:
                        rating = Global.fifa_players[player]['rating']
                    except KeyError:
                        pass
            else:
                have_id = False
                name = player.title()
                name_list.append(name)
            nation = None
            league = None
            club = None
            name_found = False
            while not name_found:
                if not name_list:
                    multi_log(obj, message='Unable to find {}'.format(player), level='error')
                    return []
                name = name_list[0]
                name_box = search_panel.find_element_by_class_name('textInput')
                obj.__type_element__(name_box, name)
                name_parent = name_box.find_element_by_xpath('..')
                sleep(Global.micro_max)
                result_list = name_parent.find_element_by_tag_name('ul')
                results = result_list.find_elements_by_class_name('btn-text')
                if not results:
                    if len(name_list) <= 1:
                        multi_log(obj, 'Unable to find results for {}'.format(player), level='warn', notify=True, title='Search Error')
                        return []
                    else:
                        og_name = name
                        new_name = name_list[1]
                        multi_log(obj, '\"{}\" not found. Trying \"{}\"'.format(og_name, new_name), level='debug')
                        search_panel = obj.__get_class__('filters-container-parent', as_list=False)
                        name_list = name_list[1:]
                else:
                    for r in results:
                        if have_id:
                            if rating and len(results) > 1:
                                result_parent = r.find_element_by_xpath('..')
                                result_rating = result_parent.find_element_by_class_name('btn-subtext').text
                                if str(rating) == str(result_rating):
                                    obj.__click_element__(r)
                                    name_found = True
                                    break
                            else:
                                try:
                                    obj.__click_element__(r)
                                    name_found = True
                                    break
                                except StaleElementReferenceException:
                                    return []
                        else:
                            if name.lower() in parse.remove_accents(r.text).lower():
                                if rating and len(results) > 1:
                                    result_parent = r.find_element_by_xpath('..')
                                    result_rating = result_parent.find_element_by_class_name('btn-subtext').text
                                    if str(rating) == str(result_rating):
                                        obj.__click_element__(r)
                                        name_found = True
                                        break
                                else:
                                    obj.__click_element__(r)
                                    name_found = True
                                    break
                    if not name_found:
                        name_list = name_list[1:]
        if item:
            item = item.title()
            item_dropdown = search_panel.find_element_by_xpath('./div/div[2]/div[1]/div[2]')
            obj.__click_element__(item_dropdown)
            sleep(2)
            obj.__check_for_errors__()
            item_dropdown.find_element_by_xpath(".//*[contains(text(), '{}')]".format(item)).click()
            sleep(2)
        if quality is not None:
            quality = quality.title()
            quality_dropdown = search_panel.find_element_by_xpath(".//*[contains(text(), 'Quality')]")
            obj.__click_element__(quality_dropdown)
            sleep(5)
            quality_parent = quality_dropdown.find_element_by_xpath('..')
            obj.__check_for_errors__()
            quality_parent.find_element_by_xpath(".//*[contains(text(), '{}')]".format(quality)).click()
        if position:
            if len(position) > 3:
                position = position.title()
            else:
                position = position.upper()
            position_dropdown = search_panel.find_element_by_xpath(".//*[contains(text(), 'Position')]")
            obj.__click_element__(position_dropdown)
            position_parent = position_dropdown.find_element_by_xpath('..')
            obj.__check_for_errors__()
            position_parent.find_element_by_xpath(".//*[contains(text(), '{}')]".format(position)).click()
        if chem_style:
            chem_style = chem_style.upper()
            chem_style_dropdown = obj.driver.find_element_by_xpath("//*[text()='Chemistry Style']")
            obj.__click_element__(chem_style_dropdown)
            chem_style_parent = chem_style_dropdown.find_element_by_xpath('..')
            obj.__check_for_errors__()
            chem_style_parent.find_element_by_xpath(".//*[contains(text(), '{}')]".format(chem_style)).click()
        if nation:
            nation = parse.nation_fix(nation)
            nation_dropdown = search_panel.find_element_by_xpath(".//*[contains(text(), 'Nationality')]")
            obj.__click_element__(nation_dropdown)
            nation_parent = nation_dropdown.find_element_by_xpath('..')
            obj.__check_for_errors__()
            nation_parent.find_element_by_xpath(".//*[contains(text(), '{}')]".format(nation)).click()
        if league:
            league = parse.league_fix(league)
            league_dropdown = search_panel.find_element_by_xpath(".//*[contains(text(), 'League')]")
            obj.__click_element__(league_dropdown)
            league_parent = league_dropdown.find_element_by_xpath('..')
            obj.__check_for_errors__()
            leagues = league_parent.find_elements_by_tag_name('li')
            found_league = False
            for l in leagues:
                if league.lower() in parse.remove_accents(l.text.lower()):
                    obj.__click_element__(l)
                    found_league = True
                    break
            if not found_league:
                league_initials = get_initials(league)
                for l in leagues:
                    if league_initials.lower() in parse.remove_accents(l.text.lower()):
                        obj.__click_element__(l)
                        found_league = True
                        break
                if not found_league:
                    multi_log(obj, 'Unable to find league: {}'.format(league), level='crit', notify=True)
                    raise Exception('Unable to find leage: {}'.format(league))
        if club:
            if type(club) is int:
                club = database.get_ea_name_from_id('fifa_clubs', club, type='id')
            else:
                club = parse.club_fix(club)
            club_dropdown = search_panel.find_element_by_xpath(".//*[contains(text(), 'Club')]")
            obj.__click_element__(club_dropdown)
            club_parent = club_dropdown.find_element_by_xpath('..')
            obj.__check_for_errors__()
            clubs = club_parent.find_elements_by_tag_name('li')
            found_club = False
            for c in clubs:
                if c.text and club and parse.remove_accents(c.text.lower()) == parse.remove_accents(club.lower()):
                    obj.__click_element__(c)
                    found_club = True
                    break
            if not found_club:
                club_initials = get_initials(club)
                for c in clubs:
                    if club_initials.lower() == parse.remove_accents(c.text.lower()):
                        obj.__click_element__(c)
                        found_club = True
                        break
                if not found_club:
                    multi_log(obj, 'Unable to find club: {}'.format(parse.remove_accents(club).lower()), level='crit', notify=True)
                    raise Exception('Unable to find club: {}'.format(parse.remove_accents(club).lower()))
        if min_buy:
            min_buy_box = search_prices.find_element_by_xpath('./div[2]/div[2]/div/input')
            obj.__type_element__(min_buy_box, min_buy)
        if max_buy:
            max_buy_box = search_prices.find_element_by_xpath('./div[3]/div[2]/div/input')
            obj.__type_element__(max_buy_box, max_buy)
        if min_bin:
            min_bin_box = search_prices.find_element_by_xpath('./div[5]/div[2]/div/input')
            obj.__type_element__(min_bin_box, min_bin)
        if max_bin:
            max_bin_box = search_prices.find_element_by_xpath('./div[6]/div[2]/div/input')
            obj.__type_element__(max_bin_box, max_bin)
    if not reset and not min_bin and not min_buy:  # To make sure we're getting fresh results
        min_bin_box = search_prices.find_element_by_xpath('./div[5]/div[2]/div/input')
        min_bin_gp = min_bin_box.find_element_by_xpath('../..')
        try:
            to_press = min_bin_gp.find_element_by_class_name('decrementBtn')
            if 'disabled' not in to_press.get_attribute('class'):
                obj.__type_element__(min_bin_box, 0)
                to_press.click()
            else:
                to_press = min_bin_gp.find_element_by_class_name('incrementBtn')
                to_press.click()
        except (ElementNotVisibleException, NoSuchElementException):
            pass
    obj.__click_element__(button_bar.find_element_by_xpath(".//*[contains(text(), 'Search')]"))
    obj.location = 'search_results'
    if start_page != 0:
        while start_page > 0:
            try:
                nav_bar = obj.__get_class__('pagingContainer', as_list=False)
            except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                nav_bar = obj.__get_class__('mainHeader', as_list=False)
            try:
                next_btn = nav_bar.find_element_by_class_name('next')
                obj.__click_element__(next_btn)
                obj.keep_alive(Global.micro_max)
                start_page -= 1
            except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
                break
    try:
        sleep(Global.micro_min)
        results = obj.__get_items__(get_price=True, timeout=Global.micro_max)
    except TimeoutException:
        return []
    return_data = []
    for item in results:
        # print(item['asset_id'], item['resource_id'])
        if include and item['asset_id'] in include:
            return_data.append(item)
        elif exclude and item['asset_id'] not in exclude:
            return_data.append(item)
        elif not exclude and not include:
            return_data.append(item)
    # print(return_data)
    if len(results) < 12:
        bin_results = {}
        for result in results:
            if result['asset_id'] not in list(bin_results.keys()) and result['time_left'] <= 58 * 60:
                bin_results[result['asset_id']] = {
                    'bins': result['buy_now_price'],
                    'count': 1
                }
            elif result['asset_id'] in list(bin_results.keys()):
                bin_results[result['asset_id']]['bins'] = result['buy_now_price']
                bin_results[result['asset_id']]['count'] += 1
        for asset, data in bin_results.items():
            tier = info.get_tier(data['bins'] / data['count'])
            rounding = Global.rounding_tiers[tier]
            bin_results[asset]['minimum_bin'] = info.round_down(data['bins'] / data['count'], rounding)
            name = info.get_player_info(asset, False)['name']
            database.save_market_data(obj, name, asset, minimum_bin=data['minimum_bin'])
    return return_data
