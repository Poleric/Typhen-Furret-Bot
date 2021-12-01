from cogs.aternos.classes import *
from cogs.aternos.exceptions import *

import requests
from bs4 import BeautifulSoup
import random
import time
import re

# for extracting token value from js scripts
import js2py
import base64
from string import ascii_lowercase, digits

# # for logging in
# from hashlib import md5

# for callbacks and discord embeds
from threading import Thread
import asyncio
from discord.ext import tasks

__all__ = (
    'Servers',
    'Server'
)


class Aternos:
    _TOKEN_SCRIPT_REGEX = re.compile(r'\(\(\) => {(window\[.+])=(window\[.+])\?(.+):(.+);}\)\(\);')

    def __init__(self, session_id):
        self._cookies = {
            "ATERNOS_SESSION": session_id
        }

        self._headers = requests.utils.default_headers()
        self._headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36"

    @staticmethod
    # two length 16 base 36 strings separated by ":"
    def _generate_sec() -> str:
        # generate randomized length n base 36 string
        def random_string(n):
            full = ''.join(random.choice(ascii_lowercase + digits) for _ in range(n))

            # convert random amount of characters from last index into 0, mimic aternos generation
            i = random.randint(3, 6)
            partial = full[:-i] + ''.join('0' for _ in range(i))
            return partial

        key, value = random_string(16), random_string(16)
        return key + ':' + value

    _token = None
    @property
    def token(self):
        if not self._token:  # use old token if it is generated before
            # create new token, if exception (js2py doesn't support with es6 syntax), do recursion until no error
            try:
                js_script = self.html('servers').select('script[type="text/javascript"]')[0].get_text()  # get the "encoded" js
                actual_token = self._TOKEN_SCRIPT_REGEX.match(js_script)[4]  # regex the token js script

                # defining atob for js2py
                def atob(s):
                    return base64.b64decode(str(s)).decode('utf-8')  # decode base64, and convert to string

                context = js2py.EvalJs({'atob': atob})  # adding atob to js2py
                self._token = context.eval(actual_token)  # evaluate js
            except js2py.PyJsException:  # if js is in es6, do the whole thing again
                return self.token
        return self._token

    @property
    def _params(self) -> dict:
        params = {
            "SEC": self._generate_sec(),
            "TOKEN": self.token
        }
        return params

    _cached_soup: dict[dict] = {}
    def html(self, options):
        if options not in self._cached_soup or self._cached_soup[options]['last_read'] > 1:  # reusing cached html
            ret = requests.get(url=f'https://aternos.org/{options}', headers=self._headers, cookies=self._cookies, timeout=10)

            ret.raise_for_status()
            if ret.url == 'https://aternos.org/go/':
                raise LogInError('User\'s not logged in')
            soup = BeautifulSoup(ret.content, 'lxml')
            if soup.find('div', class_='page-error'):
                error_type = soup.find('div', class_='page-error-title').get_text(strip=True)
                error_msg = soup.find('div', class_='page-error-message').get_text(strip=True)
                match error_type:
                    case 'Access denied.':
                        raise AccessDenied(error_msg)
                    case _:
                        raise PageError(f'{error_type}: {error_msg}')

            self._cached_soup[options] = {
                'soup': soup,
                'last_read': time.time()
            }
        return self._cached_soup[options]['soup']


class Servers(Aternos):
    def __init__(self, session_id):
        super().__init__(session_id)

    def __getitem__(self, item):
        if item == 0:
            return self.servers
        return self.servers[item - 1]

    _last_read: float = 0  # time in seconds
    _servers = None
    @property
    def servers(self):
        if time.time() - self._last_read > 14400:  # reusing old servers list if its 4 hours ago
            server_ids = self.html('servers').find_all('div', class_='server-id')
            session_id = self._cookies['ATERNOS_SESSION']
            self._servers = [Server(session_id, server_id.get_text(strip=True).strip('#')) for server_id in server_ids]
        return self._servers



class Server(Aternos):
    _IP_REGEX = re.compile(r'\w+\.\w+\.\w+')

    def __init__(self, session_id, server_id):
        super().__init__(session_id)
        self._cookies['ATERNOS_SERVER'] = server_id

    def __str__(self):
        return re.match(r'\w+', self.ip)[0]

    def __repr__(self):
        return self.ip

    @property
    def status(self):
        html = self.html('server')  # keep html instance for use later (checking estimated time if status is in queue)
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
                duration = re.search(r'\d+', est)[0]
                return WaitingInQueue(int(duration))

    @property
    def ip(self):
        ip = self.html('server').find('div', class_='server-ip').find(string=self._IP_REGEX).get_text(strip=True)
        return ip

    @property
    def player_count(self):
        player_count = self.html('server').find('span', id='players').get_text(strip=True)
        return player_count

    @property
    def software(self):
        software = self.html('server').find('span', id='software').get_text(strip=True)
        return software

    @property
    def version(self):
        version = self.html('server').find('span', id='version').get_text(strip=True)
        return version

    @property
    def players(self):
        for player in self.html('players').find_all('div', class_='players'):
            username = player.find('div', class_='playername').get_text(strip=True)
            status = player.find('div', class_='player-label').get_text(strip=True)
            yield Player(username, status)

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
            time.sleep(random.randint(5000, 15000)/1000)

            match self.status:
                case Offline() | Online() | Loading():
                    return
                case WaitingInQueue() as status:
                    if status.duration > 1:
                        time.sleep((status.duration-1) * 60)
                    self.confirm()

    def when_online(self, callback):
        # explicit wait 2 sec for aternos to process the start
        while True:
            # callback with server Status when server is
            # - online, indicating successful startup
            # - offline / crashed, indicating something went wrong
            match self.status:
                case Online() | Offline():
                    callback(self.status)
                    return
            time.sleep(10)

    # asynchronous version of when_online
    @tasks.loop(count=1)
    async def awhen_online(self, callback):
        while True:
            await asyncio.sleep(4)

            match self.status:
                case Online() | Offline():
                    await callback(self.status)
                    return
