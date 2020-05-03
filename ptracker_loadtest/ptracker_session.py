import time

from requests import Response, Session

from .utils.custom_types import TimedResponse


class PTrackerSession(Session):

    """HTTP session for PTracker. Subclasses Session so it can be used like one (e.g. '.get()', '.post()', etc)
    """

    def __init__(self, root_url: str):
        """Constructor for PTrackerSession

        :param root_url: the web server's root url (e.g. 'http://localhost:8000
        """
        super().__init__()
        self.root_url = root_url

    def authenticate(self, user: str, password: str) -> None:
        """Authenticates the session to PTracker with given credentials.

        :param user: the username
        :param password: the password
        :returns: None
        """
        login_url = f'{self.root_url}/login/'
        # With new Session, login to server with csrf token scraped from login form
        self.get(login_url)
        data = {
            'username': user,
            'password': password,
            'csrfmiddlewaretoken': self.cookies.get('csrftoken', None)
        }
        self.post(login_url, data)

    def get_index(self) -> TimedResponse:
        """GET's the PTracker index page

        If redirected from index, we will return the final, landing page

        :return: the TimedResponse from the index
        """
        start_time = time.time()
        index_page = self.get(self.root_url)
        elapsed = time.time() - start_time
        return TimedResponse(response=index_page, seconds_elapsed=elapsed)
