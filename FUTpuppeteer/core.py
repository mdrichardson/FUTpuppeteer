# -*- coding: utf-8 -*-
"""
FUTpuppeteer.core
~~~~~~~~~~~~~~~~~~~~~
This module implements the puppetSniper's basic methods.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import *
import sys
import logging
from random import uniform as rand
from . import actions, info, notifications, parse, sbc, database
from FUTpuppeteer.strategies import bpm, snipe, futbin_market, sell_club_players, continual_relist, hunt, filter_snipe, acquire, amass, sbc_hunt, \
    sell_transfer_targets_at_market, housekeeping, futbin_cheapest_sbc, relist_individually, price_fix, market_monitor, arbitrage, silver_flip, filter_finder, \
    filter_amass, coin_transfer_list, consumable_amass, check_unlock, common_deal_with_full_transfer_list, coin_transfer_prep
from .misc import multi_log, log, Global
import os
import subprocess
from time import sleep, time
from datetime import datetime, timedelta
from ruamel.yaml import YAML
import psutil
import signal
import keyring
from simplecrypt import encrypt, decrypt
from binascii import hexlify, unhexlify

yaml = YAML()
yaml.explicit_start = True
yaml.indent(mapping=4)
yaml.preserve_quotes = True

url = 'https://www.easports.com/fifa/ultimate-team/web-app/'


###################################################
#
# SESSION CLASS
#
###################################################
class Session(object):
    # noinspection PyBroadException
    def __init__(self, config_file='', proxy=None, bot_number=1, delay_login=False, debug=False, headless=False, disable_extensions=False):
        """
        Creates bot object and logs it in.
        :param config_file: str: *.yml
        :param proxy: str: proxy IP address
        :param bot_number: int: for use with multiple bots
        :param delay_login: bool: might want to set to True if first scraping Futbin or something. Just remember to log back in later
        :param debug: bool: set to True to enable more verbose logging in FUTpuppeteer.log
        """
        # Set bot variables
        self.headless = headless
        self.platform = ''
        self.credits = 0
        self.logged_in = False
        self.location = 'logged out'
        self.current_tradepile_size = 0
        self.url = url
        self.last_action_time = datetime.now() - timedelta(days=1)
        self.per_second_count = 0
        self.immediate_count = 0
        self.current_strategy = 'Logging In...'
        self.last_console = ''
        self.bot_number = bot_number
        self.userdir = '{}/bot{}'.format('/'.join(Global.path_to_chromedriver_exe.split('/')[:-1]), self.bot_number)
        self.last_sleep = datetime.now()
        self.active = False
        # Get current chromedriver PID so we can force-close the new one (this one) as needed
        pids = []
        for process in psutil.process_iter():
            if 'chromedriver' in process.name():
                pids.append(process.pid)
        # Remove "Chrome didn't shut down..." from startup
        try:
            with open('{}/Default/Preferences'.format(self.userdir), 'r') as user_prefs:
                prefs_change = user_prefs.read()
            prefs_change = prefs_change.replace('Crashed', 'Normal')
            with open('{}/Default/Preferences'.format(self.userdir), 'w') as user_prefs:
                user_prefs.write(prefs_change)
        except FileNotFoundError:
            pass
        # Load appropriate config file
        if not config_file:
            config_file = 'bot{}.yml'.format(bot_number)
        if 'config/' not in config_file:
            config_file = 'config/' + config_file
        if '' not in config_file:
            config_file = '' + config_file
        self.config_file = config_file
        info.set_config_variables(self)
        # Check for user account settings. Get them, if they don't exist
        # noinspection PyUnresolvedReferences
        self.__get_user_info__()
        if not self.user.get('password') or self.user['re-enter_user_settings']:
            self.__save_user_info__()
            info.set_config_variables(self)
            self.__get_user_info__()
        if debug:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)
        self.proxy = proxy
        # Load bot settings
        # Prep for multiple instances
        try:
            self.grid_path = '/'.join(Global.path_to_chromedriver_exe.split('/')[:-1])
            subprocess.check_call(['java -jar {}/selenium-server-standalone-3.8.1.jar -role hub'.format(self.grid_path)], stdout=subprocess.DEVNULL,
                                  stderr=subprocess.STDOUT, shell=True)
            subprocess.check_call(['java -jar {}/selenium-server-standalone-3.8.1.jar -role node  -hub http://localhost:4444/grid/register'.format(self.grid_path)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError:
            pass
        # Prep bot chromedriver
        while True:
            try:
                self.opts = Options()
                self.opts.add_argument('--user-data-dir={}'.format(self.userdir))
                self.opts.add_argument('--disable-infobars')
                self.opts.add_argument('--disable-plugins-discovery')
                self.opts.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')
                self.opts.add_argument('--window-size=1024,768')
                self.opts.add_argument('--disable-offline-auto-reload-visible-only')
                self.opts.add_argument('--allow-http-background-page')
                # self.opts.add_argument('--no-sandbox')
                if disable_extensions:
                    self.opts.add_argument('--disable-extensions')
                if headless:
                    pass
                    # self.opts.add_argument('--headless')
                    # self.opts.add_argument('--disable-gpu')
                if self.proxy:
                    self.opts.add_argument("--proxy-server={0}".format(self.proxy))
                # Install chrome extensions if they don't exist
                if not disable_extensions:
                    ublock = 'cjpalhdlnbpafiamejdnhcphjbkeiagm'
                    futbin = 'adicaaffkmhgnfheifkjhopmambgfihl'
                    if not os.path.exists(self.userdir + '/Default/Extensions/' + ublock):
                        multi_log(self, 'Installing ublock extension...', level='debug')
                        self.opts.add_extension('extensions/ublock.crx')
                    if not os.path.exists(self.userdir + '/Default/Extensions/' + futbin):
                        multi_log(self, 'Installing futbin extension...', level='debug')
                        self.opts.add_extension('extensions/futbin.crx')
                self.driver = webdriver.Chrome(executable_path=Global.path_to_chromedriver_exe, chrome_options=self.opts)
                if headless:
                    self.driver.set_window_position(-10000, 0)
                break
            except WebDriverException as e:
                multi_log(self, e, level='error', notify=False)
                multi_log(self, 'Failed to start: {}'.format(e), level='error')
                if 'failed to start' in str(e).lower():
                    raise Exception('Please close all windows for this bot before trying again. You may need to close out of ALL chrome instances to continue')
                self.keep_alive(5)
        if not delay_login:
            self.__login__()
        # Get this chromedriver PID so we can force-close it as needed
        self.pid = []
        for process in psutil.process_iter():
            if 'chromedriver' in process.name() and process.pid not in pids and time() - process.create_time() < 100:
                self.pid.append(process.pid)
        with open(self.config_file) as config:
            new_config = yaml.load(config)
            new_config['pid'] = self.pid
        with open(self.config_file, 'w') as update:
            yaml.dump(new_config, update)

    #############################
    #       GET AND STORE USER INFO
    #############################
    def __save_user_info__(self):
        # Load current config
        with open(self.config_file) as config:
            new_config = yaml.load(config)
        print('This bot needs to collect your user information. '
              'You can choose how securely to store your passwords')
        print('1. SECURE - Passwords are encrypted, but a master password must be entered every time the bot starts')
        print('2. SEMI-SECURE - Passwords are stored in your OS\'s credential manager. Any program run under your OS user account can access them, '
              'but you only ever have to enter them once.')
        while True:
            security = input('Choose 1 for SECURE or 2 for SEMI-SECURE: ')
            if str(security) == '1' or str(security) == '2':
                break
            else:
                print(security + ' was not an option. Please choose 1 for SECURE or 2 for SEMI-SECURE')
        # Only ask for necessary information. Ask for passwords and secrets, regardless. Replace input() with getpass() if you want to hide the input
        if not self.user['email']:
            ea_email = input('EA Email address: ')
            new_config['user']['email'] = ea_email
        ea_password = input('EA Password: ')
        ea_secret = input('EA secret: ')
        print('Do you want to use IMAP? This allows the bot to auto-enter your emailed 2-factor authentication code')
        while True:
            imap_choice = input('Y/N: ')
            if imap_choice.lower() == 'y':
                if not self.user['imap_email']:
                    imap_email = input('YOUR Email Address: ')
                    new_config['user']['imap_email'] = imap_email
                imap_password = input('YOUR Email Password: ')
                if not self.user['imap_server']:
                    imap_server = input('IMAP Server (imap.gmail.com for gmail): ')
                    new_config['user']['imap_server'] = imap_server
                break
            else:
                print(imap_choice + ' was not an option. Please choose Y to use IMAP or N to not use IMAP')
        if str(security) == '1':
            # Ask for master password and encrypt passwords
            print('Set a master password. It cannot be equal to any of your passwords or secrets. DON\'T FORGET IT')
            while True:
                master_password = input('Set Master Password: ')
                if master_password not in [ea_password, ea_secret, imap_password]:
                    break
                else:
                    print('Your master password CANNOT be the same as your EA Password, EA Secret, or IMAP Password')
        # We have to encode->hexlify->decode because encrypt creates bytes and keyring stores non-utf-8 string and we'll need to be able to convert later
            imap_password = hexlify(encrypt(master_password, imap_password.encode('utf-8'))).decode()
            ea_password = hexlify(encrypt(master_password, ea_password.encode('utf-8'))).decode()
            ea_secret = hexlify(encrypt(master_password, ea_secret.encode('utf-8'))).decode()
            new_config['user']['secure_passwords'] = True
        else:
            new_config['user']['secure_passwords'] = False
        # Store passwords and secrets in the keyring
        keyring.set_password('FUTpuppeteer_{}'.format(self.bot_number), 'imap_password', imap_password)
        keyring.set_password('FUTpuppeteer_{}'.format(self.bot_number), 'ea_password', ea_password)
        keyring.set_password('FUTpuppeteer_{}'.format(self.bot_number), 'ea_secret', ea_secret)
    # Write user info to config. Add option to re-enter user settings if needed
        new_config['user']['re-enter_user_settings'] = False
        with open(self.config_file, 'w') as update:
            yaml.dump(new_config, update)

    def __get_user_info__(self):
        if self.user.get('password', None) or not self.user['re-enter_user_settings']:
            # Get the info from OS credential manager
            ea_password = keyring.get_password('FUTpuppeteer_{}'.format(self.bot_number), 'ea_password')
            ea_secret = keyring.get_password('FUTpuppeteer_{}'.format(self.bot_number), 'ea_secret')
            imap_password = keyring.get_password('FUTpuppeteer_{}'.format(self.bot_number), 'imap_password')
            # Decrypt if they're encrypted
            if self.user['secure_passwords']:
                master_password = input('Enter Master Password: ')
                # We have to encode->unhexlify->decode because decrypt requires bytes and keyring uses string
                ea_password = decrypt(master_password, unhexlify(ea_password.encode())).decode('utf-8')
                ea_secret = decrypt(master_password, unhexlify(ea_secret.encode())).decode('utf-8')
                imap_password = decrypt(master_password, unhexlify(imap_password.encode())).decode('utf-8')
            # Store them in the Session Object so we can use them
            self.user['password'] = ea_password
            self.user['secret_answer'] = ea_secret
            self.user['imap_password'] = imap_password

    #############################
    #       LOGIN
    #############################
    def __login__(self): # TODO: Figure out how to force login if it takes too long
        self.credits = 0
        self.driver.get(url)
        print("Pausing so you can record\n\n\n\n\n\n\n\n")
        sleep(10) # REMOVE AFTER VIDEO RECORDING
        # See if it auto-logs-in
        self.logged_in = False
        multi_log(self, 'Logging in...', level='info')
        login_tries = 0
        while not self.logged_in:
            login_tries += 1
            if login_tries > 10:
                self.driver.get(url)
                login_tries = 0
            progress = self.__login_progress__()
            # Check if user/pass is needed
            if progress == 'ea_account':
                multi_log(self, 'Attempting User/Pass...', level='debug')
                try:
                    # noinspection PyUnresolvedReferences,PyUnresolvedReferences
                    self.__type_xpath__('//*[@id="email"]', self.user['email'], Global.micro_min)
                except TimeoutException:
                    pass
                try:
                    # noinspection PyUnresolvedReferences
                    self.__type_xpath__('//*[@id="password"]', self.user['password'], Global.micro_min)
                    multi_log(self, 'Entering user/pass...', level='debug')
                    self.__click_xpath__('//*[@id="btnLogin"]', Global.micro_min)
                except TimeoutException:
                    multi_log(self, 'No user/pass needed', level='debug')
            # Check if 2-factor code is needed
            elif progress == 'send_code':
                try:
                    multi_log(self, 'Attempting 2-factor...', level='debug')
                    self.__click_xpath__('//*[@id="btnSendCode"]', Global.micro_min)
                    multi_log(self, 'Requesting 2-factor code...')
                    code = self.__get_emailed_code__()
                    if not code:
                        multi_log(self, '2-factor code requested. Check your email or sms and enter it here...', level='warn',
                                  notify=True, title='Need 2-factor code', icon_url='https://www.inwebo.com/wp-content/uploads/ID-protectionG.png')
                        sleep(Global.med_min)
                        code = input('Enter Code: ')
                    multi_log(self, 'Entering code...', level='info')
                    self.__type_xpath__('//*[@id="oneTimeCode"]', code, Global.micro_min)
                    # if not self.__get_xpath__('//*[@id="label-trustThisDevice"]', Global.micro_min).is_selected():  # Doesn't seem to be working, default is checked, anyway
                    #     self.__click_xpath__('//*[@id="label-trustThisDevice"]', Global.micro_min)
                    self.__click_xpath__('//*[@id="btnSubmit"]', Global.micro_min)
                except TimeoutException:
                    multi_log(self, 'No 2-factor code needed.', level='debug')
            # Check if secret answer is needed
            elif progress == 'question':
                try:
                    multi_log(self, 'Attempting secret answer...', level='debug')
                    # noinspection PyUnresolvedReferences,PyUnresolvedReferences
                    self.__type_xpath__('/html/body/section/article/div/div/div[2]/div[2]/div/input', self.user['secret_answer'], Global.small_min)
                    multi_log(self, 'Entering secret answer...', level='debug')
                    self.__click_xpath__(".//*[contains(text(), 'Continue')]")
                except TimeoutException:
                    multi_log(self, 'No secret answer needed...', level='debug')
            # Check if Agreement is needed
            elif progress == 'agreement':
                try:
                    self.__click_xpath__('/html/body/section/div/div/div/div/div[2]/div/button[2]')
                    multi_log(self, 'Clicking agreement...', level='debug')
                except TimeoutException:
                    multi_log(self, 'No agreement needed...', level='debug')
        # Take care of unassigned items to prevent errors
        self.check_unassigned()

    #############################
    #
    #       INTERNAL FUNCTIONS - NOT MEANT FOR USER
    #
    #############################
    #############################
    #       MISC
    #############################
    def __logged_in__(self):
        try:
            if self.get_credits() > 0:
                multi_log(self, 'Successful Login!', level='green')
                self.credits = self.get_credits()
                self.__check_for_errors__()
                self.rate_limit()
                self.location = 'home'
                self.logged_in = True
                self.active = True
                return True
            else:
                self.logged_in = False
                return False
        except NoSuchElementException:
            self.logged_in = False
            return False

    def __login_progress__(self):
        self.__disable_click_shield__()
        if not self.__logged_in__():
            try:
                self.__click_xpath__('//*[@id="Login"]/div/div/div[1]/div/button', Global.micro_min)
            except TimeoutException:
                pass
            try:
                self.__get_xpath__("//*[contains(text(), 'Sign in with your EA Account')]", timeout=Global.micro_min)
                return 'ea_account'
            except (TimeoutException, NoSuchElementException, ElementNotVisibleException):
                pass
            try:
                self.__get_xpath__("//*[contains(text(), 'Send Security Code')]", timeout=Global.micro_min)
                return 'send_code'
            except (TimeoutException, NoSuchElementException, ElementNotVisibleException):
                pass
            try:
                self.__get_class__('p-phishing', as_list=False, timeout=Global.micro_min)
                return 'question'
            except (TimeoutException, NoSuchElementException, ElementNotVisibleException):
                pass
            try:
                self.__get_xpath__("//*[contains(text(), 'Accept')]", timeout=Global.micro_min)
                return 'agreement'
            except (TimeoutException, NoSuchElementException, ElementNotVisibleException):
                pass

    def __get_items__(self, gp_element=None, gp_type=None, p_element=None, p_type=None, get_price=False, timeout=Global.small_max):
        attempts_left = 10
        items = []
        while attempts_left:
            try:
                if gp_element:
                    if gp_type == 'class':
                        gp = self.__get_class__(gp_element, as_list=False)
                    elif gp_type == 'xpath':
                        gp = self.__get_xpath__(gp_element)
                    else:
                        raise Exception('Wrong gp_type: {}'.format(gp_type))
                if p_element and gp_element:
                    if p_type == 'class':
                        p = gp.find_element_by_class_name(p_element)
                    elif gp_type == 'xpath':
                        p = gp.find_element_by_xpath(p_element)
                    else:
                        raise Exception('Wrong p_type: {}. With gp_element: {}'.format(p_type, gp_element))
                    items = parse.parse_item_list(p.find_elements_by_class_name('listFUTItem'), get_price=get_price, obj=self)
                    break
                elif p_element and not gp_element:
                    if p_type == 'class':
                        p = self.__get_class__(p_element, as_list=False)
                    elif p_type == 'xpath':
                        p = self.__get_xpath__(p_element)
                    else:
                        raise Exception('Wrong p_type: {}'.format(p_type))
                    items = parse.parse_item_list(p.find_elements_by_class_name('listFUTItem'), get_price=get_price, obj=self)
                    break
                else:
                    items = parse.parse_item_list(self.__get_class__('listFUTItem', as_list=True, timeout=timeout), get_price=get_price, obj=self)
                    break
            except StaleElementReferenceException:
                attempts_left -= 1
                multi_log(obj=self, message='Page elements changed. Pausing and trying again. {} attempts remaining'.format(attempts_left), level='debug')
                sys.stdout.write('\rPage elements changed. Pausing and trying again. {} attempts remaining'.format(attempts_left))
                self.keep_alive(15 * (3 - attempts_left))
                sys.stdout.flush()
                sys.stdout.write('\r')
            except (TimeoutException, NoSuchElementException):
                return []
        if attempts_left == 0:
            raise Exception('Ran out of attempts to get stale element')
        return items

    def __get_emailed_code__(self):
        server = self.user.get('imap_server', None)
        email_address = self.user.get('imap_email', None)
        password = self.user.get('imap_password', None)
        if server and email_address and password:
            import imaplib
            import email

            multi_log(self, 'Waiting for email with 2-factor code...')
            iterations = 0
            while True:
                if iterations >= (300 / 5):
                    multi_log(self, 'Timed out waiting for code. Please enter manually.')
                    return None
                mail = imaplib.IMAP4_SSL(server)
                mail.login(email_address, password)
                mail.select('inbox')
                result, data = mail.uid('search', None, 'ALL')
                if result == 'OK':
                    for i in sorted(data[0].split()[-2:], reverse=True):
                        result, data = mail.uid('fetch', i, '(RFC822)')
                        if result == 'OK':
                            email_message = email.message_from_bytes(data[0][1])
                            subject = str(email.header.make_header(email.header.decode_header(email_message['Subject'])))
                            if 'ea security code' in subject.lower():
                                code = subject.split(': ')[-1]
                                multi_log(self, 'Got code: {}'.format(code))
                                mail.uid('STORE', i, '+FLAGS', '\\Deleted')
                                mail.expunge()
                                mail.close()
                                mail.logout()
                                return code
                        else:
                            multi_log(self, 'Error when fetching emails.')
                sleep(5)
                iterations += 1
        else:
            return None

    #############################
    #       ERRORS
    #############################
    def __check_for_errors__(self):
        self.__disable_click_shield__()
        classes_to_check = [
            'ui-dialog-type-alert',
            'ui-dialog-type-message',
            'client-update-screen',
            'popupClickShield',
            'Dialog',
        ]
        ids_to_check = [
            'ObjectiveRewardsOverlay',
            'LiveMessageOverlay',
        ]
        ok_errors = [
            'Bid status changed, auction data will be updated.',
            'You cannot unwatch an item you are bidding on.',
            'Cannot move this item because you already have the same item in your Club.',
            'Your bid must be higher than the current bid'
        ]
        cancel_errors = [
            'You are already the highest bidder. Are you sure you want to bid?'
        ]
        retry_errors = [
            'Sorry, an error has occurred.',
            'Sorry, a server error has occurred. Please check your network connection and try again.',
            'Sorry, the service you\'re trying to reach is unavailable at the moment.',
            'Sorry, it looks like something went wrong and an unknown error has occurred. Please refresh your browser to restart FUT Web.'
        ]
        delay_errors = [
            'You do not have enough coins to place a bid on this item.',
            'This item cannot be moved because there was an error.',
            'We’re currently having trouble with login services. While we work on it, you can try to log in from your Console or PC to get the full FUT experience.',
            'Sorry, it seems an error occurred while synchronizing with the FUT servers. The app will now restart.'
        ]
        for c in classes_to_check:
            try:
                found = self.driver.find_element_by_class_name(c)
                if found:
                    modal = self.driver.find_element_by_class_name(c)
                    try:
                        message = modal.find_element_by_tag_name('p').text
                    except (StaleElementReferenceException, NoSuchElementException):
                        message = ''
                        pass
                    if message in ok_errors:
                        modal.find_element_by_xpath(".//*[contains(text(), 'Ok')]").click()
                        message += ' Continuing'
                        multi_log(self, message, level='debug')
                        sys.stdout.write('\r{}'.format(message))
                        self.keep_alive(Global.micro_min)
                        sys.stdout.flush()
                        sys.stdout.write('\r')
                        return False
                    elif message in cancel_errors or 'highest bidder' in message:
                        modal.find_element_by_xpath(".//*[contains(text(), 'Cancel')]").click()
                        message += ' Continuing'
                        multi_log(self, message, level='warn')
                        sys.stdout.write('\r{}'.format(message))
                        self.keep_alive(3)
                        sys.stdout.flush()
                        sys.stdout.write('\r')
                        return False
                    elif message in retry_errors:
                        modal.find_element_by_xpath(".//*[contains(text(), 'Ok')]").click()
                        message += ' Retrying in 1 minute.'
                        multi_log(self, message, level='warn')
                        self.keep_alive(60)
                        self.__login__()
                        return False
                    elif message in delay_errors:
                        self.location = 'xxx'
                        modal.find_element_by_xpath(".//*[contains(text(), 'Ok')]").click()
                        message += ' Retrying in 30 seconds.'
                        multi_log(self, message, level='warn')
                        self.keep_alive(30)
                        return False
                    elif 'aptcha' in message:
                        self.__solve_captcha__()
                        return False
                    elif 'You have reached your Transfer Target limit' in message:
                        multi_log(obj=self, message='Transfer Target Limit Reached. Waiting for some items to expire then attempting to clear out expired items...',
                                  level='warn')
                        try:
                            modal.find_element_by_xpath(".//*[contains(text(), 'Ok')]").click()
                        except StaleElementReferenceException:
                            pass
                        return 'limit'
                    elif 'or more unassigned items' in message.lower():
                        multi_log(obj=self, message='Unassigned Items Limit Reached. Clear them out manually and press ENTER when done', level='error', notify=True,
                                  title='Action Required!')
                        self.__focus__()
                        return 'limit'
                    elif 'puzzle' in message:
                        self.__solve_captcha__()
                        return True
                    elif 'many actions have been taken' in message:
                        multi_log(obj=self, message='Looks like you\'ve been temp-banned. Lower RPM setting and wait a couple hours before trying again.',
                                  level='crit', notify=True, title='Temp Ban')
                        raise Exception('Looks like you\'ve been temp-banned. Lower RPM setting and wait a couple hours before trying again.')
                    elif 'players cannot be moved because of a previously disconnected gameplay session' in message:
                        current_location = self.location
                        self.location = 'xxx'
                        modal.find_element_by_xpath(".//*[contains(text(), 'Ok')]").click()
                        message += ' Retrying in 30 seconds.'
                        multi_log(obj=self, message='Either you didn\'t log out of your console or the EA server is having trouble. If this persists,'
                                                    + 'log into the account on your console, take care of any unassigned items,'
                                                    + 'and sign back out before running the bot again.')
                        self.keep_alive(30)
                        self.go_to(current_location)
                        return False
                    else:
                        try:
                            message = modal.find_element_by_class_name('description').text
                        except (StaleElementReferenceException, NoSuchElementException):
                            message = ''
                            pass
                        if 'pending rewards' in message.lower():
                            modal.find_element_by_xpath(".//*[contains(text(), 'Claim Rewards')]").click()
                            multi_log(obj=self, message='Claiming Rewards...')
                            return True
                elif c == 'client-update-screen':
                    message = self.__get_class__('patchMessage', as_list=False).text
                    message += ' Logging back in...'
                    multi_log(self, message=message)
                    self.keep_alive(Global.small_max)
                    self.driver.find_element_by_class_name('btn-text').click()
                    self.keep_alive(Global.med_max)
                    return True
            except NoSuchElementException:
                pass
        for ids in ids_to_check:
            try:
                found = self.driver.find_element_by_id(ids)
                if found:
                    if ids == 'LiveMessageOverlay':
                        multi_log(self, 'Found boot message. Pausing until we can continue...')
                        self.keep_alive(8)
                        self.__disable_click_shield__()
                        self.driver.find_element_by_xpath(".//*[contains(text(), 'Continue')]").click()
                        return True
                    else:
                        modal = found
                        try:
                            message = modal.find_element_by_class_name('description').text
                        except StaleElementReferenceException:
                            message = ''
                            pass
                        if 'pending rewards' in message:
                            modal.find_element_by_xpath(".//*[contains(text(), 'Claim Rewards')]").click()
                            message += ' . Rewards auto-claimed. Continuing'
                            multi_log(self, message, level='debug')
                            sys.stdout.write('\r{}'.format(message))
                            self.keep_alive(Global.micro_min)
                            sys.stdout.flush()
                            sys.stdout.write('\r')
                            return True
            except NoSuchElementException:
                pass
        return True

    def __solve_captcha__(self):
        multi_log(self, 'SOLVE THE CAPTCHA! HURRY!', level='crit', notify=True, title='CAPTCHA',
                        icon_url='https://www.funcaptcha.com/wp-content/themes/builder/v2/images/Blank-RB-33.jpg')
        self.__focus__()
        while True:
            try:
                self.__get_xpath__("//*[contains(text(), 'Sign in with your EA Account')]", timeout=Global.micro_min)
                try:
                    # noinspection PyUnresolvedReferences,PyUnresolvedReferences
                    self.__type_xpath__('//*[@id="email"]', self.user['email'], Global.micro_min)
                except TimeoutException:
                    pass
                try:
                    # noinspection PyUnresolvedReferences
                    self.__type_xpath__('//*[@id="password"]', self.user['password'], Global.micro_min)
                    multi_log(self, 'Entering user/pass...', level='debug')
                    self.__click_xpath__('//*[@id="btnLogin"]', Global.micro_min)
                except TimeoutException:
                    multi_log(self, 'No user/pass needed', level='debug')
                break
            except (TimeoutException, NoSuchElementException, ElementNotVisibleException):
                pass
        self.wait_for_enter()

    def __disable_click_shield__(self):
        try:
            # Try to gracefully remove clickShield
            script = '(function() {\'use strict\'; components.ClickShield.prototype.showShield = function(t) {};})();'
            self.driver.execute_script(script)
            # Force removal of div with shadow class
            self.driver.execute_script("""
            var element = document.querySelector(".shadow");
            if (element)
                element.parentNode.removeChild(element);
            """)
        except WebDriverException:
            pass

    #############################
    #       NAVIGATION / INTERACTION
    #############################
    def __click_xpath__(self, xpath, timeout=Global.large_min):
        self.__check_for_errors__()
        try:
            self.__disable_click_shield__()
        except WebDriverException:
            pass
        wait = WebDriverWait(self.driver, timeout)
        e = wait.until(ec.element_to_be_clickable((By.XPATH, xpath)))
        move = ActionChains(self.driver).move_to_element_with_offset(e, rand(1, 5), rand(1, 5))
        move.perform()
        e.click()
        sleep(Global.micro_min/2)
        self.__check_for_errors__()

    def __type_xpath__(self, xpath, text, timeout=Global.large_min):
        self.__check_for_errors__()
        self.__click_xpath__(xpath, timeout)
        e = self.driver.find_element_by_xpath(xpath)
        e.send_keys(Keys.CONTROL + 'a')
        e.send_keys(Keys.DELETE)
        e.clear()
        e.send_keys(text)
        self.__check_for_errors__()

    def __get_xpath__(self, xpath, timeout=Global.large_min):
        try:
            self.__disable_click_shield__()
        except WebDriverException:
            pass
        wait = WebDriverWait(self.driver, timeout)

        return wait.until(ec.presence_of_element_located((By.XPATH, xpath)))

    def __get_class__(self, class_name, as_list=True, timeout=Global.large_min):
        wait = WebDriverWait(self.driver, timeout)
        wait.until(ec.presence_of_element_located((By.CLASS_NAME, class_name)))
        if as_list:
            return self.driver.find_elements_by_class_name(class_name)
        else:
            return self.driver.find_element_by_class_name(class_name)

    def __click_element__(self, e):
        self.__check_for_errors__()
        move = ActionChains(self.driver).move_to_element_with_offset(e, rand(1, 5), rand(1, 5))
        move.perform()
        e.click()
        sleep(Global.micro_min/2)
        self.__check_for_errors__()

    def __type_element__(self, e, text):
        self.__check_for_errors__()
        self.__click_element__(e)
        e.send_keys(Keys.CONTROL + 'a')
        e.send_keys(Keys.DELETE)
        e.clear()
        e.send_keys(text)
        self.__check_for_errors__()

    def __focus__(self):
        self.new_tab('about:blank')
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.close_tab()
        self.driver.switch_to.window(self.driver.window_handles[0])
        if self.headless:
            self.driver.set_window_position(0, 0)

    #############################
    #
    #       MEANT FOR USER
    #
    #############################
    #############################
    #       NAVIGATION
    #############################
    def go_to(self, where):
        """
        Used to navigate to different sections of the web app.
        Generally speaking, 'where' is the title of whatever the button is in the web app
        :param where: str=
        """
        def check_for_unassigned():
            sleep(Global.micro_max)
            try:
                unassigned_tile = self.__get_class__('UnassignedTile', as_list=False, timeout=Global.micro_max)
                self.unassigned_size = int(unassigned_tile.find_element_by_class_name('itemsNumber').text)
            except (NoSuchElementException, TimeoutException):
                pass
        self.rate_limit()
        self.__disable_click_shield__()
        if where == self.location:
            if where == 'search':
                if self.__get_class__('pageTitle', as_list=False).text.lower() == 'transfers':
                    self.location = 'transfers'
                    self.go_to('search')
                    return
            multi_log(self, 'Cannot go_to {}. Already There'.format(self.location), level='debug')
        else:
            self.__check_for_errors__()
            self.location = where
            nav = self.driver.find_element_by_tag_name('nav')
            if where == 'home':
                nav.find_element_by_class_name('btnHome').click()
                sleep(Global.micro_max)
                try:
                    transfer_tile = self.__get_class__('transferListTile', as_list=False)
                    try:
                        self.current_tradepile_size = int(transfer_tile.find_element_by_class_name('count').text)
                    except ValueError:
                        pass
                except (NoSuchElementException, TimeoutException):
                    sleep(Global.small_max)
                    try:
                        transfer_tile = self.__get_class__('transferListTile', as_list=False)
                        self.current_tradepile_size = int(transfer_tile.find_element_by_class_name('count').text)
                    except (NoSuchElementException, TimeoutException):
                        pass
                check_for_unassigned()
            elif where == 'squads':
                nav.find_element_by_class_name('btnSquads').click()
            elif where == 'sbc':
                nav.find_element_by_class_name('btnSBC').click()
            elif where == 'transfers':
                try:
                    nav.find_element_by_class_name('btnTransfers').click()
                    sleep(Global.micro_max)
                    transfer_tile = self.__get_class__('transferListTile', as_list=False)
                except TimeoutException:
                    sleep(Global.med_max)
                    self.__focus__()
                    nav.find_element_by_class_name('btnTransfers').click()
                    sleep(Global.small_max)
                    transfer_tile = self.__get_class__('transferListTile', as_list=False)
                try:
                    self.current_tradepile_size = int(transfer_tile.find_element_by_class_name('count').text)
                except (NoSuchElementException, StaleElementReferenceException):
                    sleep(Global.small_max)
                    try:
                        self.current_tradepile_size = int(transfer_tile.find_element_by_class_name('count').text)
                    except (NoSuchElementException, StaleElementReferenceException):
                        pass
                except ValueError:
                    pass
            elif where == 'search' or ('search' in where and 'club' not in where):
                self.location = 'xxx'
                self.go_to('transfers')
                self.__click_xpath__('/html/body/section/article/div')
                self.location = 'search'
            elif where == 'transfer_list':
                self.go_to('transfers')
                self.__click_xpath__('/html/body/section/article/div[2]')
                self.location = 'transfer_list'
            elif where == 'transfer_targets':
                self.go_to('transfers')
                self.__click_xpath__('/html/body/section/article/div[3]')
                self.location = 'transfer_targets'
            elif where == 'store':
                nav.find_element_by_class_name('btnStore').click()
                check_for_unassigned()
            elif where == 'club':
                nav.find_element_by_class_name('btnClub').click()
            elif where == 'players':
                self.go_to('club')
                self.__click_xpath__('//*[@id="ClubHub"]/div[1]')
                self.location = 'players'
            elif where == 'unassigned':
                if self.location != 'home':
                    self.go_to('home')
                self.driver.find_element_by_id('UnassignedTile').click()
                self.location = 'unassigned'
            elif where == 'settings':
                nav.find_element_by_class_name('btnSettings').click()
            elif where == 'logout':
                self.go_to('settings')
                self.__click_xpath__('/html/body/section/div/div/div/div[2]/div[2]/div/ul[1]/button[3]')
                self.__click_xpath__('/html/body/div[1]/section/div/footer/a[2]')
                self.driver.get('about:blank')
                self.location = 'logged_out'
            else:
                raise Exception('Invalid go_to Option')
            self.__check_for_errors__()
        sleep(Global.small_max)

    def new_tab(self, new_url):
        self.driver.execute_script("window.open('{}');".format(new_url))
        sleep(Global.micro_max)
        self.driver.switch_to.window(self.driver.window_handles[-1])

    def close_tab(self):
        self.driver.execute_script("window.close();")
        sleep(Global.micro_max)
        self.driver.switch_to.window(self.driver.window_handles[-1])

    def wait_for_enter(self):
        input("Press Enter to continue...")
        multi_log(obj=self, message='Attempting to continue where we left off. If this doesn\'t work as expected, restart the bot.')

    #############################
    #       MISCELLANEOUS
    #############################
    def keep_alive(self, t):
        """
        Used to prevent session time outs. If t > 8 minutes, it will log out and then log back in.
        :param t: int: Time, in seconds to wait
        """
        re_login = False
        location = self.location
        if t > 60 * 8:
            self.driver.get('about:blank')
            re_login = True
            self.active = False
            multi_log(self, 'Will re-login once complete', level='info')
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
        if re_login:
            self.driver.switch_to.window(self.driver.window_handles[0])
            self.__login__()
            self.go_to(location)

    def rate_limit(self, min_multiplier=0.7, max_multiplier=1.3, immediate=False):
        if immediate:
            self.immediate_count += 1
            sleep(0.25)
        elif (not immediate and self.immediate_count > 0) or self.immediate_count > 10:
            multi_log(self, 'Making up for immediate requests. Delaying...', level='debug')
            sys.stdout.write('\rToo many requests. Delaying...')
            self.keep_alive(rand(20, 45))
            self.immediate_count = 0
            sys.stdout.flush()
            sys.stdout.write('\r')
        elif not immediate:
            rpm = self.settings['requests_per_minute']
            spr = 60 / rpm
            now = datetime.now()
            if (now - self.last_action_time).seconds > spr:
                self.per_second_count = 0
            else:
                if self.per_second_count < spr:
                    self.per_second_count += 1
                else:
                    multi_log(self, 'Too many requests. Delaying...', level='debug')
                    sys.stdout.write('\rToo many requests. Delaying...')
                    delay = spr - (now - self.last_action_time).seconds
                    self.keep_alive(rand(delay * min_multiplier, delay * max_multiplier))
                    self.immediate_count = 0
                    sys.stdout.flush()
                    sys.stdout.write('\r')
        self.last_action_time = datetime.now()

    def quit(self):
        # Save info from EA
        self.driver.get('about:blank')
        sleep(Global.small_max)
        # Shut down
        self.driver.close()
        self.driver.quit()
        sleep(Global.small_max)
        for pid in self.pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        with open('{}/Default/Preferences'.format(self.userdir), 'r') as user_prefs:
            prefs_change = user_prefs.read()
        prefs_change = prefs_change.replace('Crashed', 'Normal')
        with open('{}/Default/Preferences'.format(self.userdir), 'w') as user_prefs:
            user_prefs.write(prefs_change)
            multi_log(self, 'Session complete', level='header')

    def __get_gui_info__(self):
        return self.current_strategy, self.last_console

    def check_unassigned(self):
        if self.location != 'home':
            self.go_to('home')
        try:
            self.__get_xpath__('//*[@id="UnassignedTile"]', timeout=Global.micro_max)
            self.go_to('unassigned')
            if not self.settings['sell_unassigned']:
                multi_log(self, 'You must take care of all unassigned items before continuing', level='error', notify=True, title='Unassigned')
                self.__focus__()
                self.wait_for_enter()
            else:
                unassigned = self.__get_items__(get_price=True)
                for item in unassigned:
                    if item['item_type'] != 'player':
                        continue
                    futbin_price = item['futbin_price']
                    tier = info.get_tier(futbin_price)
                    start_price = futbin_price - self.bin_settings[tier]['spread']
                    try:
                        sell_result = self.sell(item, start_price, futbin_price)
                        if sell_result == 'full':
                            common_deal_with_full_transfer_list(self, 'Clear_Unassigned')
                    except TimeoutException:
                        try:
                            self.__get_xpath__("//*[contains(text(), 'Transfer list full')]")
                            common_deal_with_full_transfer_list(self, 'Clear_Unassigned')
                        except TimeoutException:
                            pass
        except (NoSuchElementException, TimeoutException, ElementNotVisibleException):
            pass

    #############################
    #       NOTIFICATIONS
    #############################
    def notify_all(self, title='', message='', icon_url='http://www.futwiz.com/assets/img/fifa18/badges/888888.png', link=''):
        notifications.notify_all(obj=self, title=title, message=message, icon_url=icon_url, link=link)

    def notify_desktop(self, title='', message='', icon_url='http://www.futwiz.com/assets/img/fifa18/badges/888888.png', link=''):
        notifications.notify_desktop(obj=self, title=title, message=message, icon_url=icon_url, link=link)

    @staticmethod
    def notify_autoremote(title='', message='', icon_url='http://www.futwiz.com/assets/img/fifa18/badges/888888.png'):
        notifications.notify_autoremote(title=title, message=message, icon_url=icon_url)

    #############################
    #       INFORMATION
    #############################
    def get_price(self, player_id):
        return info.get_price(player_id, self)

    def get_club(self):
        if self.location != 'players':
            self.go_to('players')
        multi_log(self, 'Getting club players. This takes approx. 1 minute per 100 players')
        all_club_players = []
        while True:
            page_players = self.__get_items__(get_price=True)
            for player in page_players:
                self.__click_element__(player['element'])
                panel = self.__get_class__('DetailView', as_list=False)
                try:
                    panel.find_element_by_xpath(".//*[contains(text(), 'This item cannot be traded')]")
                    player['untradeable'] = True
                except (NoSuchElementException, TimeoutException):
                    player['untradeable'] = False
                all_club_players.append(player)
            try:
                self.__click_xpath__('//*[@id="MyClubSearch"]/section/article/div[1]/div[2]/a[2]')
                self.rate_limit()
            except (TimeoutException, NoSuchElementException):
                break
        return all_club_players

    def get_credits(self):
        try:
            found = self.__get_xpath__('//*[@id="user-coin"]/div/span[2]', timeout=Global.micro_min).text
            if found != '' and '-' not in found:
                found = parse.price_parse(found)
                if found > 0:
                    self.credits = found
                    database.save_credits(self)
        except TimeoutException:
            pass
        return self.credits

    #############################
    #       SBCs
    #############################
    def solve_sbc(self, *args, **kwargs):
        return sbc.solve_sbc(self, *args, **kwargs)

    #############################
    #       ACTIONS
    #############################
    def buy_pack(self, *args, **kwargs):
        return actions.buy_pack(self, *args, **kwargs)

    def relist_all(self):
        return actions.relist_all(self)

    def clear_sold(self):
        return actions.clear_sold(self)

    def clear_expired(self):
        return actions.clear_expired(self)

    def sell(self, *args, **kwargs):
        return actions.sell(self, *args, **kwargs)

    def relist_item(self, *args, **kwargs):
        return actions.relist_item(self, *args, **kwargs)

    def quick_sell(self, *args, **kwargs):
        return actions.quick_sell(self, *args, **kwargs)

    def search(self, *args, **kwargs):
        return actions.search(self, *args, **kwargs)

    def buy_now(self, *args, **kwargs):
        return actions.buy_now(self, *args, **kwargs)

    def bid(self, *args, **kwargs):
        return actions.bid(self, *args, **kwargs)

    def check_sold(self):
        return actions.check_sold(self)

    def send_to_club(self, *args, **kwargs):
        return actions.send_to_club(self, *args, **kwargs)

    def send_to_transfer_list(self, *args, **kwargs):
        return actions.send_to_club(self, *args, **kwargs)

    def apply_consumables_to_squad(self, *args, **kwargs):
        return actions.apply_consumables_to_squad(self, *args, **kwargs)

    def futbin_login(self, *args, **kwargs):
        return actions.futbin_login(self, *args, **kwargs)

    def futbin_club_import(self):
        return actions.futbin_club_import(self)

    #############################
    #       STRATEGIES
    #############################
    def bpm(self):
        return bpm.bpm(self)

    def snipe(self):
        return snipe.snipe(self)

    def filter_snipe(self):
        return filter_snipe.filter_snipe(self)

    def filter_amass(self):
        return filter_amass.filter_amass(self)

    def hunt(self):
        return hunt.hunt(self)

    def futbin_market(self):
        return futbin_market.futbin_market(self)

    def futbin_cheapest_sbc(self):
        return futbin_cheapest_sbc.futbin_cheapest_sbc(self)

    def sell_club_players(self, *args, **kwargs):
        return sell_club_players.sell_club_players(self, *args, **kwargs)

    def continual_relist(self, *args, **kwargs):
        return continual_relist.continual_relist(self, *args, **kwargs)

    def acquire(self, *args, **kwargs):
        return acquire.acquire(self, *args, **kwargs)

    def amass(self):
        return amass.amass(self)

    def sbc_hunt(self):
        return sbc_hunt.sbc_hunt(self)

    def sell_transfer_targets_at_market(self):
        return sell_transfer_targets_at_market.sell_transfer_targets_at_market(self)

    def housekeeping(self):
        return housekeeping(self)

    def relist_individually(self, *args, **kwargs):
        return relist_individually.relist_individually(self, *args, **kwargs)

    def price_fix(self):
        return price_fix.price_fix(self)

    def market_monitor(self):
        return market_monitor.market_monitor(self)

    def arbitrage(self):
        return arbitrage.arbitrage(self)

    def silver_flip(self):
        return silver_flip.silver_flip(self)

    def filter_finder(self, *args, **kwargs):
        return filter_finder.filter_finder(self, *args, **kwargs)

    def coin_transfer_prep(self, *args, **kwargs):
        return coin_transfer_prep.coin_transfer_prep(self, *args, **kwargs)

    def coin_transfer_list(self, *args, **kwargs):
        return coin_transfer_list.coin_transfer_list(self, *args, **kwargs)

    def consumable_amass(self, *args, **kwargs):
        return consumable_amass.consumable_amass(self, *args, **kwargs)

    def check_unlock(self):
        return check_unlock.check_unlock(self)