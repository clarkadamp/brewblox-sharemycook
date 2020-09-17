import uuid
from typing import Set, Sequence

from aiohttp import ClientResponse
from aiohttp.client import ClientSession
from brewblox_service import brewblox_logger, repeater
from cached_property import cached_property

from brewblox_sharemycook.controllers import controller_types, Controller, TemperatureUnits
from brewblox_sharemycook.scraping import glean_device_ids, get_csrf_token, bs_ify, glean_temperature_units

LOGGER = brewblox_logger(__name__)

SHARE_MY_COOK = 'https://sharemycook.com'


def authenticate(func):
    async def wrapper(self, *args, **kwargs):
        response = await func(self, *args, **kwargs)
        # If you are not logged in, there will be a redirect to the login page, check for it, login, retry
        if response.history:
            if response.history[0].status == 302:
                if response.history[0].headers.get('Location').startswith('/Login'):
                    await self.login()
                    response = await func(self, *args, **kwargs)

        return response

    return wrapper


class ShareMyCook:

    def __init__(self, session: ClientSession, username: str, password: str) -> None:
        self.session = session
        self.username = username
        self.password = password

    async def poll(self) -> Sequence[Controller]:
        results = []
        for device_id in await self.device_ids:
            results.append(await self.poll_device(device_id))
        return results

    @cached_property
    async def device_ids(self) -> Set[uuid.UUID]:
        devices_page = await self.get(f'{SHARE_MY_COOK}/account/customerdevice')
        device_ids = glean_device_ids(await bs_ify(devices_page))
        LOGGER.debug(f'Discovered {len(device_ids)} device(s): {", ".join(sorted(str(u) for u in device_ids))}')
        return device_ids

    @authenticate
    async def get(self, url: str) -> ClientResponse:
        LOGGER.debug(f'GET {url}')
        return await self.session.get(url)

    async def poll_device(self, device_id: uuid.UUID) -> Controller:
        response = await self.get(f'{SHARE_MY_COOK}/account/customerdevice/temperatures_read?id={device_id}')
        json = await response.json()
        return controller_types[json['bbqGuruDeviceModel']].from_json(
            device_id, await self.temperature_units, await response.json()
        )

    @cached_property
    async def temperature_units(self) -> TemperatureUnits:
        profile_page = await self.get(f'{SHARE_MY_COOK}/Account/Profile')
        raw_units = glean_temperature_units(await bs_ify(profile_page))
        units = TemperatureUnits(raw_units.upper())
        LOGGER.info(f'Temperature units are in {units.value}')
        return units

    async def login(self) -> None:
        login_page = await self.session.get(SHARE_MY_COOK)
        login_response = await self.session.post(
            f'{SHARE_MY_COOK}/Login',
            data={
                'Username': self.username,
                'Password': self.password,
                '__RequestVerificationToken': get_csrf_token(await bs_ify(login_page)),
            }
        )
        if login_response.history and login_response.history[0].status == 302:
            LOGGER.info(f'Successfully logged in {self.username} to {SHARE_MY_COOK}')
            return
        LOGGER.error(f'Unable to login with {self.username}/{"*" * len(self.password)}')
        raise repeater.RepeaterCancelled()
