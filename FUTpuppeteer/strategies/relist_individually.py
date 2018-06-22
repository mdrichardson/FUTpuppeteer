from . import retry_decorator
from FUTpuppeteer import info
from FUTpuppeteer.misc import Global, multi_log
from selenium.common.exceptions import TimeoutException


@retry_decorator
def relist_individually(obj, at_market=False, duration='1 Hour'):
    obj.current_strategy = 'Relist Individually'
    settings = obj.strategy_settings['relist_individually']
    if settings['above_bin'] and settings['below_bin']:
        multi_log(obj, 'Cannot relist players. Settings file has both below_bin and above_bin set to True.', level='error')
        return 1
    if obj.location != 'transfer_list':
        obj.go_to('transfer_list')
    while True:
        expired = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Unsold Items')]", gp_type='xpath', get_price=True)
        if len(expired) == 0:
            break
        for item in expired:
            if item['item_type'] == 'player':
                if at_market:
                    futbin_price = item['futbin_price']
                    tier = info.get_tier(futbin_price)
                    level = 'green'
                    if settings['below_bin']:
                        futbin_price = info.round_down(futbin_price * obj.bin_settings[tier]['sell_percent'], Global.rounding_tiers[tier])
                        level = 'warn'
                    elif settings['above_bin']:
                        new_price = (item['buy_now_price'] + futbin_price) / 2
                        tier = info.get_tier(new_price)
                        futbin_price = max(futbin_price, info.round_down(new_price, Global.rounding_tiers[tier]))
                        level = 'warn'
                    tier = info.get_tier(futbin_price)
                    start_price = futbin_price - obj.bin_settings[tier]['spread']
                    multi_log(obj=obj, message='Relisting {} for {}. Was previously {}'.format(item['item_name'], futbin_price, item['buy_now_price']), level=level)
                else:
                    futbin_price = item['buy_now_price']
                    start_price = item['start_price']
                try:
                    obj.relist_item(item, start_price, futbin_price, duration)
                except TimeoutException:
                    pass
            else:
                obj.relist_item(item, item['start_price'], item['buy_now_price'], duration)
            obj.keep_alive(Global.micro_min)
            break
    try:
        obj.rate_limit()
        obj.__click_xpath__("//*[contains(text(), 'Re-list All')]", timeout=Global.small_min * 2)
        obj.__click_xpath__("//*[contains(text(), 'Yes')]", timeout=Global.small_min * 2)
        multi_log(obj, 'Items re-listed')
        obj.go_to('transfers')
    except TimeoutException:
        pass
    if duration == '1 Hour' and obj.settings['night_mode']['need_relist']:
        from ruamel.yaml import YAML
        yaml = YAML()
        yaml.explicit_start = True
        yaml.indent(mapping=4)
        yaml.preserve_quotes = True

        need_relisting = False
        active_transfers = obj.__get_items__(p_element='../..', p_type='xpath', gp_element="//*[contains(text(), 'Active Transfers')]", gp_type='xpath',
                                             get_price=False)
        for active in active_transfers:
            if active['time_left'] > 3601:
                need_relisting = True
                break
        if not need_relisting:
            with open(obj.config_file) as config:
                new_config = yaml.load(config)
                new_config['settings']['night_mode']['need_relist'] = False
            with open(obj.config_file, 'w') as update:
                yaml.dump(new_config, update)
