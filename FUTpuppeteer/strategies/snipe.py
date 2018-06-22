from FUTpuppeteer import info
from FUTpuppeteer.misc import multi_log
from . import retry_decorator, common_snipe


@retry_decorator
def snipe(obj):
    obj.current_strategy = 'Snipe'
    temp_settings = obj.strategy_settings['snipe']
    min_price = temp_settings['min_price']
    max_price = temp_settings['max_price']
    players = temp_settings['players']
    rotate = temp_settings['rotate']
    remove_keys = ['min_price', 'max_price', 'players', 'rotate']
    settings = {k: v for k, v in temp_settings.items() if k not in remove_keys}
    multi_log(obj, 'Sniping...', level='title')
    # Go through player lists
    if not rotate:
        for player in players:
            futbin_price = info.get_price(player, obj=obj)
            if futbin_price > 0:
                if obj.get_credits() > futbin_price and min_price <= futbin_price <= max_price:
                    snipe_criteria = {
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
                    common_snipe(obj, name=info.get_player_info(snipe_criteria['player'], False)['name'], snipe_criteria=snipe_criteria, strategy='snipe', **settings)
    else:
        rotations_remaining = settings['max_tries']
        temp_settings = settings
        remove_keys = ['max_tries']
        settings = {k: v for k, v in temp_settings.items() if k not in remove_keys}
        while rotations_remaining > 0:
            for player in players:
                futbin_price = info.get_price(player, obj=obj)
                if futbin_price > 0:
                    if obj.get_credits() > futbin_price and min_price <= futbin_price <= max_price:
                        snipe_criteria = {
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
                        common_snipe(obj, name=info.get_player_info(snipe_criteria['player'], False)['name'], snipe_criteria=snipe_criteria, strategy='snipe', max_tries=1, **settings)
            rotations_remaining -= 1
