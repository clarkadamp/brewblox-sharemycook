import uuid
from typing import Set

from aiohttp import ClientResponse
from brewblox_service import repeater
from bs4 import BeautifulSoup


async def bs_ify(response: ClientResponse) -> BeautifulSoup:
    return BeautifulSoup(await response.text(), features='html.parser')


def get_login_form(soup: BeautifulSoup) -> BeautifulSoup:
    for form in soup.find_all('form'):
        if form.get('action') == '/Login':
            return form


def get_csrf_token(soup: BeautifulSoup) -> str:
    login_form = get_login_form(soup)
    for _input in login_form.find_all('input'):
        if _input.get('name') == '__RequestVerificationToken':
            return _input.get('value')


def glean_device_ids(soup: BeautifulSoup) -> Set[uuid.UUID]:
    device_ids = set()
    for ul in soup.find_all('ul', {'class': 'device-info-list'}):
        for a in ul.find_all('a'):
            href = a.get('href')
            if href:
                possible_uuid = href.split('/')[-1]
                try:
                    device_ids.add(uuid.UUID(possible_uuid))
                except ValueError:
                    pass
    return device_ids


def glean_temperature_units(soup: BeautifulSoup) -> str:
    _input = soup.find(id='TemperatureUnit', checked='checked')
    if _input is None:
        raise repeater.RepeaterCancelled('Unable to identify temperature units')
    return _input.get('value')
