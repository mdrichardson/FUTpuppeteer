import json
import logging
from logging.handlers import RotatingFileHandler
from colorama import Fore, Style
from ruamel.yaml import YAML
from . import parse

yaml = YAML()
yaml.explicit_start = True
yaml.indent(mapping=4)
yaml.preserve_quotes = True
need_relisting = False


class Global:
    with open('config/global.yml', 'r') as stream:
        global_config = yaml.load(stream)
    lag_multiplier = global_config['delays']['lag_multiplier']
    huge_max = global_config['delays']['huge_max'] * lag_multiplier
    huge_min = global_config['delays']['huge_min'] * lag_multiplier
    large_max = global_config['delays']['large_max'] * lag_multiplier
    large_min = global_config['delays']['large_min'] * lag_multiplier
    med_max = global_config['delays']['med_max'] * lag_multiplier
    med_min = global_config['delays']['med_min'] * lag_multiplier
    micro_max = global_config['delays']['micro_max'] * lag_multiplier
    micro_min = global_config['delays']['micro_min'] * lag_multiplier
    small_max = global_config['delays']['small_max'] * lag_multiplier
    small_min = global_config['delays']['small_min'] * lag_multiplier

    autoremote_device_names = global_config['notifications']['autoremote_device_names']
    autoremote_key = global_config['notifications']['autoremote_key']
    autoremote_notifications = global_config['notifications']['autoremote_notifications']
    desktop_notifications = global_config['notifications']['desktop_notifications']

    path_to_chromedriver_exe = global_config['path_to_chromedriver_exe']

    use_database = global_config['use_database']

    rounding_tiers = {
        '0000to0001': 50,
        '0001to0005': 100,
        '0005to0010': 100,
        '0010to0030': 250,
        '0030to0050': 250,
        '0050to0100': 500,
        '0100to0250': 500,
        '0250to0500': 1000,
        '0500to2000': 1000,
        '2000plus': 1000,
        }
    ###################################################
    # Load EA Database
    ###################################################
    with open('data/fifa_nations.json', encoding='utf-8') as nations_db:
        fifa_nations = json.load(nations_db, parse_int=str)
    with open('data/fifa_leagues.json', encoding='utf-8') as leagues_db:
        fifa_leagues = json.load(leagues_db, parse_int=str)
    with open('data/fifa_clubs.json', encoding='utf-8') as teams_db:
        fifa_clubs = json.load(teams_db, parse_int=str)
    with open('data/fifa_stadiums.json', encoding='utf-8') as stadiums_db:
        fifa_stadiums = json.load(stadiums_db, parse_int=str)
    with open('data/fifa_balls.json', encoding='utf-8') as balls_db:
        fifa_balls = json.load(balls_db, parse_int=str)
    with open('data/fifa_play_styles.json', encoding='utf-8') as play_styles_db:
        fifa_play_styles = json.load(play_styles_db, parse_int=str)
    with open('data/fifa_players.json', encoding='utf-8') as players_db:
        fifa_players = json.load(players_db, parse_int=str)

# TODO: Write '{}' if json decode error


###################################################
#
# Logging
#
###################################################
class Colors:
    bold = Style.BRIGHT
    green = Fore.GREEN
    red = Fore.RED + Style.BRIGHT
    yellow = Fore.YELLOW
    reset = Style.RESET_ALL


log = logging.getLogger('logging')
log_file_handler = RotatingFileHandler('logs/FUTpuppeteer.log', mode='a', maxBytes=5*1024*1024, encoding=None, delay=0)
log.addHandler(log_file_handler)
log_file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))


def multi_log(obj=None, message=None, level='info', notify=False, title='FUTpuppeteer Notification', icon_url='http://www.futwiz.com/assets/img/fifa18/badges/888888.png',
              link=None):
    message = parse.remove_accents(message)
    if obj:
        message = 'Bot{}: {}'.format(obj.bot_number, message)
        obj.last_console = message
    if notify:
        try:
            if level in ['crit', 'error'] and icon_url == 'http://www.futwiz.com/assets/img/fifa18/badges/888888.png':
                icon_url = 'https://cdn0.iconfinder.com/data/icons/small-n-flat/24/678069-sign-error-256.png'
            elif level == 'warn' and icon_url == 'http://www.futwiz.com/assets/img/fifa18/badges/888888.png':
                icon_url = 'http://www.i2clipart.com/cliparts/b/d/6/8/clipart-warning-icon-bd68.png'
            elif level == 'green' and icon_url == 'http://www.futwiz.com/assets/img/fifa18/badges/888888.png':
                icon_url = 'http://i.imgur.com/Tx1OaEq.png'
            if level in ['info', 'debug', 'green']:
                obj.notify_desktop(title=title, message=message, icon_url=icon_url, link=link)
            else:
                obj.notify_all(title=title, message=message, icon_url=icon_url, link=link)
        except AttributeError:
            pass
    if level == 'header':
        message = message.upper()
        log.debug(message)
        formatted_message = Colors.bold + message + Colors.reset
        print(formatted_message)
    elif level == 'debug':
        log.debug(message)
    elif level == 'info':
        log.info(message)
        print(message)
    elif level == 'warn':
        log.warning(message)
        formatted_message = Colors.yellow + message + Colors.reset
        print(formatted_message)
    elif level == 'error':
        log.critical(message)
        formatted_message = Colors.red + message + Colors.reset
        print(formatted_message)
    elif level == 'crit':
        log.critical(message)
        formatted_message = Colors.red + 'ERROR: ' + message + Colors.reset
        print(formatted_message)
    elif level == 'green':
        log.info(message)
        formatted_message = Colors.green + message + Colors.reset
        print(formatted_message)
    elif level == 'yellow':
        log.info(message)
        formatted_message = Colors.yellow + message + Colors.reset
        print(formatted_message)
    elif level == 'title':
        log.info(message)
        formatted_message = '##   ' + Colors.bold + message + Colors.reset
        print('#' * 80)
        print('##')
        print(formatted_message)
        print('##')
        print('#' * 80)
    else:
        print('ERROR: WRONG LOG LEVEL')
