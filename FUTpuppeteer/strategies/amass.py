from FUTpuppeteer import info
from FUTpuppeteer.misc import multi_log
from . import retry_decorator, common_hunt, common_wait_to_expire


@retry_decorator
def amass(obj):
    obj.current_strategy = 'Amass'
    temp_settings = obj.strategy_settings['amass']
    players = temp_settings['players']
    remove_keys = ['players']
    settings = {k: v for k, v in temp_settings.items() if k not in remove_keys}
    multi_log(obj, 'Amassing players...', level='title')
    total_bids = 0
    # Search and bid
    for player in players:
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
        num_bids = common_hunt(obj=obj, name=player_name, hunt_criteria=hunt_criteria, strategy='amass', **settings)
        if num_bids == 'limit':
            common_wait_to_expire(obj=obj, strategy='amass')
        else:
            total_bids += num_bids
    if total_bids > 0:
        common_wait_to_expire(obj=obj, strategy='amass')
        total_bids = 0
