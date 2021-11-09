from cogs.aternos.status import *
from cogs.aternos.exceptions import *

import requests
from bs4 import BeautifulSoup
import js2py
import random
from string import ascii_lowercase, digits
import time
import re
import base64

from threading import Thread
import asyncio
from discord import Embed
from discord.ext import tasks

__all__ = (
    'Aternos',
    'Server'
)


class Aternos:
    def __init__(self, session_id) -> None:
        self._cookies = {
            "ATERNOS_SESSION": session_id
        }

        self._headers = requests.utils.default_headers()
        self._headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36"
        })

    def __getitem__(self, item):
        if item == 0:
            return self.servers
        return self.servers[item - 1]

    _last_read = 0
    _html = None
    @property
    def html(self):
        if not self._html or time.time() - self._last_read > 1:  # reusing recently generated html
            ret = requests.get(url='https://aternos.org/servers/', headers=self._headers, cookies=self._cookies, timeout=10)
            self._last_read = time.time()
            self._html = BeautifulSoup(ret.content, 'lxml')
        return self._html

    @property
    def servers(self):
        server_ids = self.html.find_all('div', class_='server-id')
        session_id = self._cookies['ATERNOS_SESSION']
        return [Server(session_id, server_id.get_text(strip=True).strip('#')) for server_id in server_ids]

    @property
    def embed(self) -> Embed:
        embed = Embed(title='List of servers')
        for i, server in enumerate(self.servers, start=1):
            embed.add_field(name='\u200b', value=f'`{i}.` {server.ip} | `{server.status}`', inline=False)
        return embed


