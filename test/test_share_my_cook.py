import json
import uuid
from textwrap import dedent
from unittest.mock import MagicMock

import pytest
from aiohttp import web, ClientSession
from aresponses import ResponsesMockServer
from brewblox_service import repeater

from brewblox_sharemycook.controllers import UltraQ, controller_types, TemperatureUnits
from brewblox_sharemycook.share_my_cook import ShareMyCook, SHARE_MY_COOK

pytestmark = [pytest.mark.asyncio]

share_my_cook_host = 'sharemycook.com'

client_devices_location = '/account/customerdevice'

main_page_content = dedent("""\
    <html>
        <form action="/Login">
            <input name="__RequestVerificationToken" value="TOKEN" />
        </form>
    </html>
    """)


@pytest.fixture
def smc_username():
    return 'username'


@pytest.fixture
def smc_password():
    return 'password'


@pytest.fixture
async def share_my_cook(smc_username, smc_password):
    async with ClientSession() as session:
        yield ShareMyCook(session=session, username=smc_username, password=smc_password)


def add_successful_login_responses(aresponses: ResponsesMockServer):
    aresponses.add(
        share_my_cook_host,
        '/',
        'GET',
        response=web.Response(
            body=main_page_content,
            status=200,
        )
    )

    # Perform the login
    aresponses.add(
        share_my_cook_host,
        '/Login',
        'POST',
        response=web.Response(
            status=302,
            headers={'Location': client_devices_location}
        )
    )

    # Redirect back to the original page
    aresponses.add(
        share_my_cook_host,
        client_devices_location,
        'GET',
        response=web.Response(
            status=200,
        )
    )


async def test_login_success(share_my_cook: ShareMyCook, aresponses: ResponsesMockServer):
    add_successful_login_responses(aresponses)

    await share_my_cook.login()
    aresponses.assert_plan_strictly_followed()


async def test_login_failed(share_my_cook: ShareMyCook, aresponses: ResponsesMockServer):
    aresponses.add(
        share_my_cook_host,
        '/',
        'GET',
        response=web.Response(
            body=main_page_content,
            status=200,
        )
    )

    # Perform the login
    aresponses.add(
        share_my_cook_host,
        '/Login',
        'POST',
        response=web.Response(
            body='<html>alternative login page</html>',
            status=200,
        )
    )

    with pytest.raises(repeater.RepeaterCancelled):
        await share_my_cook.login()
    aresponses.assert_plan_strictly_followed()


@pytest.mark.parametrize('http_code, redirect_location, login_expected', [
    (302, '/Login', True),
    (302, '/Other', False),
    (301, '/Login', False),
])
async def test_authenticate_required(
    share_my_cook: ShareMyCook, aresponses: ResponsesMockServer, http_code, redirect_location, login_expected
):
    aresponses.add(
        share_my_cook_host,
        client_devices_location,
        'GET',
        response=web.Response(
            status=http_code,
            headers={'Location': redirect_location}
        )
    )
    aresponses.add(
        share_my_cook_host,
        redirect_location,
        'GET',
        response=web.Response(
            status=200,
            body='Not retried'
        )
    )
    if http_code == 302 and redirect_location == '/Login':
        add_successful_login_responses(aresponses)
        aresponses.add(
            share_my_cook_host,
            client_devices_location,
            'GET',
            response=web.Response(
                status=200,
                body='Retried after .login()'
            )
        )

    response = await share_my_cook.get(f'{SHARE_MY_COOK}{client_devices_location}')
    assert await response.text() == 'Retried after .login()' if login_expected else 'Not retried'
    aresponses.assert_plan_strictly_followed()


async def test_authenticate_not_required(share_my_cook: ShareMyCook, aresponses: ResponsesMockServer):
    aresponses.add(
        share_my_cook_host,
        client_devices_location,
        'GET',
        response=web.Response(
            status=200,
            body='Already Authenticated'
        )
    )

    response = await share_my_cook.get(f'{SHARE_MY_COOK}{client_devices_location}')
    assert await response.text() == 'Already Authenticated'
    aresponses.assert_plan_strictly_followed()


async def test_poll(monkeypatch, share_my_cook: ShareMyCook, aresponses: ResponsesMockServer):
    ultra_q = MagicMock(UltraQ)
    monkeypatch.setitem(controller_types, UltraQ.__name__, ultra_q)

    device_uuid = uuid.uuid4()
    aresponses.add(
        share_my_cook_host,
        client_devices_location,
        'GET',
        response=dedent(f"""
        <html>
            <!-- This is a real device link (UUID) -->
            <ul class="device-info-list">
                <a href="https://doesnt.matter/for/path/{device_uuid}">link contents</a>
            </ul>
            <!-- This is a bad device link (non UUID) -->
            <ul class="device-info-list">
                <a href="https://doesnt.matter/for/path/not-a-uuid">link contents</a>
            </ul>
            <!-- This is a malformed "a" element -->
            <ul class="device-info-list">
                <a>link contents</a>
            </ul>
        </html>
        """)
    )

    poll_device_data = {'bbqGuruDeviceModel': UltraQ.__name__, 'a': 'b', 'c': 'd'}

    aresponses.add(
        share_my_cook_host,
        f'/account/customerdevice/temperatures_read?id={device_uuid}',
        'GET',
        match_querystring=True,
        response=web.Response(
            body=json.dumps(poll_device_data),
            content_type='application/json',
        )
    )

    aresponses.add(
        share_my_cook_host,
        '/Account/Profile',
        'GET',
        response=dedent("""
        <html>
            <input id="TemperatureUnit" name="TemperatureUnit" type="radio" value="Fahrenheit" /> Fahrenheit
            <input checked="checked" id="TemperatureUnit" name="TemperatureUnit" type="radio" value="Celsius" /> Celsius
        </html>
        """)
    )

    await share_my_cook.poll()
    ultra_q.from_json.assert_called_once_with(device_uuid, TemperatureUnits.CELSIUS, poll_device_data)
    aresponses.assert_plan_strictly_followed()
