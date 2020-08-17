import json
import logging
import urllib.request

from idoc.decorators import retry
from idoc.debug import ScanException
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False
formatter = logging.Formatter('%(message)s')
fh = logging.FileHandler('requests.log')
fh.setFormatter(formatter)
logger.addHandler(fh)

class HTTPMixin:

    @retry(ScanException, tries=3, delay=1, backoff=1)
    def _get_json(self, url, timeout=5, post_data=None, log='info'):

        try:
            if log == 'info':
                logger.info(url)
                logger.info('DATA: %s', post_data)
            elif log == 'debug':
                pass
                # logger.info(url)

            req = urllib.request.Request(url, data=post_data, headers={'Content-Type': 'application/json'})
            
            try:
                file_handle = urllib.request.urlopen(req, timeout=timeout)
            except Exception as error:
                logger.warning('Could not carry out operation')
                logger.warning('URL: %s', url)
                logger.warning('DATA: %s', post_data)
                
                return

            message = file_handle.read()
            if not message:
                # logging.error("URL error whist scanning url: %s. No message back." % self._id_url)
                raise ScanException("No message back")
            try:
                resp = json.loads(message)
                return resp
            except ValueError:
                # logging.error("Could not parse response from %s as JSON object" % self._id_url)
                raise ScanException("Could not parse Json object")

        except urllib.error.HTTPError as error:
            logger.warning('Cannot open URL %s', url)
            raise ScanException("Error" + str(error.code))
            #return e

        except urllib.error.URLError as error:
            logger.warning('Cannot open URL %s', url)
            raise ScanException("Error" + str(error.reason))
            #return e

        except Exception as error:
            raise ScanException("Unexpected error" + str(error))
