import logging
import sys
import time
import subprocess

from libs.dnacLib import dnac_loop


log = logging.getLogger("wifininja")
log.setLevel(logging.DEBUG)
log_format = logging.Formatter(
    fmt="%(asctime)s (%(name)s) %(levelname)s:%(message)s",
    datefmt="%m/%d/%Y %H:%M:%S"
)
log_console = logging.StreamHandler()
log_console.setLevel(logging.DEBUG)
log_console.setFormatter(log_format)

log.addHandler(log_console)

def run():

    subprocess.run(["echo", "DNAC collector : Running"])
    try:
        while True:
            dnac_loop()
            time.sleep(1)
                
    except KeyboardInterrupt:
        subprocess.run(["clear"])
        subprocess.run(["echo", "DNAC collector : Stopped"])
        sys.exit()


if __name__ == "__main__":

    run()