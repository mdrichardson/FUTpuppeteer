from FUTpuppeteer import info
from FUTpuppeteer.misc import multi_log, Global
from . import retry_decorator, common_snipe, common_hunt, common_wait_to_expire


@retry_decorator
def acquire(obj, player_list, futbin_multiplier, increase_each_round=False, max_increases=5, sell_acquired_if_full=True, special_only=False):
    obj.current_strategy = 'Acquire'
    snipe_settings = obj.strategy_settings['acquire']['snipe']
    hunt_settings = obj.strategy_settings['acquire']['hunt']
    if type(player_list) is not list:
        new = [player_list]
        player_list = new
    if special_only:
        quality = 'Special'
    else:
        quality = None
    multi_log(obj, 'Acquiring Players...', level='title')
    # Go through player lists
    remaining_players = player_list
    acquired = []
    iteration = 1
    while len(remaining_players) > 0:
        bids = 0
        search_list = []
        if iteration > 1:
            snipe_settings['max_results'] = 9999999
        print('{:<30}  {:<20}  {:<20}'.format('Name', 'Futbin Price', 'Asset ID'))
        for player in remaining_players:
            player_info = info.get_player_info(player, include_futbin_price=True)
            print('{:<30}  {:<20}  {:<20}'.format(player_info['name'], player_info['futbin_price'], player))
            search_list.append(player_info)
        for player in search_list:
            name = player['name']
            futbin_price = player['futbin_price']
            tier = info.get_tier(futbin_price)
            max_bin = max(200, info.round_down(futbin_price * futbin_multiplier, Global.rounding_tiers[tier]))
            if increase_each_round:
                max_bin += Global.rounding_tiers[tier] * iteration
            include = []
            if quality and quality.lower() == 'special' and int(player['asset_id']) <= 300000:
                special_ids = info.get_special_ids(player['asset_id'])
                for s in list(special_ids.values()):
                    if int(s) >= 300000:
                        include.append(s)
                include.append(info.get_base_id(player['asset_id']))
                include.append(player.get('asset_id', None))
            elif int(player['asset_id']) > 300000:
                include.append(player['asset_id'])
                include.append(info.get_base_id(player['asset_id']))
            snipe_criteria = {
                'search_type': 'Players',
                'player': player['asset_id'],
                'quality': quality,
                'position': None,
                'chem_style': None,
                'nation': None,
                'league': None,
                'club': None,
                'min_bin': None,
                'include': include,
                'exclude': None,
            }
            snipe_result = common_snipe(obj=obj, snipe_criteria=snipe_criteria, name=name, strategy='acquire', price=max_bin,
                                        max_item_buys=1, sell_acquired_if_full=sell_acquired_if_full, **snipe_settings)
            if snipe_result == 'too many':
                multi_log(obj, 'Lots of results returned. Trying to get this cheaper by bidding...')
                max_bin -= Global.rounding_tiers[tier]
            elif snipe_result > 0:
                acquired.append((name, max_bin))
                for i, player_id in enumerate(remaining_players):
                    if str(player_id) == str(player['asset_id'] or str(player_id) in include):
                        remaining_players.pop(i)
                        break
                continue
            if obj.get_credits() > player['futbin_price']:
                num_bids = common_hunt(obj=obj, name=name, hunt_criteria=snipe_criteria, price=max_bin, strategy='acquire', max_item_bids=1, **hunt_settings)
                if num_bids == 'limit':
                    common_wait_to_expire(obj, 'acquire', remaining_players, acquired, sell_acquired_if_full=sell_acquired_if_full)
                    break
                elif num_bids == 'owned' or num_bids == 'sniped':
                    acquired.append((name, max_bin))
                    for i, player_id in enumerate(remaining_players):
                        if str(player_id) == str(player['asset_id']) or str(player_id) in include:
                            remaining_players.pop(i)
                            break
                else:
                    bids += num_bids
        if bids > 0:
            remaining_players, acquired = common_wait_to_expire(obj, 'acquire', remaining_players, acquired, sell_acquired_if_full=sell_acquired_if_full)
        if increase_each_round and iteration <= max_increases:
            iteration += 1
            if len(remaining_players) > 0:
                multi_log(obj, message='Increasing search price by {} step(s)'.format(min(iteration, max_increases)))
    multi_log(obj, message='Got all players!', level='green', notify=True, title='DONE')
    print('Acquired:')
    print('-' * 50)
    print('{:<30}  {:<6}'.format('Name', 'Price'))
    for player in acquired:
        print('{:<30}  {:<6}'.format(player[0], player[1]))
    return 'done'