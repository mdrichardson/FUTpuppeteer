# FUTpuppeteer/FUTpuppeteer/strategies

Settings for each strategy are determined in `config/bot*.yml`. User is not meant to call any of these directly. Below is an explanation for each strategy:

## __init__

Contains strategies that are called on a more recurring basis, rather than directly. Also contains common functions between other strategies.

## acquire

Used to try over and over to acquire a single player. Once acquired, stops. This strategy is called automatically while using the bot to complete SBCs.

## amass

Bids for as many of a list of players as possible.

## arbitrage

Looks at prices of players on Futbin and Futhead. If there's a profitable difference, buys profitable players and attempts to sell.

## bpm

Bronze Pack Method. Google it for more information; it's a popular beginner strategy.

## check_unlock

New FIFA accounts start locked. You can run this and it will notify you when your account unlocks.

## coin_transfer_finish_prep

Part of the Coin Transfer strategy. It runs another bot in the background in order to finish the coin transfer.

## coin_transfer_finish

Part of the Coin Transfer strategy. This is what the buying bot uses to buy the player from the coin transfer.

## coin_transfer_list

Part of the Coin Transfer strategy. This lists the player for coin transfer.

## coin_transfer_prep

Part of the Coin Transfer strategy. This buys good players for coin transferring

## consumable_amass

Bids for as many of a consumable as possible.

## continual_relist

Lists your transfer items over and over.

## filter_amass

Bids for as many players in a filter search as possible.

## filter_finder

Searches futbin to help you find profitable filters (e.g. `Gold` `Center Backs` in `Premier League` from `Brazil`). It prints the results in the console and you can directly copy/paste them into `/config/bot*.yml`

## filter_snipe

Buy It Now's all players that show in results of a filter search.

## futbin_cheapest_sbc

Finds the cheapest solution to an SBC on Futbin. Isn't really needed if you're using the sbc solver.

## futbin_market

Uses Futbin's market momentum to make buys. I haven't found this to be profitable. Maybe you will with different settings.

## hunt

Mass-bids on a single player.

## market_monitor

Gets market rate from Futbin over a period of time and saves it to `user_db.sqlite`. You can use this to help you find good targets and when to target them.

## price_fix

Mass-buys a player through both snipes and bids and lists them at higher than market price.

## relist_individually

Relists players from your transfer list indiviually based on market price.

## sbc_hunt

Finds popular players in SBCs and `hunt`s for them.

## sell_club_players

Sells all of your Bronze, Silver, or Gold players. Players can be excluded by player_id.

## sell_transfer_targets_at_market

Sells all of your transfer targets at the market rate.

## silver_flip

Searches for popular silvers in SBCs, then `amass`es and `snipe`s them

## snipe

Buys players immediately using Buy It Now.