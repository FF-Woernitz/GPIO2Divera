import json
import sys
import requests
import time
import RPi.GPIO as GPIO
import logging
from logging.handlers import RotatingFileHandler
import threading

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
    logger.info(config_json)
    logger.info(type(config_json))
    return config_json

def get_conf(config_json):
    conf = {"gpio_pins": [], "api_url": "", "api_key": "", "request": "", "pullup": False, "max_tries": 3}
    conf["gpio_pins"] = config_json["gpio_pins"]
    conf["api_url"] = config_json["api_endpoint"]
    conf["api_key"] = config_json["api_key"]
    conf["request"] = config_json["request"]
    conf["pullup"] = config_json["pullup"]
    conf["max_tries"] = config_json["max_tries"]
    logger.warning("configuration:")
    logger.warning(conf)

    for index, x in enumerate(conf['gpio_pins']):
        if x[1] == 0:
            conf['gpio_pins'][index][1] = GPIO.LOW
        if x[1] == 1:
            conf['gpio_pins'][index][1] = GPIO.HIGH

    return conf


def call_api(conf):
    logger.info("calling api")
    for api_try in range(conf["max_tries"]):
        r = requests.post(conf["api_url"] + conf["api_key"], json=conf["request"])
        logger.info("Request-URL:")
        logger.info(r.url)
        logger.info("Request-answer:")
        logger.info(r.content)
        logger.info("Status_code:")
        logger.info(r.status_code)
        if r.status_code == 200:
            logger.warning("Successfully send alert")
            return
        else:
            logger.error("Failed to send alert. Try: " + str(api_try + 1))
            time.sleep(5)
            continue

def setup(conf):
    GPIO.setmode(GPIO.BCM)
    if conf["pullup"]:
        gpioPullMode = GPIO.PUD_UP
    else:
        gpioPullMode = GPIO.PUD_DOWN
    for x in conf['gpio_pins']:
        GPIO.setup(x[0], GPIO.IN, pull_up_down=gpioPullMode)

def check_state(conf):
    countNotDefault = 0
    for x in conf['gpio_pins']:
        gpioState = GPIO.input(x[0])
        logger.debug("GPIO {} defaultstate: {} state: {}".format(x[0],x[1], gpioState))
        if gpioState != x[1]:
            logger.info("GPIO {} not default value".format(x[0]))
            countNotDefault += 1
    if countNotDefault >= len(conf['gpio_pins']):
        return True
    else:
        return False

def monitor_gpio(conf):
    logger.warning("Starting Monitoring")
    last_pin_state = False
    while True:
        pin_state = check_state(conf)
        if last_pin_state == False and pin_state == True:
            logger.warning("GPIO switched to alarm state")
            logger.warning("Received Alert")
            startNewAlarmThread(conf)
        if last_pin_state == True and pin_state == False:
            logger.warning("GPIO switched to normal state")
        last_pin_state = pin_state
        time.sleep(0.01)

def startNewAlarmThread(conf):
    x = threading.Thread(target=call_api, args=(conf,))
    x.start()

def main():
    logger.warning("GPIO2Divera started")
    conf_file = read_json("config.json")
    conf = get_conf(conf_file)
    if len(conf["gpio_pins"]) == 0:
        raise Exception("No GPIO pins configured")
    if conf["api_key"] == "YOURKEY" or conf["api_key"] == "":
        raise Exception("No API key configured")

    setup(conf)

    monitor_gpio(conf)

main()
