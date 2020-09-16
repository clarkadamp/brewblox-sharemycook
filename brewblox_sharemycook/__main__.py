"""
Example of how to import and use the brewblox service
"""
from argparse import ArgumentParser

from brewblox_service import brewblox_logger, http, mqtt, scheduler, service

from brewblox_sharemycook import broadcaster

LOGGER = brewblox_logger(__name__)


def create_parser(default_name='brewblox-sharemycook') -> ArgumentParser:
    # brewblox-service has some default arguments
    # We can add more arguments here before sending the parser back to brewblox-service
    # The parsed values for all arguments are placed in app['config']
    # For documentation see https://docs.python.org/3/library/argparse.html
    parser: ArgumentParser = service.create_parser(default_name=default_name)

    # This will be used by publish_example
    # Note how we specify the type as float
    parser.add_argument('--active-poll-interval',
                        help='Interval (in seconds) between polling when active devices detected. [%(default)s]',
                        type=int,
                        default=2)
    parser.add_argument('--inactive-poll-interval',
                        help='Interval (in seconds) between polling when no active devices detected. [%(default)s]',
                        type=int,
                        default=300)
    parser.add_argument('--username', help='Share My Cook Username')
    parser.add_argument('--password', help='Share My Cook Password')

    return parser


def main() -> None:
    app = service.create_app(parser=create_parser())

    scheduler.setup(app)
    mqtt.setup(app)
    http.setup(app)
    broadcaster.setup(app)

    service.furnish(app)
    service.run(app)


if __name__ == '__main__':
    main()
