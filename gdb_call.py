############################
### Main callable script
############################
def main():
    import argparse
    import logging
    import coloredlogs
    import sys
    from pathlib import Path
    from LeMDT.lmdt_utils import setup_logging
    from LeMDT.interface import Interface
    from LeMDT import PROJECT_DIR

    DURATION = 200 * 60
    coloredlogs.install()

    # Set up general settings

    #print('VIDEO resolution is %d by %d !' % (cap.get(3), cap.get(4)))
    #print('FPS is: {}'.format(int(cap.get(5))))

    setup_logging()
    log = logging.getLogger(__name__)

    interface = Interface(
        arduino = True, track = True,
        port = "/dev/ttyACM0",
        camera = "pylon", video = None, config = Path(PROJECT_DIR, 'config.yaml').__str__(),
        reporting = False, output_path = ".",
        duration = DURATION, gui = "tkinter"
    )

    interface.start()

main()
