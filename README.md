# FUTpuppeteer FIFA 18 Ultimate Team Bot

*__Note: This repo is not meant for the public. You're welcome to use it, but I am not providing support and you'll need to be semi-experienced with Python to get it running.__*

This is an auto-clicker bot used to trade players and items on FIFA Ultimate Team's Web App.

## Key Features

* Set-and-forget: runs *everything* automatically.
* Can buy and sell players and some consumables using Buy It Now and/or auctions
* Gathers SBC solutions, buys the players, and enters them into SBC solution, automatically
* Can automatically manage transfer, watch, and unassigned lists
* Contains *numerous* strategies that can be customized easily
* Desktop and AutoRemote (Android app) notifications

## Technical Features

* Contains rate limiting and keep-alive function so that it can run continuously without getting "caught"
* Notifications for captcha, buy, sell, etc
* Fairly verbose logging and console output
* Price checks with Futbin or Futhead
* Saves price data and user buy/sell data in sqlite database
* IMAP support: can auto-login with 2-factor email authentication

## Limitations

* Stores your password on your in plain text. Watch out!
* Uses Selenium. This is slower than using requests, but significantly harder to get caught. This can also cause issues on slow machines and/or connections. 
  * Try changing `lag_multiplier` in `global.yml` to something larger if your comupter or connection are slow.
* FUT web app does not differentiate well between similar cards of the same player (e.g. Gold Diego Costa with a club change). 
  * In order to accurately get the price, all player card possibilities are grabbed from EA database. Cards in web app are then compared with those in database and closest match is returned. This is slightly slow.
* EA database must be manually updated. It takes ~10 minutes to complete. You can update it manually by executing `update_player_data()` in `database.py`.

## Installation

### Requirements

* [Python 3.5+](https://www.python.org/downloads/) (only tested in v3.5)
* [Chromedriver 2.39+](http://chromedriver.chromium.org/downloads) (only tested in v2.39)
* Python packages:
  * selenium
  * ruamel.YAML
  * signal
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

- [ ] Add readmes to each folder
- [ ] Clean up code, refactor as necessary
- [ ] Test

## Needs to be done, but won't be unless I pick the project back up

- [ ] Don't save passwords in plain text
- [ ] Completely refactor to use [FUTapi](https://github.com/futapi/fut) instead of Selenium
  * The increased likelihood of being caught is worth the increased speed
- [ ] Write unit tests
