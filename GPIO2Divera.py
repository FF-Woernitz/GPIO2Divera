import json
import sys
import requests
import time
import RPi.GPIO as GPIO
import logging
from logging.handlers import RotatingFileHandler

logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")
logger = logging.getLogger()

fileHandler = RotatingFileHandler("GPIO2Divera.log", maxBytes=20000, backupCount=10)
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)
logger.setLevel(logging.DEBUG)

def read_json(file):
    with open(file) as json_file:
        config_json = json.load(json_file)
    logger.debug(config_json)
    logger.debug(type(config_json))
    return config_json

def get_conf(config_json):
    conf = {"input_pin": "", "api_url": "", "api_key": "", "request": "", "invert_gpio": False, "max_tries": 3}
    conf["input_pin"] = config_json["gpio_pin"]
    conf["api_url"] = config_json["api_endpoint"]
    conf["api_key"] = config_json["api_key"]
    conf["request"] = config_json["request"]
    conf["invert_gpio"] = config_json["invert_gpio"]
    conf["max_tries"] = config_json["max_tries"]
    logger.info("configuration:")
    logger.info(conf)
    return conf


def call_api(conf):
    logger.debug("calling api")
    for api_try in range(conf["max_tries"]):
        r = requests.post(conf["api_url"] + conf["api_key"], json=conf["request"])
        logger.debug("Request-URL:")
        logger.debug(r.url)
        logger.debug("Request-answer:")
        logger.debug(r.content)
        logger.debug("Status_code:")
        logger.debug(r.status_code)
        if r.status_code == 200:
            logger.info("Successfully send alert")
            return
        else:
            logger.warning("Failed to send alert. Try: " + str(api_try + 1))
            time.sleep(5)
            continue

def setup(input_pin):
    # RPi.GPIO Layout verwenden (wie doku)
    logger.debug("Setting GPIO layout as docu")
    GPIO.setmode(GPIO.BCM)
    # Set up the GPIO channels - one input
    logger.debug("Set up the GPIO channels - one input")
    GPIO.setup(input_pin, GPIO.IN)

def check_state(conf):
    if GPIO.input(conf['input_pin']) == GPIO.LOW:
        pin_state = False
    elif GPIO.input(conf['input_pin']) == GPIO.HIGH:
        pin_state = True
    else:
        return False
    if conf["invert_gpio"]:
        pin_state = not pin_state
    #logger.debug("GPIO-state:" + str(pin_state)) #DEBUG
    return pin_state

def monitor_gpio(conf):
    logger.info("Starting Monitoring")
    last_pin_state = False
    while True:
        pin_state = check_state(conf)
        if last_pin_state == False and pin_state == True:
            logger.info("GPIO switched to alarm state")
            logger.info("Received Alert")
            call_api(conf)
        if last_pin_state == True and pin_state == False:
            logger.info("GPIO switched to normal state")
        last_pin_state = pin_state
        time.sleep(0.5)

def main():
    logger.info("GPIO2Divera started")
    conf_file = read_json("config.json")
    conf = get_conf(conf_file)

    setup(conf['input_pin'])

    monitor_gpio(conf)

main()
