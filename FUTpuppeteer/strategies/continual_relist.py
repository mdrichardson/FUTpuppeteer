from FUTpuppeteer.misc import multi_log
from random import uniform as rand
from . import retry_decorator


@retry_decorator
def continual_relist(obj, ignore_tradepile=False):
    current_location = obj.location
    previous_length = 0
    while True or ignore_tradepile:
        obj.current_strategy = 'Continual Relist'
        multi_log(obj, 'Reached maximum tradepile capacity. Entering relist-only mode...')
        obj.clear_sold()
        obj.relist_all()
        items = obj.__get_items__(get_price=False)
        min_expire = 60 * 60
        for item in items:
            if item['time_left'] < min_expire:
                min_expire = item['time_left']
        if len(items) < previous_length and not ignore_tradepile:
            break
        else:
            previous_length = len(items)
            obj.keep_alive(rand(min_expire, min_expire + (15 * 60)))
    obj.go_to(current_location)
