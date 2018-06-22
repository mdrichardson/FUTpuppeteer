# -*- coding: utf-8 -*-
"""
FUTpuppeteer.notifications
~~~~~~~~~~~~~~~~~~~~~
This module implements the puppetSniper's notification functions.
"""
import requests
from .misc import Global, multi_log


def notify_all(obj, title='', message='', icon_url='http://www.futwiz.com/assets/img/fifa18/badges/888888.png', link=''):
    """
    Sends notification to everything allowed in config
    :param obj: bot/Session object
    :param title: str: Title of notification
    :param message: str: Content of notification
    :param icon_url: str: URL to icon to use in notifications. Defaults to FUT icon
    :param link: str for URL when clicking notification
    """
    if not title:
        title = ''
    if not message:
        message = ''
    if not icon_url:
        icon_url = ''
    if not link:
        link = ''
    message = str(message)
    notify_autoremote(title, message, icon_url, link)
    notify_desktop(obj, title, message, icon_url, link)


# noinspection PyPep8
def notify_autoremote(title='FUTpuppeteer Notification', message='', icon_url='http://www.futwiz.com/assets/img/fifa18/badges/888888.png', link=''):
    """
    Creates notification using autoremote Android app. Disable in config if you don't use it
    """
    if not title:
        title = ''
    if not message:
        message = ''
    if not icon_url:
        icon_url = ''
    if not link:
        link = ''
    autoremote_url = 'https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush'
    if Global.autoremote_notifications:
        multi_log(message='Notifying AutoRemote with {}'.format(message), level='debug')
        try:
            requests.get(autoremote_url + '?deviceNames=' + Global.autoremote_device_names + '&text=' + message + '&title=' + title +
                         '&icon=' + icon_url + '&apikey=' + Global.autoremote_key + '&url=' + link)
        except Exception as e:
            multi_log(message='Autoremote connection failed: {}'.format(e), level='warn')
    else:
        multi_log(message='Unable to notify. Autoremote notifications are turned off in global.yml', level='warn')


def notify_desktop(obj, title='', message='', icon_url='http://www.futwiz.com/assets/img/fifa18/badges/888888.png', link=''):
    """
    Creates a chrome desktop notification.
    """
    if not title:
        title = ''
    if not message:
        message = ''
    if not icon_url:
        icon_url = ''
    if not link:
        link = ''
    if Global.desktop_notifications:
        check_permission = 'document.addEventListener("DOMContentLoaded",function(){"granted"!==Notification.permission&&Notification.requestPermission()});'
        obj.driver.execute_script(check_permission)
        create_notification = 'if("granted"!==Notification.permission)Notification.requestPermission();else{var notification=new Notification("%s",{icon:"%s",\
            body:"%s"});notification.onclick=function(){window.open("%s")}}' % (title, icon_url, message, link)
        try:
            obj.driver.execute_script(create_notification)
        except Exception as e:
            multi_log(obj, 'Autoremote error: {}, {}{}{}{}'.format(e, title, icon_url, message, link), level='error')
    else:
        multi_log(message='Unable to notify. Desktop notifications are turned off in global.yml', level='warn')
