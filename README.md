# Vestaboard Server

Fun uses for the [Vestaboard](https://www.vestaboard.com/).  It is also used to linked to my Home Automation system easier since it exposes the sending a message function easier.

## Environment variables for the docker image
PORT (Defaults to 3020 if not set) for web listening port

VESTABOARD_API_KEY = API Key from Vestaboard Installable API Key Creation

VESTABOARD_API_SECRET = API Secret from Vestaboard Installable API Key Creation


### Enabled a random quote generator sourced from a mysql DB
SAYING_DB_HOST

SAYING_DB_NAME

SAYING_DB_PASS

SAYING_DB_USER


DB Schema is just a table named `sayings` with a column named `quote`.  I also put `source` as a column in case I wanted to display it later.
