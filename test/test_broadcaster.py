import uuid
from datetime import datetime

import pytest
from brewblox_service import http, scheduler
from mock import AsyncMock, MagicMock

from brewblox_sharemycook import broadcaster
from brewblox_sharemycook.controllers import UltraQ, State, TemperatureUnits
from brewblox_sharemycook.share_my_cook import ShareMyCook

pytestmark = [pytest.mark.asyncio]

TESTED = broadcaster.__name__


@pytest.fixture
def m_publish(mocker):
    m = mocker.patch(TESTED + '.mqtt.publish', AsyncMock())
    return m


@pytest.fixture
def m_share_my_cook(monkeypatch):
    mock_share_my_cook = MagicMock(ShareMyCook)
    monkeypatch.setattr(f'{TESTED}.ShareMyCook', mock_share_my_cook)
    return mock_share_my_cook.return_value


@pytest.fixture
def app(app, m_publish):
    scheduler.setup(app)
    http.setup(app)
    return app


@pytest.fixture
def device_id():
    return uuid.uuid4()


@pytest.fixture
def active_device(device_id):
    return UltraQ(
        device_id=device_id,
        name='MyDeviceName',
        state=State.ONLINE,
        units=TemperatureUnits.CELSIUS,
        last_update=datetime.now(),
        pit_temp=50,
        pit_target=55,
        food1_temp=65,
        food1_target=95,
        food2_temp=66,
        food2_target=96,
        food3_temp=-500,
        food3_target=97,
        fan_duty=48
    )


@pytest.fixture
def inactive_device(device_id):
    return UltraQ(
        device_id=device_id,
        name='MyDeviceName',
        state=State.OFFLINE,
        units=TemperatureUnits.CELSIUS,
        last_update=datetime.now(),
        pit_temp=50,
        pit_target=55,
        food1_temp=65,
        food1_target=95,
        food2_temp=66,
        food2_target=96,
        food3_temp=-500,
        food3_target=97,
        fan_duty=48
    )


async def test_run(app, m_publish, m_share_my_cook, active_device, caplog):
    def device_polls():
        yield active_device

    m_share_my_cook.poll = AsyncMock(side_effect=device_polls)
    caster = broadcaster.Broadcaster(app)
    await caster.prepare()
    await caster.run()

    m_publish.assert_awaited_with(
        app,
        'brewcast/history', {
            'key': 'ShareMyCook',
            'data': {
                'MyDeviceName': {
                    'Active': 1,
                    'Fan_Duty[%]': 48,
                    'Values': {
                        'pit[DegC]': 50,
                        'food1[DegC]': 65,
                        'food2[DegC]': 66,
                    },
                    'Targets': {
                        'pit[DegC]': 55,
                        'food1[DegC]': 95,
                        'food2[DegC]': 96,
                    },
                }
            },
        }
    )

    assert 'Polling intervals: Active 0.01s, Inactive 0.05s' in caplog.messages
    assert 'name: test_app' in caplog.messages
    assert 'topic: brewcast/history' in caplog.messages


async def test_device_state_change(app, m_share_my_cook, active_device, inactive_device, device_id, caplog):
    responses = (
        [inactive_device],
        [active_device],
        [inactive_device],
    )
    m_share_my_cook.poll = AsyncMock(side_effect=responses)

    caster = broadcaster.Broadcaster(app)

    await caster.prepare()
    await caster.run()
    assert f'New device MyDeviceName({device_id}) is OFFLINE' in caplog.messages

    caplog.clear()
    await caster.run()
    assert f'Device MyDeviceName({device_id}) transitioned from OFFLINE to ONLINE' in caplog.messages
    assert 'Changing polling interval from 0.05s to 0.01s' in caplog.messages

    caplog.clear()
    await caster.run()
    assert f'Device MyDeviceName({device_id}) transitioned from ONLINE to OFFLINE' in caplog.messages
    assert 'Changing polling interval from 0.01s to 0.05s' in caplog.messages
