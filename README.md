# FUTpuppeteer FIFA 18 Ultimate Team Bot

*__Note: This repo is not meant for the public. You're welcome to use it, but I am not providing support and you'll need to be semi-experienced with Python to get it running.__*

This is an auto-clicker bot used to trade players and items on FIFA Ultimate Team's Web App.

Click this image for a video demo that covers a few capabilities:
[![FUTpuppeteer Demo](https://i.imgur.com/TsWZ6hb.jpg)](https://streamable.com/9616t)

## Key Features

* Set-and-forget: runs *everything* automatically.
* Can buy and sell players and some consumables using Buy It Now and/or auctions
* Gathers SBC solutions, buys the players, and enters them into SBC solution, automatically
* Can automatically manage transfer, watch, and unassigned lists
* Can apply consumables to each individual member in any squad, optionally including subs and reserves (individual fitness, contracts, etc.)
* Contains *numerous* strategies that can be customized easily
* Desktop and AutoRemote (Android app) notifications
* Stealth:
  * There was a big ban wave in early 2018. The commercial bots got hit. This one did not.
  * Uses randomized delays and off-center clicking to mimic human interactions
  * Uses randomized keep-alive
  * Customizeable maximum rate of user server requests
  * You can compile chromedriver yourself [here](https://chromium.googlesource.com/chromium/src/+/master/docs/windows_build_instructions.md) and change `key` in `call_function.js` to something random, [as seen here](https://stackoverflow.com/a/41220267/7729352)

## Technical Features

* Notifications for captcha, buy, sell, etc
* Fairly verbose logging and console output
* Price checks with Futbin or Futhead
* Saves price data and user buy/sell data in sqlite database
* IMAP support: can auto-login with 2-factor email authentication
* Passwords are saved locally using OS's credential manager. They can optionally be encrypted with a master password

## Limitations

* Runs on Selenium to mimic human interactions for better stealth. This requires higher CPU and RAM usage as well as additional delays due to page load times that you wouldn't see with something that uses EA's API directly.  
  * Try changing `lag_multiplier` in `global.yml` to something larger if you get errors because your comupter or connection are slow.
* FUT web app doesn't differentiate well between similar cards of the same player (e.g. Gold Diego Costa with a club change).
  * In order to accurately get the price of the right card, all player card possibilities are grabbed from EA database and stored locally. Cards that appear in web app searches are then compared with those in the database and the closest match is returned. This is slightly slow and you will often be out-sniped by API-only bots.  
  * When FIFA was first released, this wasn't an issue. But as more and more new card variations were released, this was the only way to solve this issue without direct API calls (which are less stealthy).
* EA database must be manually updated. It takes ~10 minutes to complete. You can update it manually by executing `update_player_data()` in `database.py`.

## Installation

### Requirements

* [Python 3.5+](https://www.python.org/downloads/) (only tested in v3.5)
* [Chromedriver 2.39+](http://chromedriver.chromium.org/downloads) (only tested in v2.39)
* Python packages:
  * selenium
  * ruamel.YAML
  * signal
  * simple-crypt
  * requests
  * sqlite3
  * ast
  * json
  * re
* Fast computer and internet connection
* An understanding of Python

### Steps to Install

1. Install Python, Chromedriver, and Python packages
2. Pull or clone this repo

3. Rename `config\botExample.yml` to `bot1.yml`
    * Open it and input your user info at the bottom
4. Rename `config\globalExample.yml` to `global.yml`
    * Input appropriate `path_to_chromedriver_exe`
    * Change other settings as needed
5. Edit `RunExample.py` to your liking
    * There's a lot of examples in there. Comment in what you want to run and comment out what you don't. Read the code and change as necessary

## To-Do

- [X] Add readmes to each folder
- [X] Add gif that shows bot operate
- [ ] Clean up code, refactor as necessary
- [ ] Test

## Needs to be done, but won't be unless I pick the project back up

- [ ] Make install easier
- [ ] Have it create databases from scratch
- [ ] Have it auto-generate blank `bot*.yml` if `Session(bot_number=*)` doesn't exist
- [ ] Store all settings in database, instead of yaml files
- [ ] Completely refactor to use [oczkers' FUT API wrapper](https://github.com/futapi/fut) instead of Selenium
  * The increased likelihood of being caught is worth the increased speed, unless web app security increases significantly in the future
    * Increased risk can be mitigated by frequently running a separate bot that logs in via Selenium (like this one) and compares all HTTP method parameters and cookies using BrowserProxyMob to make sure they match what oczker's API is sending
- [ ] Write unit tests
