from requests import Response
from typing import NamedTuple

# Type tags a requests.Response with the seconds (as a float) elapsed to retrieve it
TimedResponse = NamedTuple('TimedResponse', [('response', Response), ('seconds_elapsed', float)])
