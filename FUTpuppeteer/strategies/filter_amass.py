from FUTpuppeteer.parse import create_futbin_url, parse_futbin_tables
from FUTpuppeteer.misc import multi_log
from . import retry_decorator, common_hunt, common_wait_to_expire


@retry_decorator
def filter_amass(obj):
    obj.current_strategy = 'Filter Amass'
    temp_settings = obj.strategy_settings['filter_amass']
    filters = temp_settings['filters']
    max_price = temp_settings['max_price']
    remove_keys = ['filters', 'max_price']
    settings = {k: v for k, v in temp_settings.items() if k not in remove_keys}
    multi_log(obj, 'Filter amassing players...', level='title')
    total_bids = 0
    # Search and bid
    for f in filters:
        multi_log(obj, 'Getting filter data...')
        futbin_url = create_futbin_url(obj, f)
        obj.new_tab(futbin_url)
        obj.location = 'futbin'
        max_price = f.get('max_price', max_price)
        # Grab all data from tables, hit next page until it can't any more, turn data into list of player dicts
        all_results = parse_futbin_tables(obj, futbin_url, True, False)
        multi_log(obj, 'Done getting filter data')
        obj.close_tab()
        obj.driver.switch_to.window(obj.driver.window_handles[0])
        obj.location = 'home'
        prices = []
        include = []
        for result in all_results:
            if result['price'] != 0 and result['resource_id'] not in f.get('exclude', []):
                include.append(result['resource_id'])
                prices.append(result['price'])
        filter_name = list(f.values())
        if not prices:
            prices = [0]
        if max_price and max_price > 0:
            max_buy = min(max_price, max(prices))
        else:
            max_buy = max(prices)
        try:
            hunt_criteria = {
                'search_type': 'Players',
                'player': None,
                'quality': f.get('quality', None),
                'position': f.get('position', None),
                'chem_style': f.get('chem_style', None),
                'nation': f.get('nation', None),
                'league': f.get('league', None),
                'club': f.get('club', None),
                'max_buy': max_buy,
                'include': include,
                'exclude': f.get('exclude', None),
            }
        except ValueError:
            continue
        num_bids = common_hunt(obj=obj, name=filter_name, hunt_criteria=hunt_criteria, strategy='filter_amass', **settings)
        if num_bids == 'limit':
            common_wait_to_expire(obj=obj, strategy='filter_amass')
        else:
            total_bids += num_bids
    if total_bids > 0:
        common_wait_to_expire(obj=obj, strategy='filter_amass')
