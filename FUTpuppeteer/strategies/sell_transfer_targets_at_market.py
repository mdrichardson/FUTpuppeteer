from . import retry_decorator, common_process_transfer_targets


@retry_decorator
def sell_transfer_targets_at_market(obj):
    obj.current_strategy = 'Sell Transfer Targets at Market'
    if obj.location != 'transfer_targets':
        obj.go_to('transfer_targets')
    common_process_transfer_targets(obj, 'sell_at_market')