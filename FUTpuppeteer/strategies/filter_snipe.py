from FUTpuppeteer import info
from FUTpuppeteer.misc import multi_log, Global
from FUTpuppeteer.parse import create_futbin_url, parse_futbin_tables
from . import retry_decorator, common_snipe, dynamic_profit


@retry_decorator
def filter_snipe(obj):
    obj.current_strategy = 'Filter Snipe'
    temp_settings = obj.strategy_settings['filter_snipe']
    filters = temp_settings['filters']
    max_price = temp_settings['max_price']
    remove_keys = ['max_price', 'filters']
    settings = {k: v for k, v in temp_settings.items() if k not in remove_keys}
    multi_log(obj, 'Filter Sniping...', level='title')
    for f in filters:
        multi_log(obj, 'Getting filter data...')
        futbin_url = create_futbin_url(obj, f)
        obj.new_tab(futbin_url)
        obj.location = 'futbin'
        # Grab all data from tables, hit next page until it can't any more, turn data into list of player dicts
        all_results = parse_futbin_tables(obj, futbin_url, True, False)
        multi_log(obj, 'Done getting filter data')
        obj.close_tab()
        obj.driver.switch_to.window(obj.driver.window_handles[0])
        obj.location = 'home'
        include = []
        max_bin = 999999999999
        for result in all_results:
            if result['price'] != 0 and result['resource_id'] not in f.get('exclude', []):
                include.append(result['resource_id'])
                if result['price'] < max_bin:
                    max_bin = result['price']
        tier = info.get_tier(max_bin)
        if not settings['use_buy_percent']:
            search_price = info.round_down((max_bin * 0.95 * dynamic_profit(obj) * obj.bin_settings[tier]['sell_percent']) - settings['min_profit'],
                                           Global.rounding_tiers[tier])
        else:
            search_price = info.round_down((max_bin * obj.bin_settings[tier]['buy_percent'] * dynamic_profit(obj)), Global.rounding_tiers[tier])
        if obj.get_credits() > max_bin and search_price <= max_bin <= max_price:
            try:
                snipe_criteria = {
                    'search_type': 'Players',
                    'player': None,
                    'quality': f.get('quality', None),
                    'position': f.get('position', None),
                    'chem_style': f.get('chem_style', None),
                    'nation': f.get('nation', None),
                    'league': f.get('league', None),
                    'club': f.get('club', None),
                    'include': include,
                    'exclude': f.get('exclude', None),
                }
            except ValueError:
                continue
            name = list(f.values())
            common_snipe(obj, name=name, snipe_criteria=snipe_criteria, strategy='filter_snipe', price=max_bin,
                         **settings)