import uuid
from datetime import datetime

import pytest

from brewblox_sharemycook.controllers import controller_types, TemperatureUnits


@pytest.fixture
def device_id():
    return uuid.uuid4()


@pytest.fixture
def timestamp():
    return datetime.now()


@pytest.fixture
def timestamp_string(timestamp):
    return timestamp.isoformat()


@pytest.fixture
def sample_response(model, online, timestamp_string):
    return {
        'UltraQ': {
            'bbqGuruDeviceModel': 'UltraQ',
            'customerDeviceName': 'MyDeviceName',
            'indicateStatus': 'good' if online else 'offline',
            'pitActualTemp': 106,
            'pitTargetTemp': 107,
            'food1ActualTemp': 67,
            'food1TargetTemp': 97,
            'food2ActualTemp': 66,
            'food2TargetTemp': 96,
            'food3ActualTemp': -500,  # Disconnected
            'food3TargetTemp': 95,
            'currentOutputPercent': 78,
            'lastDeviceCommunicationTimestamp': timestamp_string
        }
    }[model]


ultra_q_online_deg_c = {
    'MyDeviceName': {
        'Active': 1,
        'Fan_Duty[%]': 78,
        'Values': {
            'pit[DegC]': 106,
            'food1[DegC]': 67,
            'food2[DegC]': 66,
        },
        'Targets': {
            'pit[DegC]': 107,
            'food1[DegC]': 97,
            'food2[DegC]': 96,
        },
    }
}

ultra_q_online_deg_f = {
    'MyDeviceName': {
        'Active': 1,
        'Fan_Duty[%]': 78,
        'Values': {
            'pit[DegF]': 106,
            'food1[DegF]': 67,
            'food2[DegF]': 66,
        },
        'Targets': {
            'pit[DegF]': 107,
            'food1[DegF]': 97,
            'food2[DegF]': 96,
        },
    }
}

ultra_q_offline = {
    'MyDeviceName': {
        'Active': 0,
    }
}


@pytest.mark.parametrize('model, temperature_units, online, expected_serialized', [
    ('UltraQ', TemperatureUnits.CELSIUS, True, ultra_q_online_deg_c),
    ('UltraQ', TemperatureUnits.FAHRENHEIT, True, ultra_q_online_deg_f),
    ('UltraQ', TemperatureUnits.FAHRENHEIT, False, ultra_q_offline),
])
def test_controller(model, temperature_units, sample_response, expected_serialized):
    controller = controller_types[model].from_json(
        device_id=device_id, units=temperature_units, json=sample_response
    )
    assert controller.serialize() == expected_serialized
