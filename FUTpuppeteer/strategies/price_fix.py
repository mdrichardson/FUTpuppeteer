from FUTpuppeteer import info
from FUTpuppeteer.misc import multi_log, Global
from . import retry_decorator, common_snipe, common_hunt, common_wait_to_expire


@retry_decorator
def price_fix(obj):
    obj.current_strategy = 'Price Fix'
    settings = obj.strategy_settings['price_fix']
    snipe_settings = settings['snipe']
    hunt_settings = settings['hunt']
    players = settings['players']
    multi_log(obj, 'Price-fixing Players...', level='title')
    bids = 0
    for num, player in players.items():
        name = info.get_player_info(player['asset_id'], False)['name']
        futbin_price = info.get_price(player['asset_id'], obj, False)
        if futbin_price > player['sell_price'] :
            multi_log(obj, '{} price of {} is too low. Their Futbin price is {}'.format(name, player['sell_price'], futbin_price), level='warn')
            continue
        max_bin = player['sell_price']
        tier = info.get_tier(max_bin)
        if settings['use_buy_percent']:
            max_bin = min(futbin_price, info.round_down(max_bin * obj.bin_settings[tier]['buy_percent'], Global.rounding_tiers[tier]))
        else:
            max_bin = info.round_down((player['sell_price'] * 0.95) - settings['min_profit'], Global.rounding_tiers[tier])
        sell_price = player['sell_price']
        snipe_criteria = {
            'search_type': 'Players',
            'player': player['asset_id'],
            'quality': None,
            'position': None,
            'chem_style': None,
            'nation': None,
            'league': None,
            'club': None,
            'min_bin': None,
        }
        common_snipe(obj=obj, snipe_criteria=snipe_criteria, name=name, strategy='price_fix', price=max_bin, sell_price=sell_price, **snipe_settings)
        if obj.get_credits() > max_bin:
            num_bids = common_hunt(obj=obj, name=name, hunt_criteria=snipe_criteria, strategy='price_fix', price=max_bin, **hunt_settings)
            if num_bids == 'limit':
                common_wait_to_expire(obj=obj, strategy='price_fix', sell_price=sell_price)
            else:
                bids += num_bids
        if bids > 0:
            common_wait_to_expire(obj=obj, strategy='price_fix', sell_price=sell_price)
            bids = 0
