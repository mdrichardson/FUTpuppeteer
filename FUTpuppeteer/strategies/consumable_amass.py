from FUTpuppeteer.parse import price_parse
from FUTpuppeteer.misc import multi_log, Global
from . import retry_decorator, common_hunt, common_wait_to_expire
from selenium.common.exceptions import TimeoutException


@retry_decorator
def consumable_amass(obj):
    obj.current_strategy = 'Consumable Amass'
    temp_settings = obj.strategy_settings['consumable_amass']
    filters = temp_settings['filters']
    sell_price = {}
    for f in filters:
        sell_price[f['item']] = f['sell_price']
    remove_keys = ['filters', 'sell_price']
    settings = {k: v for k, v in temp_settings.items() if k not in remove_keys}
    multi_log(obj, 'Filter amassing consumables...', level='title')
    total_bids = 0
    # Search and bid
    for f in filters:
        try:
            hunt_criteria = {
                'search_type': 'Consumables',
                'item': f['item'],
                'quality': f.get('quality', None),
                'position': f.get('position', None),
                'chem_style': f.get('chem_style', None),
                'nation': f.get('nation', None),
                'league': f.get('league', None),
                'club': f.get('club', None),
                'max_buy': f['max_buy']
            }
        except ValueError:
            continue
        name = '/'.join([str(x) for x in list(hunt_criteria.values()) if x is not None])
        num_bids = common_hunt(obj=obj, name=name, hunt_criteria=hunt_criteria, strategy='consumable_amass', **settings)
        if num_bids == 'limit':
            common_wait_to_expire(obj=obj, strategy='consumable_amass', sell_price=sell_price)
        else:
            total_bids += num_bids
    if total_bids > 0:
        common_wait_to_expire(obj=obj, strategy='consumable_amass', sell_price=sell_price)
