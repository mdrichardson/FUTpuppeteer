from FUTpuppeteer.core import Session
from FUTpuppeteer.misc import multi_log


bot1 = Session(bot_number=1, delay_login=False, debug=True, headless=False)

##################
#  Single-Use 
##################
# bot1.wait_for_enter()
# bot1.continual_relist(ignore_tradepile=True)
# bot1.clear_sold()
# bot1.relist_all()
# bot1.relist_individually(at_market=True)
# bot1.sell_club_players(search='bronze', min_sell_bronze=800, rare_multiplier=1)
# bot1.sell_club_players(search='silver', min_sell_silver=1000, rare_multiplier=1.2)
# bot1.sell_club_players(search='gold', min_sell_silver=1000, rare_multiplier=1.2, exclude=['28130', '230666', '173731', '191740', '200145', '220834', '169595', '184432', '200724', '204963', '193041'])
# bot1.apply_consumables_to_squad('active', 'contracts', 'gold', False, 1)
# bot1.apply_consumables_to_squad('active', 'fitness', 'bronze', True, 1)
# bot1.acquire(['67309009'], futbin_multiplier=0.95, increase_each_round=True, max_increases=10)
# bot1.coin_transfer_prep(250000)
# bot1.coin_transfer_list(3, ['180754'])
# bot1.coin_transfer_list(5, ['187033'])
# bot1.futbin_club_import()
# bot1.wait_for_enter()
# bot1.quit()

##################
#  SBC Solver
##################

# to_solve = [
# ('https://www.futbin.com/18/squad/100163474/sbc', []),
# ]
# for sbc in to_solve:
#     bot1.housekeeping()
#     bot1.solve_sbc(sbc[0], 0.98, increase_each_round=True, max_increases=8, exclude=sbc[1])
# bot1.wait_for_enter()


# bot1.quit()

##################
#  Main
##################
total_cycles = 5
while True:
    if not bot1.logged_in:
        bot1.__login__()
    #bot1.relist_at_market()
    # bot1.continual_relist(ignore_tradepile=True)
    '''
    while bot1.max_tradepile_size - bot1.current_tradepile_size > 30:
        bot1.bpm()
        bot1.keep_alive(3)
        bot1.get_tradepile()
        bot1.clear_sold()
        bot1.relist_all()
    '''
    strategies = [
        #bot1.arbitrage,
        #bot1.amass,
        #bot1.sbc_hunt,
        #bot1.futbin_cheapest_sbc,
        # bot1.filter_snipe,
        # bot1.consumable_amass,
        #bot1.hunt,
        # bot1.snipe,
        #bot1.futbin_market,
        bot1.bpm,
        #bot1.silver_flip,
        #bot1.price_fix,
        # bot1.market_monitor
    ]
    for strategy in strategies:
            bot1.housekeeping()
            strategy()
    multi_log(bot1, 'Iteration complete')
bot1.quit()
