import uuid
from textwrap import dedent

import pytest
from brewblox_service import repeater

from brewblox_sharemycook.scraping import bs_ify, get_csrf_token, glean_device_ids
from brewblox_sharemycook.scraping import glean_temperature_units, get_login_form

device_id = uuid.uuid4()

login_page = dedent("""\
    <html>
        <form action="/Other" method="post">
        </form>
        <form action="/Login" method="post">
            <input name="not-crsf-token" />
            <input name="__RequestVerificationToken" type="hidden" value="TOKEN" />
        </form>
    </html>""")


def test_get_csrf_token():
    assert get_csrf_token(bs_ify(login_page)) == 'TOKEN'


device_ids_page = dedent(f"""\
    <html>
        <!-- This is a real device link (UUID) -->
        <ul class="device-info-list">
            <a href="https://doesnt.matter/for/path/{device_id}">link contents</a>
        </ul>
        <!-- This is a bad device link (non UUID) -->
        <ul class="device-info-list">
            <a href="https://doesnt.matter/for/path/not-a-uuid">link contents</a>
        </ul>
        <!-- This is a malformed "a" element -->
        <ul class="device-info-list">
            <a>link contents</a>
        </ul>
    </html>""")


def test_glean_device_ids():
    assert glean_device_ids(bs_ify(device_ids_page)) == {device_id}


profile_page_c = dedent("""\
<html>
    <input id="TemperatureUnit" name="TemperatureUnit" type="radio" value="Fahrenheit" /> Fahrenheit
    <input checked="checked" id="TemperatureUnit" name="TemperatureUnit" type="radio" value="Celsius" /> Celsius
<html>""")

profile_page_f = dedent("""\
<html>
    <input checked="checked" id="TemperatureUnit" name="TemperatureUnit" type="radio" value="Fahrenheit" /> Fahrenheit
    <input id="TemperatureUnit" name="TemperatureUnit" type="radio" value="Celsius" /> Celsius
<html>""")


@pytest.mark.parametrize('content, expected_value', [
    (profile_page_c, 'Celsius'),
    (profile_page_f, 'Fahrenheit'),
])
def test_glean_temperature_units(content, expected_value):
    assert glean_temperature_units(bs_ify(content)) == expected_value


@pytest.mark.parametrize('scraper', [get_login_form, glean_temperature_units])
def test_error_raises(scraper):
    with pytest.raises(repeater.RepeaterCancelled):
        scraper(bs_ify('<html></html>'))


def test_get_csrf_token_raises():
    content = dedent("""\
    <html>
        <form action="/Login" method="post">
        </form>
    </html>""")
    with pytest.raises(repeater.RepeaterCancelled):
        get_csrf_token(bs_ify(content))
