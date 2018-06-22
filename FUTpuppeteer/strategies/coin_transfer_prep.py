from FUTpuppeteer.misc import multi_log, Global
from FUTpuppeteer.parse import parse_futbin_players_table
from FUTpuppeteer.info import get_special_ids
from FUTpuppeteer import info, parse
from time import sleep
from selenium.common.exceptions import TimeoutException, ElementNotVisibleException, NoSuchElementException, StaleElementReferenceException
from math import ceil


def coin_transfer_prep(obj, amount):
    def add_player(player_to_search):
        rating = None
        quality = 'Special'
        search_panel = obj.__get_class__('ClubSearchFilters', as_list=False)
        sleep(Global.micro_min / 2)
        name_list = []
        if type(player_to_search) is int or (type(player_to_search) is str and any(n in player_to_search for n in '1234567890')):
            have_id = True
            if int(player_to_search) >= 300000:
                quality = 'Special'
            try:
                db_player = Global.fifa_players[player_to_search]
            except KeyError:
                try:
                    player_to_search =  info.get_base_id(player_to_search)
                    db_player = Global.fifa_players[player_to_search]
                except KeyError:
                    multi_log(obj, 'No player with id {} in fifa_players.json, Unable to find player'.format(player_to_search), level='error')
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
        if quality is not None:
            quality = quality.title()
            quality_dropdown = search_panel.find_element_by_xpath(".//*[contains(text(), 'Quality')]")
            obj.__click_element__(quality_dropdown)
            sleep(5)
            quality_parent = quality_dropdown.find_element_by_xpath('..')
            obj.__check_for_errors__()
            quality_parent.find_element_by_xpath(".//*[contains(text(), '{}')]".format(quality)).click()
        else:
            try:
                obj.__click_element__(search_panel.find_element_by_xpath('.//div[3]/div[2]/div[3]/div/a'))  # Remove quality filter
            except ElementNotVisibleException:
                pass
        obj.__click_element__(search_panel.find_element_by_xpath('.//div[3]/div[2]/div[4]/div/a'))  # Remove position filter
        obj.__click_element__(search_panel.find_element_by_xpath(".//*[contains(text(), 'Search')]"))
        sleep(Global.small_min)
        results = obj.__get_class__('MyClubResults', as_list=False)
        if not results:
            multi_log(obj, 'Missing {} for SBC solution'.format(info.get_player_info(player_to_search, False)['name']))
            return False
        try:
            results.find_element_by_class_name('has-action').click()
            obj.__click_xpath__(".//*[contains(text(), 'Swap Player')]")
            return True
        except (TimeoutException, ElementNotVisibleException, NoSuchElementException):
            pass
        multi_log(obj, 'Missing {} for coin transfer'.format(info.get_player_info(player_to_search, False)['name']))
        return False

    multi_log(obj, 'Prepping for Coin Transfer...', level='title')
    # Get cheap gold IFs that aren't 0
    multi_log(obj, 'Finding best players to purchase for coin transfer...')
    if 'pc' in obj.platform:
        platform = 'pc'
    elif 'xbox' in obj.platform:
        platform = 'xbox'
    else:
        platform = 'ps'
    futbin_url = 'https://www.futbin.com/18/players?page=1&version=if_gold&sort={}_price&order=asc'.format(platform)
    all_results = []
    # Get enough players to reach amount
    players_needed = ceil(amount / 35000)
    obj.new_tab(futbin_url)
    obj.location = 'futbin'
    results = parse_futbin_players_table(obj, futbin_url, all_results)[0:players_needed - 1]
    obj.close_tab()
    obj.driver.switch_to.window(obj.driver.window_handles[0])
    obj.location = 'home'
    multi_log(obj, 'Done finding players. Acquiring...')
    players_needed = []
    for player in results:
        if int(player['asset_id']) < 300000:
            special_ids = list(get_special_ids(player['asset_id']).values())
            good_ids = [int(i) for i in special_ids if int(i) > 300000]
            player['asset_id'] = str(min(good_ids))
        players_needed.append(player['asset_id'])
    # Acquire players
    result = obj.acquire(players_needed, 1, False, special_only=True)
    if result == 'done':
        # Put players into a squad
        multi_log(obj, 'Putting players into squad...')
        obj.go_to('squads')
        obj.__click_xpath__("//*[contains(text(), 'Squad Management')]")
        obj.location = 'squad_management'
        squads = obj.__get_class__('listFUTSquad', as_list=True)
        squad_exists = False
        for squad in squads:
            if squad.find_element_by_tag_name('h1').text.lower() == 'ignore me':
                obj.__click_element__(squad)
                sleep(Global.micro_max)
                side_panel = obj.__get_class__('squadDetailView', as_list=False)
                side_panel.find_element_by_xpath("//*[contains(text(), 'Open')]").click()
                squad_exists = True
                break
        if not squad_exists:
            obj.__click_xpath__("//*[contains(text(), 'Create New Squad')]")
            text_box = obj.__get_class__('textInput', as_list=False)
            obj.__type_element__(text_box, 'Ignore Me')
            obj.__click_xpath__("//*[contains(text(), 'Create')]")
        sleep(Global.micro_max)
        players_added = 0
        ignore = []
        while True and players_added < len(players_needed):
            all_full = True
            squad_pitch = obj.__get_class__('squadPitch', as_list=False)
            squad_slots = squad_pitch.find_elements_by_class_name('squadSlot')
            for slot in reversed(squad_slots):
                index = slot.get_attribute('index')
                try:
                    if 'locked' not in slot.get_attribute('class') and 'empty' in slot.find_element_by_class_name('player').get_attribute('class') and index not in ignore:
                        all_full = False
                        slot.click()
                        sleep(Global.micro_min)
                        panel = obj.__get_class__('ui-layout-right', as_list=False)
                        obj.__click_element__(panel.find_element_by_xpath("//*[contains(text(), 'Add Player')]"))
                        sleep(Global.micro_min)
                        add_result = add_player(players_needed[players_added])
                        players_added += 1
                        if not add_result or add_result == 'no_name':
                            ignore.append(index)
                        break
                except NoSuchElementException:
                    pass
            if all_full:
                break
    multi_log(obj, 'Done adding players to squad. Play a game with them before selling (less risky)')