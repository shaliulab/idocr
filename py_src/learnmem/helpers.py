# Standard library imports
import datetime
import logging
import os
import random

# Third party imports
import bottle
import git

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class MachineDatetime(datetime.datetime):
    r"""
    A convenient class that expands datetime.datetime
    by having an extra format which matches the one
    IDOC uses to write timestamps in folders and files.
    """

    def machineformat(self):
        year = self.year
        month = self.month
        day = self.day

        hour = self.hour
        minute = self.minute
        second = self.second

        date = "%s-%s-%s" % (str(year).zfill(4), str(month).zfill(2), str(day).zfill(2))
        clock_time = "%s-%s-%s" % (str(hour).zfill(2), str(minute).zfill(2), str(second).zfill(2))
        return "%s_%s" % (date, clock_time)


def hours_minutes_seconds(timedelta):
    return timedelta.seconds//3600, (timedelta.seconds//60)%60, timedelta.seconds%60

def iso_format(dhm):
    hours, minutes, seconds = dhm
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


def get_server(port):
    r"""
    This checks if the patch has to be applied or not. We check if bottle has declared cherootserver
    we assume that we are using cherrypy > 9.
    If cherootserver is not available, trick bottle to think cheroot actually is a cherrypy server,
    modifies the server_names allowed in bottle so we use cheroot in background.
    """



    server = "cheroot"
    try:
        from bottle import CherootServer # pylint: disable=import-outside-toplevel

    except ImportError as error:
        server = "cherrypy"

        class CherootServer(bottle.ServerAdapter):

            def __init__(self, *args, **kwargs):

                self._server = None
                super().__init__(*args, **kwargs)

            def run(self, handler): # pragma: no cover
                from cheroot import wsgi # pylint: disable=import-outside-toplevel
                from cheroot.ssl import builtin # pylint: disable=import-outside-toplevel
                self.options['bind_addr'] = (self.host, self.port)
                self.options['wsgi_app'] = handler
                certfile = self.options.pop('certfile', None)
                keyfile = self.options.pop('keyfile', None)
                chainfile = self.options.pop('chainfile', None)
                self._server = wsgi.Server(**self.options)
                if certfile and keyfile:
                    server.ssl_adapter = builtin.BuiltinSSLAdapter(
                        certfile, keyfile, chainfile
                    )

                try:
                    import warnings
                    warnings.filterwarnings(
                        action="ignore", message="unclosed",
                        category=ResourceWarning
                    )
                    self._server.start()
                finally:
                    self._server.stop()

            def stop(self):
                self._server.stop()

        bottle.server_names["cherrypy"] = CherootServer(host='0.0.0.0', port=port)
        logger.info("Cherrypy version is bigger than 9, we have to change to cheroot server")
        # logger.warning(error)

    return server

def get_machine_id(path="/etc/machine-id"):
    r"""
    Reads the machine ID
    This file should be present on any linux installation
    When missing, it is automatically generated by the OS.
    """

    with open(path, 'r') as filehandle:
        info = filehandle.readline().rstrip()
    return info

def get_commit_version(commit):
    '''
    '''
    commit_date = datetime.datetime.utcfromtimestamp(commit.committed_date)
    commit_date_formatted = commit_date.strftime('%Y-%m-%d %H:%M:%S')

    return {
        "id": str(commit),
        "date": commit_date_formatted
        }

def get_git_version():
    r"""
    Return the current git version
    """
    working_directory = os.getcwd()

    while working_directory != "/":
        try:
            repo = git.Repo(working_directory)
            commit = repo.commit()
            return get_commit_version(commit)

        except git.InvalidGitRepositoryError:
            working_directory = os.path.dirname(working_directory)

    raise Exception("Not in a git Tree")


def get_machine_name(path="/etc/machine-name"):
    """
    Reads the machine name
    This file will be present only on a real ethoscope
    When running locally, it will generate a randome name
    """

    if os.path.exists(path):
        with open(path, 'r') as filehandle:
            info = filehandle.readline().rstrip()
        return info

    else:
        return 'LEARNMEMORY_' + str(random.randint(100, 999))
