# Brewblox ShareMyCook

This brewblox module pulls metrics from BBQGurus https://sharemycook.com/

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

Metric should start to appear
