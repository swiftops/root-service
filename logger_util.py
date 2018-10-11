import logging

logging.basicConfig(filename='./log/app.log',
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)


def get_logger():
    logger = logging.getLogger(__name__)
    return logger


