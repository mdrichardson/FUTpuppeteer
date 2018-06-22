from FUTpuppeteer.parse import parse_futbin_tables
from FUTpuppeteer.misc import multi_log, Global, Colors
from FUTpuppeteer.database import get_ea_name_from_id
from datetime import datetime
from urllib.parse import urlsplit, parse_qs
import numpy as np
from os import linesep


def filter_finder(obj, starting_url, min_price=None, min_players=None, include_zeroes=None, max_multiplier=2, max_spread=3500):
    obj.current_strategy = 'Filter Finder'
    settings = obj.strategy_settings['filter_finder']
    if not min_price:
        min_price = settings['min_price']
    if not min_players:
        min_players = settings['min_players']
    if not include_zeroes:
        include_zeroes = settings['include_zeroes']
    multi_log(obj, 'Finding Filters...', level='title')

    def get_futbin_url(filters_list, og_link):
        def add_to_filter(ft, text):
            if ft == '- {':
                ft = ft + text
            else:
                ft = ft + ', ' + text
            return ft

        if 'pc' in obj.platform:
            platform = 'pc'
        elif 'xbox' in obj.platform:
            platform = 'xbox'
        else:
            platform = 'ps'
        if 'sort' not in og_link:
            base_url = og_link + '&sort={}_price&order=asc'.format(platform)
        else:
            base_url = og_link
        params = parse_qs(urlsplit(og_link).query)
        filter_text = '- {'
        for k, v in params.items():
            if 'gold' in v[0].lower():
                filter_text = add_to_filter(filter_text, 'quality: Gold')
            elif 'silver' in v[0].lower():
                filter_text = add_to_filter(filter_text, 'quality: Silver')
            elif 'bronze' in v[0].lower():
                filter_text = add_to_filter(filter_text, 'quality: Bronze')
            elif 'special' in v[0].lower():
                filter_text = add_to_filter(filter_text, 'quality: Special')
            elif k.lower() == 'position':
                filter_text = add_to_filter(filter_text, 'position: {}'.format(v[0].upper()))
            elif k.lower() == 'nation':
                filter_text = add_to_filter(filter_text, 'nation: {}'.format(Global.fifa_nations[v[0]]))
            elif k.lower() == 'league' and 'club' not in og_link:
                filter_text = add_to_filter(filter_text, 'league: {}'.format(Global.fifa_leagues[v[0]]))
            elif k.lower() == 'club':
                filter_text = add_to_filter(filter_text, 'club: {}'.format(Global.fifa_clubs[v[0]]))
        for f in filters_list:
            if f[0] == 'quality' and f[1] in available_quality and 'version' not in base_url:
                base_url = base_url + '&version={}'.format(f[1].lower())
                filter_text = add_to_filter(filter_text, 'quality: {}'.format(f[1]))
            elif f[0] == 'position' and f[1]  in available_position and 'position' not in base_url:
                base_url = base_url + '&position={}'.format(f[1])
                filter_text = add_to_filter(filter_text, 'position: {}'.format(f[1]))
            elif f[0] == 'nation' and f[1] in available_nation and 'nation' not in base_url:
                name = get_ea_name_from_id(ea_db='fifa_nations', thing_id=f[1])
                base_url = base_url + '&nation={}'.format(f[1])
                filter_text = add_to_filter(filter_text, 'nation: {}'.format(name))
            elif f[0] == 'league' and f[1] in available_league and 'league' not in base_url and 'club' not in base_url:
                name = get_ea_name_from_id(ea_db='fifa_leagues', thing_id=f[1])
                base_url = base_url + '&league={}'.format(f[1])
                filter_text = add_to_filter(filter_text, 'league: {}'.format(name))
            elif f[0] == 'club' and f[1] in available_club and 'club' not in base_url:
                name = get_ea_name_from_id(ea_db='fifa_clubs', thing_id=f[1])
                base_url = base_url + '&club={}'.format(f[1])
                filter_text = add_to_filter(filter_text, 'club: {}'.format(name))
        filter_text = filter_text + '}'
        return base_url, filter_text

    def adjust_prices(price_list):
        try:
            return sorted([p for p in price_list if p <= max_multiplier * min(i for i in price_list if i > 0) or p <= min(i for i in price_list if i > 0) + max_spread])
        except ValueError:
            return []
    
    # Go to url
    multi_log(obj, 'Getting player data...')
    og_url = starting_url
    if 'sort' not in starting_url:
        starting_url = starting_url + '&sort=TotalIGS&order=asc'
    obj.location = 'futbin'
    # Grab all data from tables, hit next page until it can't any more, turn data into list of player dicts
    all_results = parse_futbin_tables(obj, starting_url, ignore_untradeable=True, fast=True)
    if len(all_results) >= min_players:
        multi_log(obj, 'Analyzing player data...')
        # Go though list of dicts, put all filters into available_x
        available_quality = []
        available_position = []
        available_nation = []
        available_league = []
        available_club = []
        ignore_quality = ['SBC']
        for result in all_results:
            if result.get('quality', None) and result.get('quality', None) not in available_quality and 'version' not in og_url and result['quality'] not in ignore_quality:
                available_quality.append(result['quality'])
            if result.get('position', None) and result.get('position', None) not in available_position and 'position' not in og_url:
                available_position.append(result['position'])
            if result.get('nation', None) and result.get('nation', None) not in available_nation and 'nation' not in og_url:
                available_nation.append(str(result['nation']))
            if result.get('league', None) and result.get('league', None) not in available_league and 'league' not in og_url and 'club' not in og_url:
                if ('version' in og_url and result['league'] != '2118') or 'version=all_specials' in og_url or 'version' not in og_url:
                    available_league.append(str(result['league']))
            if result.get('club', None) and result.get('club', None) not in available_club and 'club' not in og_url and result.get('club', None) != '112658':
                available_club.append(str(result['club']))
        # Arrange into appropriate filter groups
        singles = []
        doubles = []
        triples = []
        quads = []
        # Compare Quality permutations
        try:
            for q in available_quality:
                for p in available_position:
                    for n in available_nation:
                        for l in available_league:
                            prices = []
                            for player in all_results:
                                if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                                    if player['quality'] == q and player['position'] == p and player['nation'] == n \
                                            and player['league'] == l:
                                        prices.append(player['price'])
                                elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                                    if player['quality'] == q and player['position'] == p and player['nation'] == n \
                                            and player['league'] == l:
                                        prices = []
                                        break
                            prices = adjust_prices(prices)
                            if len(prices) >= min_players:
                                mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                                if std < mean:
                                    quads.append(([('quality', q), ('position', p), ('nation', n), ('league', l)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                        for c in available_club:
                            prices = []
                            for player in all_results:
                                if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                                    if player['quality'] == q and player['position'] == p and player['nation'] == n \
                                            and player['club'] == c:
                                        prices.append(player['price'])
                                elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                                    if player['quality'] == q and player['position'] == p and player['nation'] == n \
                                            and player['club'] == c:
                                        prices = []
                                        break
                            prices = adjust_prices(prices)
                            if len(prices) >= min_players:
                                mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                                if std < mean:
                                    quads.append(([('quality', q), ('position', p), ('nation', n), ('club', c)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                        prices = []
                        for player in all_results:
                            if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                                if player['quality'] == q and player['position'] == p and player['nation'] == n:
                                    prices.append(player['price'])
                            elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                                if player['quality'] == q and player['position'] == p and player['nation'] == n:
                                    prices = []
                                    break
                        prices = adjust_prices(prices)
                        if len(prices) >= min_players:
                            mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                            if std < mean:
                                triples.append(([('quality', q), ('position', p), ('nation', n)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                    for l in available_league:
                        prices = []
                        for player in all_results:
                            if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                                if player['quality'] == q and player['position'] == p and player['league'] == l:
                                    prices.append(player['price'])
                            elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                                if player['quality'] == q and player['position'] == p and player['league'] == l:
                                    prices = []
                                    break
                        prices = adjust_prices(prices)
                        if len(prices) >= min_players:
                            mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                            if std < mean:
                                triples.append(([('quality', q), ('position', p), ('league', l)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                    for c in available_club:
                        prices = []
                        for player in all_results:
                            if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                                if player['quality'] == q and player['position'] == p and player['club'] == c:
                                    prices.append(player['price'])
                            elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                                if player['quality'] == q and player['position'] == p and player['club'] == c:
                                    prices = []
                                    break
                        prices = adjust_prices(prices)
                        if len(prices) >= min_players:
                            mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                            if std < mean:
                                triples.append(([('quality', q), ('position', p), ('club', c)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                    prices = []
                    for player in all_results:
                        if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                            if player['quality'] == q and player['position'] == p:
                                prices.append(player['price'])
                        elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                            if player['quality'] == q and player['position'] == p:
                                prices = []
                                break
                    prices = adjust_prices(prices)
                    if len(prices) >= min_players:
                        mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                        if std < mean:
                            doubles.append(([('quality', q), ('position', p)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                for n in available_nation:
                    for l in available_league:
                        prices = []
                        for player in all_results:
                            if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                                if player['quality'] == q and player['nation'] == n and player['league'] == l:
                                    prices.append(player['price'])
                            elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                                if player['quality'] == q and player['nation'] == n and player['league'] == l:
                                    prices = []
                                    break
                        prices = adjust_prices(prices)
                        if len(prices) >= min_players:
                            mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                            if std < mean:
                                triples.append(([('quality', q), ('nation', n), ('league', l)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                    for c in available_club:
                        prices = []
                        for player in all_results:
                            if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                                if player['quality'] == q and player['nation'] == n and player['club'] == c:
                                    prices.append(player['price'])
                            elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                                if player['quality'] == q and player['nation'] == n and player['club'] == c:
                                    prices = []
                                    break
                        prices = adjust_prices(prices)
                        if len(prices) >= min_players:
                            mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                            if std < mean:
                                triples.append(([('quality', q), ('nation', n), ('club', c)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                    prices = []
                    for player in all_results:
                        if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                            if player['quality'] == q and player['nation'] == n:
                                prices.append(player['price'])
                        elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                            if player['quality'] == q and player['nation'] == n:
                                prices = []
                                break
                    prices = adjust_prices(prices)
                    if len(prices) >= min_players:
                        mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                        if std < mean:
                            doubles.append(([('quality', q), ('nation', n)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                for l in available_league:
                    prices = []
                    for player in all_results:
                        if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                            if player['quality'] == q and player['league'] == l:
                                prices.append(player['price'])
                        elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                            if player['quality'] == q and player['league'] == l:
                                prices = []
                                break
                    prices = adjust_prices(prices)
                    if len(prices) >= min_players:
                        mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                        if std < mean:
                            doubles.append(([('quality', q),  ('league', l)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                for c in available_club:
                    prices = []
                    for player in all_results:
                        if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                            if player['quality'] == q and player['club'] == c:
                                prices.append(player['price'])
                        elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                            if player['quality'] == q and player['club'] == c:
                                prices = []
                                break
                    prices = adjust_prices(prices)
                    if len(prices) >= min_players:
                        mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                        if std < mean:
                            doubles.append(([('quality', q), ('club', c)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                prices = []
                for player in all_results:
                    if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                        if player['quality'] == q:
                            prices.append(player['price'])
                    elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                        if player['quality'] == q:
                            prices = []
                            break
                prices = adjust_prices(prices)
                if len(prices) >= min_players:
                        mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                        if std < mean:
                            singles.append(([('quality', q)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
            # Compare Position permutations
            for p in available_position:
                for n in available_nation:
                    for l in available_league:
                        prices = []
                        for player in all_results:
                            if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                                if player['position'] == p and player['nation'] == n and player['league'] == l:
                                    prices.append(player['price'])
                            elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                                if player['position'] == p and player['nation'] == n and player['league'] == l:
                                    prices = []
                                    break
                        prices = adjust_prices(prices)
                        if len(prices) >= min_players:
                            mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                            if std < mean:
                                quads.append(([('position', p), ('nation', n), ('league', l)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                    for c in available_club:
                        prices = []
                        for player in all_results:
                            if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                                if player['position'] == p and player['nation'] == n and player['club'] == c:
                                    prices.append(player['price'])
                            elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                                if player['position'] == p and player['nation'] == n and player['club'] == c:
                                    prices = []
                                    break
                        prices = adjust_prices(prices)
                        if len(prices) >= min_players:
                            mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                            if std < mean:
                                quads.append(([('position', p), ('nation', n), ('club', c)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                prices = []
                for player in all_results:
                    if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                        if player['position'] == p and player['nation'] == n:
                            prices.append(player['price'])
                    elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                        if player['position'] == p and player['nation'] == n:
                            prices = []
                            break
                prices = adjust_prices(prices)
                if len(prices) >= min_players:
                    mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                    if std < mean:
                        doubles.append(([('position', p), ('nation', n)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                for l in available_league:
                    prices = []
                    for player in all_results:
                        if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                            if player['position'] == p and player['league'] == l:
                                prices.append(player['price'])
                        elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                            if player['position'] == p and player['league'] == l:
                                prices = []
                                break
                    prices = adjust_prices(prices)
                    if len(prices) >= min_players:
                        mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                        if std < mean:
                            doubles.append(([('position', p), ('league', l)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                for c in available_club:
                    prices = []
                    for player in all_results:
                        if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                            if player['position'] == p and player['club'] == c:
                                prices.append(player['price'])
                        elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                            if player['position'] == p and player['club'] == c:
                                prices = []
                                break
                    prices = adjust_prices(prices)
                    if len(prices) >= min_players:
                        mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                        if std < mean:
                            doubles.append(([('position', p), ('club', c)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                prices = []
                for player in all_results:
                    if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                        if player['position'] == p:
                            prices.append(player['price'])
                    elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                        if player['position'] == p:
                            prices = []
                            break
                prices = adjust_prices(prices)
                if len(prices) >= min_players:
                    mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                    if std < mean:
                        singles.append(([('position', p)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
            # Compare Nation permutations
            for n in available_nation:
                for l in available_league:
                    prices = []
                    for player in all_results:
                        if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                            if player['nation'] == n and player['league'] == l:
                                prices.append(player['price'])
                        elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                            if player['nation'] == n and player['league'] == l:
                                prices = []
                                break
                    prices = adjust_prices(prices)
                    if len(prices) >= min_players:
                        mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                        if std < mean:
                            doubles.append(([('nation', n), ('league', l)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                for c in available_club:
                    prices = []
                    for player in all_results:
                        if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                            if player['nation'] == n and player['club'] == c:
                                prices.append(player['price'])
                        elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                            if player['nation'] == n and player['club'] == c:
                                prices = []
                                break
                    prices = adjust_prices(prices)
                    if len(prices) >= min_players:
                        mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                        if std < mean:
                            doubles.append(([('nation', n), ('club', c)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
                prices = []
                for player in all_results:
                    if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                        if player['nation'] == n:
                            prices.append(player['price'])
                    elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                        if player['nation'] == n:
                            prices = []
                            break
                prices = adjust_prices(prices)
                if len(prices) >= min_players:
                    mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                    if std < mean:
                        singles.append(([('nation', n)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
            # Compare League
            for l in available_league:
                prices = []
                for player in all_results:
                    if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                        if player['league'] == l:
                            prices.append(player['price'])
                    elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                        if player['league'] == l:
                            prices = []
                            break
                prices = adjust_prices(prices)
                if len(prices) >= min_players:
                    mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                    if std < mean:
                        singles.append(([('league', l)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
            # Compare Club
            for c in available_club:
                prices = []
                for player in all_results:
                    if player['price'] >= min_price or (include_zeroes and player['price'] == 0):
                        if player['club'] == c:
                            prices.append(player['price'])
                    elif player['price'] < min_price or (not include_zeroes and player['price'] == 0):
                        if player['club'] == c:
                            prices = []
                            break
                prices = adjust_prices(prices)
                if len(prices) >= min_players:
                    mean, std = int(round(float(np.mean(prices)))), int(round(float(np.std(prices))))
                    if std < mean:
                        singles.append(([('club', c)], len(prices), min(i for i in prices if i > 0), mean, std, sorted(prices)))
            multi_log(obj, 'Done finding filters', notify=True, icon_url='https://cdn3.iconfinder.com/data/icons/gray-toolbar-2/512/filter_stock_funnel_filters-128.png')
            print('-' * 100)
        except KeyError as e:
            print(e)
            print(player)

        # Sort lists by # players
        singles = sorted(singles, reverse=True, key=lambda x: x[1])
        doubles = sorted(doubles, reverse=True, key=lambda x: x[1])
        triples = sorted(triples, reverse=True, key=lambda x: x[1])
        quads = sorted(quads, reverse=True, key=lambda x: x[1])

        def print_filters(name, filters):
            filter_log = ''
            print('')
            print('-' * 100)
            time = 'TIMESTAMP: {}'.format(datetime.now())
            print(time)
            print(og_url)
            header = '{}{} Filters{}'.format(Colors.bold, name.title(), Colors.reset)
            print(header)
            categories = '{}{!s:<100} {:<11} {:<11} {:<8} {:<8} {:<130} {!s:<100}{}'.format(Colors.bold, 'Filters', '# Players', 'Min Price', 'Avg', 'Std. Dev', 'Prices', 'Futbin Link', Colors.reset)
            print(categories)
            filter_log += '-' * 100 + linesep
            filter_log += time + linesep
            filter_log += og_url + linesep
            filter_log += header + linesep
            filter_log += categories + linesep
            for x in filters:
                link, f_text = get_futbin_url(x[0], og_url)
                output = '{!s:<100} {:<11} {:<11} {:<8} {:<8} {!s:<130} {!s:<100}'.format(f_text, x[1], x[2], x[3], x[4], x[5], link)
                print(output)
                filter_log += output + linesep
        print_filters('single', singles)
        print_filters('double', doubles)
        print_filters('triple', triples)
        print_filters('quadruple', quads)
    obj.close_tab()



