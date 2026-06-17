# ============================================================
# main.py — The entry point for our FastAPI backend server
# Think of this file as the "front desk" of our application.
# Every request that comes in goes through here first.
# ============================================================


# FastAPI is the framework we use to build our backend server.
# A framework is like a set of pre-built tools so we don't have
# to build everything from scratch ourselves.
from fastapi import FastAPI

# CORSMiddleware solves a browser security rule called CORS.
# By default, browsers block a website on one port (React on 3000)
# from talking to a server on a different port (FastAPI on 8000).
# This middleware is like a permission slip that says:
# "Hey browser, it's okay — these two are allowed to talk."
from fastapi.middleware.cors import CORSMiddleware


# ============================================================
# CREATE THE APP
# ============================================================

# This line creates our FastAPI application.
# Think of `app` as the restaurant itself — everything else
# (routes, middleware, etc.) gets attached to it.
app = FastAPI()


# ============================================================
# CORS MIDDLEWARE — Allowing React to talk to FastAPI
# ============================================================

# Here we attach the CORS permission slip to our app.
# Without this, the browser would throw a security error
# when React tries to fetch data from our backend.
app.add_middleware(
    CORSMiddleware,

    # allow_origins: Which websites are allowed to talk to us?
    # We're only allowing our React app running on port 3000.
    allow_origins=["http://localhost:3000"],

    # allow_credentials: Can the request include login cookies?
    # Yes — we'll need this later when we add user authentication.
    allow_credentials=True,

    # allow_methods: Which HTTP methods are allowed?
    # "*" means all of them (GET, POST, PUT, DELETE, etc.)
    # GET = read data, POST = create data,
    # PUT = update data, DELETE = remove data
    allow_methods=["*"],

    # allow_headers: Which request headers are allowed?
    # "*" means all of them. Headers carry extra info about
    # a request, like what format the data is in.
    allow_headers=["*"],
)


# ============================================================
# ROUTES — The endpoints users (or React) can call
# ============================================================

# A route is like a specific desk in our front office.
# Each route has a URL path and a function that runs when
# someone visits that path.

# @app.get("/health") means:
# "When someone sends a GET request to /health, run this function."
# GET means we're just reading/checking something, not changing it.
@app.get("/health")
def health_check():
    # This function returns a simple message to confirm
    # that the server is running correctly.
    # It's like asking "are you alive?" and getting "yes" back.
    # We'll use this to test our backend is working.
    return {"status": "ok"}