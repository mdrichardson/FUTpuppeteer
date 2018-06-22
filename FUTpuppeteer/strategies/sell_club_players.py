from FUTpuppeteer import actions, info, parse
from FUTpuppeteer.misc import multi_log, Global
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotVisibleException
from . import retry_decorator


@retry_decorator
def sell_club_players(obj, search='all', min_sell_bronze=300, min_sell_silver=400, min_sell_gold=800, rare_multiplier=1.35, exclude=None):
    obj.current_strategy = 'Sell Club Players'
    if not exclude:
        exclude = []
    if obj.location != 'players':
        obj.go_to('players')
    if search != 'all':
        search_button = obj.__get_class__('searchAction', as_list=False)
        obj.__click_element__(search_button)
        search = search.title()
        search_panel = obj.__get_class__('searchContainer', as_list=False)
        quality_dropdown = search_panel.find_element_by_xpath(".//*[contains(text(), 'Quality')]")
        obj.__click_element__(quality_dropdown)
        quality_parent = quality_dropdown.find_element_by_xpath('..')
        obj.__check_for_errors__()
        quality_parent.find_element_by_xpath(".//*[contains(text(), '{}')]".format(search)).click()
        button_bar = obj.__get_class__('layout-flex-bar', as_list=False)
        obj.__click_element__(button_bar.find_element_by_xpath(".//*[contains(text(), 'Search')]"))
        obj.location = 'club_search_results'
    multi_log(obj, 'Getting {} club players. This takes approx. 1 minute per 100 players'.format(search))
    while True:
        obj.keep_alive(Global.small_max)
        page_players = obj.__get_items__(get_price=False)
        for player in page_players:
            futbin_data = info.get_price(player['asset_id'], obj, True)
            if futbin_data != 0:
                updated = futbin_data[1]
                price = futbin_data[0]
                if updated > 8 * 60 * 60 or price == 0:
                    continue
                if player['quality'] == 'bronze' and price >= min_sell_bronze and player['asset_id'] not in exclude:
                    min_price = min_sell_bronze
                    if player['rare']:
                        min_price *= rare_multiplier
                elif player['quality'] == 'silver' and price >= min_sell_silver and player['asset_id'] not in exclude:
                    min_price = min_sell_silver
                    if player['rare']:
                        min_price *= rare_multiplier
                elif player['quality'] == 'gold' and price >= min_sell_gold and player['asset_id'] not in exclude:
                    min_price = min_sell_gold
                    if player['rare']:
                        min_price *= rare_multiplier
                else:
                    continue
                if price > min_price:
                    player_list = obj.driver.find_elements_by_class_name('listFUTItem')
                    for e in player_list:
                        if parse.remove_accents(e.find_element_by_class_name('name').text) == player['item_name'] and not player['loan']:
                            e.click()
                            break
                    panel = obj.__get_class__('DetailView', as_list=False, timeout=Global.micro_min)
                    try:
                        panel.find_element_by_xpath(".//*[contains(text(), 'This item cannot be traded')]")
                    except (NoSuchElementException, TimeoutException):
                        tier = info.get_tier(price)
                        bin_price = int(max(min_price, info.round_down(price * obj.bin_settings[tier]['sell_percent'], Global.rounding_tiers[tier])))
                        start_price = bin_price - obj.bin_settings[tier]['spread']
                        result = actions.sell(obj, player, start_price, bin_price)
                        if result == 'full':
                            return
                        obj.keep_alive(Global.micro_max)
        try:
            nav_bar = obj.__get_class__('pagingContainer', as_list=False)
        except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
            nav_bar = obj.__get_class__('mainHeader', as_list=False)
        try:
            next_btn = nav_bar.find_element_by_class_name('next')
            obj.__click_element__(next_btn)
        except (ElementNotVisibleException, NoSuchElementException, TimeoutException):
            multi_log(obj, 'Done selling club players')
            break
