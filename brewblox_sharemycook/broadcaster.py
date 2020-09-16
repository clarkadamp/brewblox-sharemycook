import asyncio
import os

from aiohttp import web
from brewblox_service import (brewblox_logger, features, mqtt, repeater)

from brewblox_sharemycook.controllers import State, Controller
from brewblox_sharemycook.share_my_cook import ShareMyCook

LOGGER = brewblox_logger(__name__)


class Broadcaster(repeater.RepeaterFeature):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = None
        self.active_interval = None
        self.inactive_interval = None
        self.current_interval = None
        self.topic = None
        self.share_my_cook = None
        self.device_states = {}

    async def prepare(self):
        self.name = self.app['config']['name']
        self.active_interval = self.app['config']['active_poll_interval']
        self.inactive_interval = self.app['config']['inactive_poll_interval']
        self.current_interval = self.inactive_interval
        self.topic = self.app['config']['history_topic']

        username = self.app['config'].get('username') or os.environ['USERNAME']
        password = self.app['config'].get('password') or os.environ['PASSWORD']
        self.share_my_cook = ShareMyCook(self.app, username, password)

        LOGGER.info(f"Polling intervals: Active {self.active_interval}s, Inactive {self.inactive_interval}s")
        LOGGER.info(f"name: {self.name}")
        LOGGER.info(f"topic: {self.topic}")

    @property
    def active_devices(self) -> bool:
        return State.ONLINE in self.device_states.values()

    @property
    def interval(self) -> int:
        """
        If devices are offline, reduce the polling interval to self.inactive_interval

        :return: poll interval
        """
        new_interval = self.active_interval if self.active_devices else self.inactive_interval
        if self.current_interval != new_interval:
            LOGGER.info(f"Changing polling interval from {self.current_interval}s to {new_interval}s")
            self.current_interval = new_interval
        return self.current_interval

    async def run(self) -> None:
        data = {}
        for device_data in await self.share_my_cook.poll():
            self.report_device_state_changes(device_data)
            data.update(device_data.serialize())

        LOGGER.debug(f"Publishing: ShareMyCook: {data}")
        try:
            await mqtt.publish(
                self.app,
                self.topic,
                {
                    'key': f"ShareMyCook",
                    'data': data
                }
            )
        finally:
            await asyncio.sleep(self.interval)

    def report_device_state_changes(self, device_data: Controller) -> None:
        device_id = device_data.device_id
        if device_id not in self.device_states:
            LOGGER.info(f"New device {device_data.name}({device_id}) is {device_data.state.value}")
            self.device_states[device_id] = device_data.state

        if self.device_states[device_id] != device_data.state:
            LOGGER.info(
                f"Device {device_data.name}({device_id}) transitioned "
                f"from {self.device_states[device_id].value} "
                f"to {device_data.state.value}")
            self.device_states[device_id] = device_data.state


def setup(app: web.Application) -> None:
    features.add(app, Broadcaster(app))


def get_broadcaster(app: web.Application) -> Broadcaster:
    return features.get(app, Broadcaster)
