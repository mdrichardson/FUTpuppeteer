from FUTpuppeteer import parse, info
from FUTpuppeteer.misc import multi_log, Global
from . import retry_decorator, common_wait_to_expire, common_hunt
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from time import sleep
from ruamel.yaml import YAML

yaml = YAML()
yaml.explicit_start = True
yaml.indent(mapping=4)
yaml.preserve_quotes = True
need_relisting = False


@retry_decorator
def sbc_hunt(obj):
    obj.current_strategy = 'SBC Hunt'
    temp_settings = obj.strategy_settings['sbc_hunt']
    max_iterations = temp_settings['max_iterations']
    min_price = temp_settings['min_price']
    max_price = temp_settings['max_price']
    only_new = temp_settings['only_new']
    solutions_per_challenge = temp_settings['solutions_per_challenge']
    refresh_players = temp_settings['refresh_players']
    max_players = temp_settings['max_players']
    remove_keys = ['max_iterations', 'min_price', 'max_price', 'only_new', 'refresh_players', 'players', 'solutions_per_challenge', 'max_players']
    settings = {k: v for k, v in temp_settings.items() if k not in remove_keys}
    multi_log(obj, 'SBC Hunting...', level='title')
    if refresh_players:
        all_players = []

        def remove_cookie_warning():
            sleep(Global.micro_max)
            script = "var elements=document.getElementsByClassName('cc_container');while(elements.length>0){elements[0].parentNode.removeChild(elements[0]);};"
            obj.driver.execute_script(script)

        def get_players():
            player_cards = obj.__get_class__('cardetails')
            sbc_solution_players = []
            for card in player_cards:
                try:
                    sbc_icon = card.find_element_by_class_name('sbc-alternatives')
                    if 'display: none' in sbc_icon.get_attribute('style'):
                        card_details = card.find_element_by_class_name('pcdisplay')
                        sbc_player_id = card_details.get_attribute('data-resource-id')
                        if platform == 'ps':
                            sbc_player_price = card_details.get_attribute('data-price-ps3')
                        elif platform == 'pc':
                            sbc_player_price = card_details.get_attribute('data-price-pc')
                        else:
                            sbc_player_price = card_details.get_attribute('data-price-xbl')
                        sbc_player_price = parse.price_parse(sbc_player_price)
                        if type(sbc_player_price) is not int:
                            sbc_player_price = 0
                        sbc_solution_players.append({
                            'asset_id': sbc_player_id,
                            'price': sbc_player_price
                        })
                except NoSuchElementException:
                    pass
            return sbc_solution_players

        if 'pc' in obj.platform:
            platform = 'pc'
        elif 'xbox' in obj.platform:
            platform = 'xbox'
        else:
            platform = 'ps'
        futbin_url = 'https://www.futbin.com/squad-building-challenges'
        multi_log(obj, 'Getting players from SBC challenges...')
        obj.driver.get(futbin_url)
        obj.location = 'futbin'
        remove_cookie_warning()
        if only_new:
            try:
                sets = obj.__get_class__('round-star-label')
            except TimeoutException:
                multi_log(obj, message='No new sets found')
                obj.__login__()
                return
        else:
            sets = obj.__get_class__('set_name')
        set_links = []
        for sbc in sets:
            gp = sbc.find_element_by_xpath('../..')
            set_name = gp.find_element_by_class_name('set_name').text.lower()
            if 'loan' not in set_name:
                set_column = gp.find_element_by_xpath('../../..')
                set_link = set_column.find_element_by_tag_name('a').get_attribute('href')
                set_links.append(set_link)
        for s_link in set_links:
            if len(all_players) >= max_players:
                break
            obj.new_tab(s_link)
            chal_links = []
            chal_names = obj.__get_class__('chal_name')
            for chal in chal_names:
                if len(all_players) >= max_players:
                    break
                chal_column = chal.find_element_by_xpath('../..')
                chal_link = chal_column.find_element_by_xpath(".//*[contains(text(), 'Completed Challenges')]").get_attribute('href')
                chal_links.append(chal_link)
            for c_link in chal_links:
                if len(all_players) >= max_players:
                    break
                obj.new_tab(c_link)
                remove_cookie_warning()
                # Get cheapest solution
                solutions = []
                relevant_price = '{}_price'.format(platform)
                remove_cookie_warning()
                table = obj.__get_class__('chal_table', as_list=False)
                for row in table.find_elements_by_xpath('.//tr'):
                    if 'thead_des' != row.get_attribute('class'):
                        data = row.find_elements_by_xpath('.//td')
                        if data:
                            try:
                                solution = {
                                    'ps_price': parse.price_parse(data[5].text),
                                    'xbox_price': parse.price_parse(data[6].text),
                                    'pc_price': parse.price_parse(data[7].text)
                                }
                                if solution[relevant_price] <= max_price * 11 * 3:
                                    solutions.append([solution, row, data[1].text, int(data[9].text), int(data[10].text)])
                            except IndexError:
                                continue
                if len(solutions) == 0:
                    multi_log(obj, 'No good solutions found. Skipping...', level='warn')
                else:
                    sorted_solutions = sorted(solutions, key=lambda s: s[0][relevant_price])

                    for cheap in sorted_solutions[0:solutions_per_challenge + 1]:
                        try:
                            cheap_url = cheap[1].find_element_by_class_name('squad_url').get_attribute('href')
                            obj.new_tab(cheap_url)
                        except WebDriverException:
                            break
                        solution_players = get_players()
                        for player in solution_players:
                            if min_price <= player['price'] <= max_price and player['asset_id'] not in all_players and len(all_players) < max_players:
                                all_players.append(player['asset_id'])
                        with open(obj.config_file) as config:
                            new_config = yaml.load(config)
                            new_config['strategy_settings']['sbc_hunt']['players'] = all_players
                        with open(obj.config_file, 'w') as update:
                            yaml.dump(new_config, update)
                        obj.close_tab()
                obj.close_tab()
            obj.close_tab()
        obj.__login__()
    else:
        with open(obj.config_file) as config:
            old_config = yaml.load(config)
            all_players = old_config['strategy_settings']['sbc_hunt']['players']
    multi_log(obj, 'Amassing SBC players...', level='header')
    total_bids = 0
    # Search and bid
    i = 0
    while i < max_iterations:
        for player in all_players:
            player_name = info.get_player_info(player, include_futbin_price=False)['name']
            hunt_criteria = {
                'search_type': 'Players',
                'player': player,
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
            num_bids = common_hunt(obj=obj, name=player_name, hunt_criteria=hunt_criteria, strategy='sbc_hunt', **settings)
            if num_bids == 'limit':
                common_wait_to_expire(obj=obj, strategy='sbc_hunt')
            else:
                total_bids += num_bids
        i += 1
    if total_bids > 0:
        common_wait_to_expire(obj=obj, strategy='sbc_hunt')





