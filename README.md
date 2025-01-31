# Home automation server

Just a collection of uses and connectors for my home automation uses.

One such use is for [Vestaboard](https://www.vestaboard.com/).

## Environment variables for the docker image
PORT (Defaults to 3020 if not set) for web listening port

VESTABOARD_API_KEY = API Key from Vestaboard Installable API Key Creation

VESTABOARD_API_SECRET = API Secret from Vestaboard Installable API Key Creation


### Enabled a random quote generator sourced from a mysql DB
SAYING_DB_ENABLE = 1 (1 for enabled, 0 for disabled (default))

SAYING_DB_HOST

SAYING_DB_NAME

SAYING_DB_PASS

SAYING_DB_USER

SAYING_DB_PORT


DB Schema is just 2 tables named `sfw_quotes` and `nsfw_quotes` with a column named `quote`.  I also put `source` as a column in case I wanted to display it later.
