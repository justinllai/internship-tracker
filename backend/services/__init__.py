# "services" = business logic that isn't tied to HTTP.
# Routers (routers/*.py) handle requests/responses and call into
# these modules. Keeping them separate means we can unit-test the
# logic without spinning up a web server.
