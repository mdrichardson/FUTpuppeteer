from . import parse, info
from .misc import Global,  multi_log
from time import sleep
from selenium.common.exceptions import TimeoutException, ElementNotVisibleException, NoSuchElementException, StaleElementReferenceException


def solve_sbc(obj, futbin_link, futbin_multiplier=0.98, increase_each_round=True, max_increases=5, exclude=None):
    def add_player(player_to_search):
        rating = None
        quality = None
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
                multi_log(obj, 'No player with id {} in fifa_players.json'.format(player_to_search), level='error')
                try:
                    player_to_search =  info.get_base_id(player_to_search)
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
        multi_log(obj, 'Missing {} for SBC solution'.format(info.get_player_info(player_to_search, False)['name']))
        return False

    def finish_solution():
        def fill_slots():
            ignore = []
            while True:
                all_full = True
                squad_pitch = obj.__get_class__('squadPitch', as_list=False)
                squad_slots = squad_pitch.find_elements_by_class_name('squadSlot')
                for slot in reversed(squad_slots):
                    index = slot.get_attribute('index')
                    if 'locked' not in slot.get_attribute('class') and 'empty' in slot.find_element_by_class_name('player').get_attribute('class') and index not in ignore:
                        all_full = False
                        position = slot.find_element_by_class_name('label').text.lower()
                        requirements = obj.__get_class__('progress-container', as_list=False)
                        if 'checked' in requirements.get_attribute('class'):
                            requirements.click()
                        slot.click()
                        sleep(Global.micro_min)
                        panel = obj.__get_class__('ui-layout-right', as_list=False)
                        obj.__click_element__(panel.find_element_by_xpath("//*[contains(text(), 'Add Player')]"))
                        sleep(Global.micro_min)
                        for solution_player in solution:
                            if solution_player[1] == position:
                                add_result = add_player(solution_player[0])
                                solution.remove(solution_player)
                                if not add_result or add_result == 'no_name':
                                    ignore.append(index)
                                break
                        break
                if all_full:
                    break

        obj.location = challenge
        sleep(Global.micro_max)
        obj.__disable_click_shield__()
        obj.rate_limit()
        try:
            obj.__click_element__(obj.__get_class__('call-to-action', as_list=False))
        except (TimeoutException, ElementNotVisibleException, NoSuchElementException):
            pass
        obj.__disable_click_shield__()
        try:
            requirements = obj.__get_class__('progress-container', as_list=False)
            if 'checked' in requirements.get_attribute('class'):
                requirements.click()
                sleep(Global.micro_min)
        except (TimeoutException, NoSuchElementException, ElementNotVisibleException):
            pass
        fill_slots()


    def find_set():
        obj.location = set_name
        script = "var headers=document.querySelectorAll('.tileHeader');for(var i=0;i<headers.length;i++){headers[i].style.textTransform='None'}"
        obj.driver.execute_script(script)
        sleep(Global.small_max)
        obj.rate_limit()
        try:
            challenge_headers = obj.__get_class__('tileTitle')
            challenge_pairs = []
            for challenge_header in challenge_headers:
                challenge_pairs.append([parse.remove_accents(challenge_header.text.lower()), challenge_header])
            got_challenge = False
            for chal in challenge_pairs:
                if chal[0] in challenge:
                    got_challenge = True
                    obj.__disable_click_shield__()
                    g_parent = chal[1].find_element_by_xpath('../..')
                    g_parent.click()
                    sleep(Global.small_min)
                    finish_solution()
                    break
        except TimeoutException:
            got_challenge = False
            pass
        if not got_challenge:
            multi_log(obj, 'Something went wrong. Please navigate to the approprate challenge for {} and press Enter'.format(challenge.title()), notify=True,
                      title='SBC Error')
            obj.wait_for_enter()
            finish_solution()

    # Get Futbin Solution
    if '?analyze=1' not in futbin_link:
        futbin_link = futbin_link + '?analyze=1'
    obj.new_tab(futbin_link)
    obj.futbin_login(futbin_link)
    obj.location = 'futbin'
    sleep(Global.med_min)
    header = obj.__get_class__('header_mid_text', as_list=False)
    set_name = parse.remove_accents(header.find_element_by_xpath('./span[3]/a').text).lower()
    challenge = parse.remove_accents(header.find_element_by_xpath('./span[5]/a').text.lower().split(' simulator')[0]).lower()
    multi_log(obj, 'Getting Futbin SBC solution for {} / {}'.format(set_name.title(), challenge.title()), level='header')
    multi_log(obj, 'Solution URL: {}'.format(futbin_link))
    solution_area = obj.driver.find_element_by_id('area')
    players = solution_area.find_elements_by_class_name('card')
    solution = []
    just_players = []
    for player in players:
        classes = player.get_attribute('class')
        try:
            overlays = player.find_element_by_class_name('overlay-card').get_attribute('class')
        except NoSuchElementException:
            overlays = []
        if 'droppable' in classes:
            image_div = player.find_element_by_class_name('pcdisplay-picture')
            player_info = player.find_element_by_class_name('pcdisplay')
            quality_classes = player_info.get_attribute('class')
            if any(s in quality_classes for s in ['futmas', 'sbc', 'award-winner', 'icon', 'sbc_premium', 'if', 'toty', 'otw', 'halloween', 'purple', 'marquee', 'promo']):
                player_id = player_info.get_attribute('data-resource-id')
            else:
                player_id = image_div.find_element_by_tag_name('img').get_attribute('src').split('/')[-1].split('.')[0].replace('p', '')
            position = player.get_attribute('data-formpos').lower()
            solution.append((player_id, position))
            if 'green' not in overlays and player_id not in exclude:
                just_players.append(player_id)
    # Acquire players
    multi_log(obj, 'Done getting solution information')
    obj.driver.switch_to.window(obj.driver.window_handles[0])
    obj.location = 'home'
    if 'all' not in exclude:
        result = obj.acquire(just_players, futbin_multiplier, increase_each_round, max_increases)
    else:
        result = 'done'
        obj.keep_alive(Global.small_min)
    if result == 'done':
        multi_log(obj, 'Putting players into solution...')
        obj.check_unassigned()
        if obj.location != 'sbc':
            obj.go_to('sbc')
        script = "var headers=document.querySelectorAll('.tileHeader');for(var i=0;i<headers.length;i++){headers[i].style.textTransform='None'}"
        obj.driver.execute_script(script)
        sleep(Global.micro_max)
        obj.rate_limit()
        tile_headers = obj.__get_class__('tileHeader')  # Must get actual tile headers due to removing accented characters
        header_pairs = []
        for header in tile_headers:
            header_pairs.append([parse.remove_accents(header.text), header])
        got_set = False
        for header_pair in header_pairs:
            if parse.remove_accents(header_pair[0]).lower() in set_name:
                got_set = True
                obj.__disable_click_shield__()
                header_pair[1].click()
                find_set()
                break
        if not got_set:
            multi_log(obj, 'Something went wrong. Please navigate to the approprate set for {} and press Enter'.format(set_name.title()), notify=True,
                      title='SBC Error', level='error')
            obj.wait_for_enter()
            find_set()
        multi_log(obj, 'Ensure solution looks correct, then submit and claim the reward', level='green', notify=True, title='SBC Solved!', icon_url='http://futhead.cursecdn.com/static/img/sbc/17/logo.png')
        multi_log(obj, 'Note: You may need to leave the SBCs page then come back for chemistry/rating to work. Bot may have also added wrong player with similar name or a club transfer')
        multi_log(obj, 'MAKE SURE IT DIDN\'T USE A SPECIAL CARD IF IT SHOULD\'T HAVE', level='warn')
        obj.__focus__()
        obj.wait_for_enter()
        multi_log(obj, 'Marking challenge completed in Futbin')
        handles = obj.driver.window_handles
        try:
            for i, window in enumerate(handles):
                if window != obj.driver.window_handles[0]:
                    obj.driver.switch_to.window(obj.driver.window_handles[i])
                    obj.close_tab()
        except IndexError:
            pass
        obj.driver.switch_to.window(obj.driver.window_handles[0])
        obj.new_tab(futbin_link)
        obj.futbin_login(futbin_link)
        obj.location = 'futbin'
        header = obj.__get_class__('header_mid_text', as_list=False)
        link = header.find_element_by_xpath('//span[3]/a').get_attribute('href')
        obj.driver.get(link)
        sleep(Global.small_min)
        challenges = obj.__get_class__('chal_name')
        for chal in challenges:
            if chal.text.lower() == challenge:
                ggg_parent = chal.find_element_by_xpath('../../..')
                button = ggg_parent.find_element_by_class_name('mark-completed-challenge')
                button.click()
                obj.driver.execute_script("arguments[0].click()", button)
                sleep(Global.small_max)
                break
        handles = obj.driver.window_handles
        try:
            for i, window in enumerate(handles):
                if window != obj.driver.window_handles[0]:
                    obj.driver.switch_to.window(obj.driver.window_handles[i])
                    obj.close_tab()
        except IndexError:
            pass
        obj.driver.switch_to.window(obj.driver.window_handles[0])
