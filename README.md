# Brewblox ShareMyCook

This [brewblox](https://brewblox.netlify.app/) module pulls metrics from BBQGurus https://sharemycook.com/

It will auto discover your controllers and units and publish them to a new `ShareMyCook` category

## How to use

Add the following to your brewblox `.env`
```
SMC_USER=<sharemycook-username>
SMC_PASS=<sharemycook-password>
```

Add the following to your brewblox `docker-compose.yml`
```
  sharemycook:
    image: clarkadamp/brewblox-sharemycook:develop
    restart: unless-stopped
    environment:
    - USERNAME=$SMC_USER
    - PASSWORD=$SMC_PASS
```

then run:
```
brewblox-ctl restart
```

Metrics should start to appear under the `ShareMyCook` category.


## Development

Setup `poetry`
```shell
curl -sSL https://install.python-poetry.org | python3 -
export PATH="~/.local/bin:$PATH"
poetry install
```

Run locally
```
poetry run python3 -m brewblox_sharemycook --mqtt-host=10.17.10.1 --mqtt-protocol=mqtt --username <username> --password <password>
```


To run tests
```shell
poetry run python3 -m pytest test
```
