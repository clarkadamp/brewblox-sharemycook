import datetime
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Union, Any

controller_types = {}


def controller(cls):
    controller_types[cls.__name__] = cls
    return cls


class State(Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class TemperatureUnits(Enum):
    CELSIUS = "CELSIUS"
    FAHRENHEIT = "FAHRENHEIT"


@dataclass
class Controller(ABC):
    DISCONNECTED_TEMP = -500

    device_id: uuid.UUID
    name: str
    state: State
    units: TemperatureUnits
    last_update: datetime.datetime

    @property
    def temp_units(self) -> str:
        return "Deg{}".format("C" if self.units == TemperatureUnits.CELSIUS else "F")

    @classmethod
    @abstractmethod
    def from_json(
        cls, device_id: uuid.UUID, units: TemperatureUnits, json: Mapping[str, Union[str, int]]
    ) -> 'Controller':
        """
        Instantiate an instance from ShareMyCook JSON data
        """

    @abstractmethod
    def serialize(self) -> Mapping[str, Any]:
        """
        Return this controllers data ready for MQTT
        """


@controller
@dataclass
class UltraQ(Controller):
    pit_temp: float
    pit_target: float
    food1_temp: float
    food1_target: float
    food2_temp: float
    food2_target: float
    food3_temp: float
    food3_target: float
    fan_duty: int

    @classmethod
    def from_json(
        cls, device_id: uuid.UUID, units: TemperatureUnits, json: Mapping[str, Union[str, int]]
    ) -> 'UltraQ':
        return cls(
            device_id=device_id,
            name=json['customerDeviceName'],
            state=State.ONLINE if "good" in json['indicateStatus'].lower() else State.OFFLINE,
            units=units,
            pit_temp=float(json['pitActualTemp']),
            pit_target=float(json['pitTargetTemp']),
            food1_temp=float(json['food1ActualTemp']),
            food1_target=float(json['food1TargetTemp']),
            food2_temp=float(json['food2ActualTemp']),
            food2_target=float(json['food2TargetTemp']),
            food3_temp=float(json['food3ActualTemp']),
            food3_target=float(json['food3TargetTemp']),
            fan_duty=json['currentOutputPercent'],
            last_update=datetime.datetime.fromisoformat(json["lastDeviceCommunicationTimestamp"])
        )

    def serialize(self) -> Mapping[str, Any]:
        values = {}
        targets = {}

        data = {
            "Active": 1 if self.state == State.ONLINE else 0,
        }

        if self.state == State.ONLINE:
            data["Fan_Duty[%]"] = self.fan_duty if self.state == State.ONLINE else None
            data["Targets"] = targets
            data["Values"] = values

            for probe_name in ['pit', 'food1', 'food2', 'food3']:
                probe_temp = getattr(self, f"{probe_name}_temp")
                if probe_temp > self.DISCONNECTED_TEMP:
                    values[f"{probe_name}[{self.temp_units}]"] = probe_temp
                    targets[f"{probe_name}[{self.temp_units}]"] = getattr(self, f"{probe_name}_target")

        return {self.name: data}
