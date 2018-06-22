from FUTpuppeteer.misc import multi_log
from random import uniform as rand


def check_unlock(obj):
    while True:
        obj.go_to('transfers')
        if len(obj.driver.find_elements_by_class_name('tileDisabledMessage')) == 0:
            multi_log(obj, 'MARKET UNLOCKED', notify=True, level='title', title='MARKET UNLOCKED')
            return True
        else:
            multi_log(obj, 'Market still locked', notify=True, level='info', title='Still locked')
            wait = rand(60 * 60, 60 * 120)
            obj.keep_alive(wait)