
import time
from typing import Union, Optional


import requests
from requests.exceptions import HTTPError


class GQLError(Exception):
    """ Special error type for GQL exceptions """
    pass


class GQLClient(object):

    def __init__(self, url: str, headers: Optional[dict] = None,
                 retries: int = 0, retry_wait_time: Union[int, float] = 0):
        """ Create object for interfacing with a GraphQL API

        Parameters
        ----------
        url : str
            URL of the GraphQL API to query
        headers : Optional[dict], optional
            Dictionary representing headers to be included in the API requests,
            default is None (no headers)
        retries : int, optional
            Number of times to re-attempt the post request should the prior
            attempt respond with a 503 error before raising an exception,
            default is 0 (no re-attempts)
        retry_wait_time : Union[int, float], optional
            Amount of time, in seconds, to wait after a 503 error response
            prior to re-attempting, default is 0
        """
        self.url = url
        self.headers = {} if headers is None else headers
        self.retries = retries
        self.retry_wait_time = retry_wait_time

    def execute(self, query: str,
                variables: Optional[dict] = None,
                retries: Optional[int] = None,
                retry_wait_time: Union[int, float, None] = None) -> dict:
        """ Query a GraphQL API, optionally multiple times in the event of
            repeated 503 error responses, raise an exception if the response
            includes a GraphQL error, otherwise return the query result

        Parameters
        ----------
        query : str
            GraphQL query string, can be a query or a mutation
        variables : dict, optional
            Dictionary of variables to be passed to the GraphQL query,
            default is None
        retries : int, optional
            Number of times to re-attempt the post request should the prior
            attempt respond with a 503 error before raising an exception,
            will use the client-specified retries if not included
        retry_wait_time : Union[int, float], optional
            Amount of time, in seconds, to wait after a 503 error response
            prior to re-attempting, will use the client-specified wait time
            if not included

        Returns
        -------
        dict
            JSON-style dictionary containing the result of the GraphQL query

        Raises
        ------
        GQLError
            Exception if the response includes a GraphQL error message
        """
        retries = retries or self.retries
        retry_wait_time = retry_wait_time or self.retry_wait_time

        json = {'query': query}
        if variables is not None:
            json['variables'] = variables

        attempt = 0
        while True:
            response = requests.post(self.url, json=json, headers=self.headers)
            if (response.status_code in [requests.codes.UNAVAILABLE, 
                                         requests.codes.TOO_MANY, 
                                         requests.codes.GATEWAY_TIMEOUT]
                and attempt < retries):
                # If response is a 503 error and there are
                # retries remaining
                attempt += 1
                time.sleep(retry_wait_time)
                continue
            else:
                # Otherwise raise error for a bad response (or proceed if ok)
                response.raise_for_status()
            break

        result = response.json()

        if 'errors' in result:
            msg = '; '.join(
                        '{} ({})'.format(
                            e['message'],
                            ','.join('L{line}C{column}'.format(**p)
                                     for p in e['locations'])
                        ) for e in result['errors']
                    )
            raise GQLError(msg)

        return result['data']


class StartggClient(GQLClient):

    API_VERSION = 'alpha'
    API_URL = 'https://api.start.gg/gql/{}'.format(API_VERSION)

    def __init__(self, token: str = None, **kwargs):
        super().__init__(self.API_URL, **kwargs)
        if token is not None:
            self.headers['Authorization'] = 'Bearer {}'.format(token)
