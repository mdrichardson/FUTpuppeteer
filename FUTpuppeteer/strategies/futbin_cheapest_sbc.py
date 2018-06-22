from FUTpuppeteer import info
from FUTpuppeteer.misc import multi_log
from . import retry_decorator, common_hunt, common_wait_to_expire


@retry_decorator
def futbin_cheapest_sbc(obj):
    obj.current_strategy = 'Futbin Cheapest SBC'
    temp_settings = obj.strategy_settings['futbin_cheapest_sbc']
    total_bids = 0

    def buy_and_search(target_player):
        player_info = info.get_player_info(target_player, include_futbin_price=True)
        player_name = player_info['name']
        bids = 0
        if obj.credits > player_info['futbin_price']:
            hunt_criteria = {
                'search_type': 'Players',
                'player': target_player,
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
            bids = common_hunt(obj=obj, name=player_name, hunt_criteria=hunt_criteria, strategy='futbin_cheapest_sbc', **settings)
        return bids

    multi_log(obj, 'Hunting for Cheapest SBC on Futbin...', level='title')
    min_price = temp_settings['min_price']
    max_price = temp_settings['max_price']
    remove_keys = ['min_price', 'max_price']
    settings = {k: v for k, v in temp_settings.items() if k not in remove_keys}
    players = info.get_futbin_cheapest_sbc(obj, min_price, max_price)
    for player in players:
        num_bids = buy_and_search(player)
        if num_bids == 'limit':
            common_wait_to_expire(obj=obj, strategy='futbin_cheapest_sbc')
        else:
            total_bids += num_bids
    if total_bids > 0:
        common_wait_to_expire(obj=obj, strategy='futbin_cheapest_sbc')
