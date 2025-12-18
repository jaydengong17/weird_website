import random
import time
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import modal

image = modal.Image.debian_slim().pip_install("fastapi[standard]")

app = modal.App("weird-website", image=image)

gong_rng_volume = modal.Volume.from_name("gong-rng-inventories", create_if_missing=True)
gong_rng_probabilities = [0.000001, 0.000002, 0.000002, 0.000005, 0.00004, 0.00005, 0.0002, 0.0004, 0.0005, 0.0008, 0.001, 0.002, 0.005, 0.01, 0.08, 0.166666666666, 0.33333333333333, 0.4]


@app.function(
    min_containers=1,
    allow_concurrent_inputs=1000,
    volumes={"/gongrng": gong_rng_volume}
)
@modal.asgi_app()
def fastapi_app():    
    web_app = FastAPI()
    
    # Add CORS middleware
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://jaydengong.com", "http://127.0.0.1:4000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # create things if it doesn't exist
    os.makedirs("/gongrng/clientdata/", exist_ok=True)
    
    @web_app.post("/")
    def roll(req: Request):
        # do random generation
        result = getRollRank()

        # create response
        response = JSONResponse(
            {
                "result": result,
            },
        )

        # cookies
        session_key = req.cookies.get("session_key", None)

        # if cookie doesn't exist yet or not in file (new client)
        if not checkKeyDataExists(session_key):
            # length 32 string, hopefully no collisions
            session_key = f"{round(time.time()):b>12}a{random.random():b<19}"
            # add cookie
            response.set_cookie(
                key="session_key",
                value=session_key,
                httponly=False,
                secure=True,
                domain="jaydengong17--weird-website-fastapi-app.modal.run",
                samesite="none",
            )
            # create file
            with open("/gongrng/clientdata/" + session_key, "w") as f:
                f.write("0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")

        # add result to storage
        with open("/gongrng/clientdata/" + session_key, "r+") as f:
            addResultToData(f, result)

        return response
    
    def getRollRank():
        # rng
        rng = random.random()
        result = -1

        # keep testing for inside probability, accounting for possible precision errors
        while (rng > 0.00000001):
            rng -= gong_rng_probabilities[result + 1]
            result += 1
        
        return result

    def checkKeyDataExists(session_key):
        # check if it's none
        if (session_key == None):
            return False
        # check if file exists
        return os.path.exists("/gongrng/clientdata/" + session_key)

    def addResultToData(client_file, roll_result):
        raw_file_data = client_file.read()
        client_data = [0] * 18
        try:
            # split and convert to ints
            client_data = [int(i) for i in raw_file_data.strip().split(",")]
        except:
            # if somehow something goes wrong and it's not all ints
            print("client file is wrong, somehow. the file looks like: " + client_data)
            return
        
        # increment roll result
        client_data[roll_result] += 1

        # clear and rewrite file
        client_file.seek(0)
        # guaranteed to be shorter (also make everything a string so clientdata works)
        client_file.write(",".join([str(i) for i in client_data]))

    return web_app
