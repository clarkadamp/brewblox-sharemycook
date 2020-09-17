from textwrap import dedent

import pytest
from aiohttp import web, ClientSession
from aresponses import ResponsesMockServer

from brewblox_sharemycook.share_my_cook import ShareMyCook


@pytest.fixture
def smc_username():
    return 'username'


@pytest.fixture
def smc_password():
    return 'password'


@pytest.fixture
def main_page_content():
    return dedent("""\
    <html>
        <form action="/Login">
            <input name="__RequestVerificationToken" value="TOKEN" />
        </form>
    </html>
    """)


@pytest.fixture
async def share_my_cook(smc_username, smc_password):
    session = await ClientSession(raise_for_status=True).__aenter__()
    yield ShareMyCook(session, smc_username, smc_password)
    await session.close()


@pytest.fixture
def provision_login_responses(aresponses: ResponsesMockServer, main_page_content):
    client_devices_location = '/account/customerdevice'

    # The normal trigger for a login
    aresponses.add(
        'sharemycook.com',
        client_devices_location,
        'GET',
        response=web.Response(
            status=302,
            headers={'Location': '/Login'}
        )
    )

    # Login will get the verification token from the main page
    aresponses.add(
        'sharemycook.com',
        '/',
        'GET',
        response=web.Response(
            body=main_page_content,
            status=200,
        )
    )

    # Perform the login
    aresponses.add(
        'sharemycook.com',
        '/Login',
        'POST',
        response=web.Response(
            status=302,
            headers={'Location': client_devices_location}
        )
    )

    # Redirect back to the original page
    aresponses.add(
        'sharemycook.com',
        client_devices_location,
        'GET',
        response=web.Response(
            status=200,
        )
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures('provision_login_responses')
async def test_login(share_my_cook):
    await share_my_cook.login()
