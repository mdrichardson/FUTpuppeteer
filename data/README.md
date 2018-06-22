#FUTpuppeteer/data

## FIFA_*.json
JSON files of EA's database of *. Only partial for players because of how it gets it. Updates quickly and automatically at login

## ea_db.sqlite
SQLITE version of EA's database. Must be updated manually via `update_player_data()` in `database.py`

## user_db.sqlite
You'll probably want to wipe this first, but it stores all of your buy/sell and market info