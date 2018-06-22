from FUTpuppeteer import info
from FUTpuppeteer.misc import multi_log, Global
from . import retry_decorator, common_snipe
from time import sleep


@retry_decorator
def arbitrage(obj):
    obj.current_strategy = 'Arbitrage'
    temp_settings = obj.strategy_settings['arbitrage']
    min_price = temp_settings['min_price']
    max_price = temp_settings['max_price']
    min_profit = temp_settings['min_profit']
    min_percentage_of_price = temp_settings['min_percentage_of_price']
    players = temp_settings['players']
    remove_keys = ['min_price', 'max_price', 'min_profit', 'min_percentage_of_price', 'players']
    settings = {k: v for k, v in temp_settings.items() if k not in remove_keys}
    multi_log(obj, 'Conducting Arbitrage...', level='title')
    players_to_arbitrage = []
    # Go through player lists
    for player in players:
        futbin = info.get_price(player, obj, False, False, 'futbin')
        futhead = info.get_price(player, obj, False, False, 'futhead')
        if futbin != 0 and futhead != 0:
            potential = int(round((futbin * 0.95) - futhead))
            percent = abs(int(round((potential / futbin) * 100)))
            if potential > min_profit and percent > min_percentage_of_price:
                players_to_arbitrage.append((player, futhead, futbin, potential))
        sleep(0.25)
    if len(players_to_arbitrage) == 0:
        multi_log(obj, 'No players to arbitrage')
        return None
    for player in players_to_arbitrage:
        search_price = player[2]
        tier = info.get_tier(search_price)
        search_price = info.round_down(search_price, Global.rounding_tiers[tier])
        sell_price = info.round_down(player[2] - (0.2 * player[3]), Global.rounding_tiers[tier])
        if search_price > 0:
            if obj.get_credits() > search_price and min_price <= search_price <= max_price:
                snipe_criteria = {
                    'search_type': 'Players',
                    'player': player[0],
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
                common_snipe(obj, name=info.get_player_info(snipe_criteria['player'], False)['name'], snipe_criteria=snipe_criteria, price=search_price,
                             sell_price=sell_price, strategy='arbitrage', **settings)