class Server:
    TOKEN_SCRIPT_REGEX = re.compile(r'\(\(\) => {(window\[.+])=(window\[.+])\?(.+):(.+);}\)\(\);')
    IP_REGEX = re.compile(r'\w+\.\w+\.\w+')

    def __init__(self, session_id, server_id) -> None:
        self._cookies = {
            "ATERNOS_SESSION": session_id,
            "ATERNOS_SERVER": server_id
        }

        self._headers = requests.utils.default_headers()
        self._headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36"
        })

    @staticmethod
    # two length 16 base 36 strings separated by ":"
    def _generate_sec() -> str:
        # generate randomized length n base 36 string
        def random_string(n):
            return ''.join(random.choice(ascii_lowercase + digits) for _ in range(n))

        key, value = random_string(16), random_string(16)
        return key + ':' + value

    _last_read = 0
    _html = None
    @property
    def html(self):
        if time.time() - self._last_read > 1:  # reusing recently generated html (if the last html is generated
            ret = requests.get(url='https://aternos.org/server/', headers=self._headers, cookies=self._cookies, timeout=10)
            self._html = BeautifulSoup(ret.content, 'lxml')
            self._last_read = time.time()
        return self._html

    _token = None
    @property
    def token(self):
        if not self._token:  # use old token if it is generated before
            # create new token, if exception (js2py doesn't support with es6 syntax), do recursion until no error
            try:
                js_script = self.html.select('script[type="text/javascript"]')[1].get_text()  # get the "encoded" js
                actual_token = self.TOKEN_SCRIPT_REGEX.match(js_script)[3]  # regex the token js script

                # defining atob for js2py
                def atob(s):
                    return base64.b64decode(s).decode('utf-8')  # decode base64, and convert to string

                context = js2py.EvalJs({'atob': atob})  # adding atob to js2py
                self._token = context.eval(actual_token)  # evaluate js
            except js2py.PyJsException:  # if js is in es6, do the whole thing again
                return self.token
        return self._token

    @property
    def status(self):
        html = self.html  # keep html instance for use later (checking estimated time if status is in queue)
        status = html.find('span', class_='statuslabel-label').get_text(strip=True)
        match status:
            case 'Online':
                return Online()
            case 'Offline':
                return Offline()
            case 'Crashed':
                return Crashed()
            case 'Loading ...':
                return Loading()
            case 'Preparing ...':
                return Preparing()
            case 'Starting ...':
                return Starting()
            case 'Restarting ...':
                return Restarting()
            case 'Stopping ...':
                return Stopping()
            case 'Saving ...':
                return Saving()
            case 'Waiting in queue':
                est = html.find('span', class_='queue-time').get_text(strip=True)
                return WaitingInQueue(est)

    @property
    def ip(self):
        ip = self.html.find('div', class_='server-ip').find(string=self.IP_REGEX).get_text(strip=True)
        return ip

    @property
    def players(self):
        players = self.html.find('span', id='players').get_text(strip=True)
        return players

    @property
    def software(self):
        software = self.html.find('span', id='software').get_text(strip=True)
        return software

    @property
    def version(self):
        version = self.html.find('span', id='version').get_text(strip=True)
        return version

    @property
    def _params(self) -> dict:
        params = {
            "SEC": self._generate_sec(),
            "TOKEN": self.token
        }
        return params

    def start(self, callback=None):
        # Check the status to exit early if it's status is not offline
        match self.status:
            case Offline():
                pass
            case status:
                raise ServerNotOffline(f'Server\'s {status}')

        params = self._params
        params.update({
            "headstart": 0,
            "access-credit": 0
        })

        key, value = params['SEC'].split(':')
        cookies = self._cookies
        cookies[f'ATERNOS_SEC_{key}'] = value

        ret = requests.get('https://aternos.org/panel/ajax/start.php', params=params, cookies=cookies, headers=self._headers, timeout=10)
        ret.raise_for_status()

        match ret.json():
            case {'success': True}:
                Thread(target=self.confirm_thread).start()  # auto confirmation

                if callback:
                    # callback type handling
                    if asyncio.iscoroutinefunction(callback):
                        self.awhen_online.start(callback=callback)
                    else:
                        Thread(target=self.when_online, args=(callback,)).start()
                return True
            case {'success': False, 'error': 'eula'}:  # handle first time starting, eula confirmation
                self.eula()
                if not self.start(callback):  # start server again and check if successful
                    return False
                return True
            case {'success': False}:
                return False

    def stop(self):
        # Check the status to exit early if it's status is not online, starting or waiting in queue
        match self.status:
            case Online() | Starting() | WaitingInQueue():
                pass
            case status:
                raise ServerNotOnline(f'Server\'s {status}')

        params = self._params

        key, value = params['SEC'].split(':')
        cookies = self._cookies
        cookies[f'ATERNOS_SEC_{key}'] = value

        ret = requests.get('https://aternos.org/panel/ajax/stop.php', params=params, cookies=cookies, headers=self._headers, timeout=10)
        ret.raise_for_status()
        match ret.json():
            case {'success': True}:
                return True
            case {'success': False}:
                return False

    def restart(self, callback=None):
        # Check the status to exit early if it's status is not online
        match self.status:
            case Online():
                pass
            case status:
                raise ServerNotOnline(f'Server\'s {status}')

        params = self._params

        key, value = params['SEC'].split(':')
        cookies = self._cookies
        cookies[f'ATERNOS_SEC_{key}'] = value

        ret = requests.get('https://aternos.org/panel/ajax/restart.php', params=params, cookies=cookies, headers=self._headers, timeout=10)
        ret.raise_for_status()

        if callback:
            # callback type handling
            if asyncio.iscoroutinefunction(callback):
                self.awhen_online.start(callback=callback)
            else:
                Thread(target=self.when_online, args=(callback,)).start()
        return True

    def confirm(self):
        # Check the status to exit early if it's status is not waiting in queue
        match self.status:
            case WaitingInQueue():
                pass
            case status:
                raise ServerNotInQueue(f'Server\'s {status}')

        params = self._params

        key, value = params['SEC'].split(':')
        cookies = self._cookies
        cookies[f'ATERNOS_SEC_{key}'] = value

        ret = requests.get('https://aternos.org/panel/ajax/confirm.php', params=params, cookies=cookies, headers=self._headers, timeout=10)
        ret.raise_for_status()
        return True

    def eula(self):
        params = self._params

        key, value = params['SEC'].split(':')
        cookies = self._cookies
        cookies[f'ATERNOS_SEC_{key}'] = value

        ret = requests.get('https://aternos.org/panel/ajax/eula.php', params=params, cookies=cookies, headers=self._headers, timeout=10)
        ret.raise_for_status()
        match ret.json():
            case {'success': True}:
                return True
            case {'success': False}:
                return False

    def confirm_thread(self):
        while True:
            time.sleep(4)

            match self.status:
                case Offline() | Online() | Loading():
                    return
                case WaitingInQueue():
                    self.confirm()

    def when_online(self, callback):
        while True:
            time.sleep(4)

            match self.status:
                case Offline():
                    return
                case Online():
                    callback()
                    return

    # asynchronous version of when_online
    @tasks.loop(count=1)
    async def awhen_online(self, callback):
        while True:
            await asyncio.sleep(4)

            match self.status:
                case Offline():
                    return
                case Online():
                    await callback()
                    return

    @property
    def embed(self) -> Embed:
        status = self.status

        embed = Embed(title=self.ip, color=status.COLOR)
        embed.add_field(name='Status', value=str(status))

        match status:
            case Online():
                embed.add_field(name='Players', value=self.players)
            case WaitingInQueue():
                embed.add_field(name='EST', value=status.est)

        embed.add_field(name='Software', value=f'{self.software} {self.version}')
        return embed
