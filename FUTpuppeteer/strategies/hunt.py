from FUTpuppeteer import info
from FUTpuppeteer.misc import multi_log
from . import retry_decorator, common_hunt, common_fight, common_wait_to_expire


@retry_decorator
def hunt(obj):
    obj.current_strategy = 'Hunt'
    temp_settings = obj.strategy_settings['hunt']
    min_price = temp_settings['min_price']
    max_price = temp_settings['max_price']
    players = temp_settings['players']
    remove_keys = ['min_price', 'max_price', 'players']
    settings = {k: v for k, v in temp_settings.items() if k not in remove_keys}
    multi_log(obj, 'Hunting...', level='title')
    total_bids = 0
    # Search and bid
    for player in players:
        futbin_price = info.get_price(player, obj=obj)
        if futbin_price > 0:
            if obj.get_credits() > futbin_price and min_price <= futbin_price <= max_price:
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
                num_bids = common_hunt(obj=obj, name=info.get_player_info(hunt_criteria['player'], False)['name'], hunt_criteria=hunt_criteria, strategy='hunt', **settings)
                if num_bids == 'limit':
                    common_wait_to_expire(obj=obj, strategy='hunt')
                else:
                    total_bids += num_bids

    if total_bids > 0:
        if not settings['use_max_buy']:
            common_fight(obj=obj, strategy='hunt', settings=settings)
        else:
            common_wait_to_expire(obj=obj, strategy='hunt')
