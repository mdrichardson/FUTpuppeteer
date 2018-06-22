from FUTpuppeteer.misc import multi_log, Global
from FUTpuppeteer import info, parse
from . import coin_transfer_finish_prep
from datetime import datetime, timedelta
from time import sleep
from selenium.common.exceptions import StaleElementReferenceException
from random import uniform as rand
from ruamel.yaml import YAML

yaml = YAML()
yaml.explicit_start = True
yaml.indent(mapping=4)
yaml.preserve_quotes = True


def find_player(obj, player_to_search):
    obj.go_to('players')
    search_button = obj.__get_class__('searchAction', as_list=False)
    obj.__click_element__(search_button)
    rating = None
    quality = 'Special'
    search_panel = obj.__get_class__('searchContainer', as_list=False)
    sleep(Global.micro_min / 2)
    name_list = []
    if type(player_to_search) is int or (type(player_to_search) is str and any(n in player_to_search for n in '1234567890')):
        have_id = True
        try:
            db_player = Global.fifa_players[player_to_search]
        except KeyError:
            multi_log(obj, 'No player with id {} in fifa_players.json'.format(player_to_search), level='error')
            try:
                player_to_search = info.get_base_id(player_to_search)
                db_player = Global.fifa_players[player_to_search]
            except KeyError:
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
        if not rating and int(player_to_search) < 300000:
            try:
                rating = Global.fifa_players[player_to_search]['rating']
            except KeyError:
                pass
    else:
        have_id = False
        name = player_to_search.title()
        name_list.append(name)
    name_found = False
    while not name_found:
        if not name_list:
            multi_log(obj, message='Unable to find {}.'.format(player_to_search))
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
                multi_log(obj, 'Unable to find results for {}'.format(player_to_search), level='warn', notify=True, title='Search Error')
                return []
            else:
                og_name = name
                new_name = name_list[1]
                multi_log(obj, '\"{}\" not found. Trying \"{}\"'.format(og_name, new_name), level='debug')
                search_panel = obj.__get_class__('ClubSearchFilters', as_list=False)
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
    quality = quality.title()
    quality_dropdown = search_panel.find_element_by_xpath(".//*[contains(text(), 'Quality')]")
    obj.__click_element__(quality_dropdown)
    sleep(5)
    quality_parent = quality_dropdown.find_element_by_xpath('..')
    obj.__check_for_errors__()
    quality_parent.find_element_by_xpath(".//*[contains(text(), '{}')]".format(quality)).click()
    obj.__click_element__(search_panel.find_element_by_xpath(".//*[contains(text(), 'Search')]"))
    sleep(Global.small_min)
    results = obj.__get_items__(get_price=False)
    return results


def coin_transfer_list(obj, lose_coins, players):
    # List player for 80-90% of max with a bid random few steps below and for 1 day
    run_transfer_finish = False
    for i, player in enumerate(players):
        name = info.get_player_info(player)['name']
        tier = info.get_tier(38000)
        step = Global.rounding_tiers[tier]
        start_price = info.round_down(int(38000 + (rand(-10, 10) * step)), Global.rounding_tiers[tier])
        bin_price = info.round_down(start_price + (rand(6, 10) * step), Global.rounding_tiers[tier])
        result = find_player(obj, player)
        if len(result) == 1:
            run_transfer_finish = True
            obj.sell(result[0], start_price, bin_price, duration='1 Day')
            # Record min bid and bin and time to expire
            expires = datetime.now() + timedelta(days=1)
            with open(obj.config_file) as config:
                new_config = yaml.load(config)
                new_player = {
                    'asset_id': player,
                    'start_price': start_price,
                    'bin_price': bin_price,
                    'expires': expires,
                    'lose_coins': lose_coins
                    }
                try:
                    new_config['coin_transfer']['players'].append(new_player)
                except AttributeError:
                    new_config['coin_transfer']['players'] = []
                    new_config['coin_transfer']['players'].append(new_player)
            with open(obj.config_file, 'w') as update:
                yaml.dump(new_config, update)
        else:
            multi_log(obj, 'Error finding player {} for coin transfer'.format(name), level='error', notify=True, title='Coin Transfer Error')
    if run_transfer_finish:
        # Start buy script that runs in background
        coin_transfer_finish_prep.prep(obj.bot_number, lose_coins)
        multi_log(obj, 'Waiting for coin transfer to finish in the background.')
        obj.location = 'home'
    else:
        multi_log(obj, 'Something went wrong with coin transferring and there were no players to list.', level='error', notify=True, title='Coin Transfer Error')

