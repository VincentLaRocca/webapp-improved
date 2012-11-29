# -*- coding: utf-8 -*-
"""
    webapp2_extras.xsrf
    ===================

    Helpers for defending against cross-site request forgery attacks.

    :copyright: 2011 by tipfy.org.
    :license: Apache Sotware License, see LICENSE for details.
"""

__author__ = 'John Lockwood'

import base64
import hmac
import hashlib
import time

class XSRFException(Exception):
    pass

class XSRFTokenMalformed(XSRFException):
    pass

class XSRFTokenExpiredException(XSRFException):
    pass

class XSRFTokenInvalid(XSRFException):
    pass

class XSRFToken(object):
    _DELIMITER = '|'

    def __init__(self, user_id, secret, current_time=None):
        """Initializes the XSRFToken object.

        :param user_id:
            A string representing the user that the token will be valid for.
        :param secret:
            A string containing a secret key that will be used to seed the
            hash used by the :class:`XSRFToken`.
        :param current_time:
            An int representing the number of seconds since the epoch. Will be
            used by `verify_token_string` to check for token expiry. If `None`
            then the current time will be used.
        """
        self.user_id = user_id
        self.secret = secret
        if current_time is None:
          self.current_time = int(time.time())
        else:
          self.current_time = int(current_time)

    def _digest_maker(self):
        return hmac.new(self.secret, digestmod=hashlib.sha1)

    def generate_token_string(self, action=None):
        """Generate a hash of the given token contents that can be verified.

        :param action:
            A string representing the action that the generated hash is valid
            for. This string is usually a URL.
        :returns:
            A string containing the hash contents of the given `action` and the
            contents of the `XSRFToken`. Can be verified with
            `verify_token_string`. The string is base64 encoded so it is safe
            to use in HTML forms without escaping.
        """
        digest_maker = self._digest_maker()
        digest_maker.update(self.user_id)
        digest_maker.update(self._DELIMITER)
        if action:
            digest_maker.update(action)
            digest_maker.update(self._DELIMITER)

        digest_maker.update(str(self.current_time))
        return base64.b64encode(self._DELIMITER.join([digest_maker.hexdigest(),
                                                      str(self.current_time)]))

    def verify_token_string(self,
                            token_string,
                            action=None,
                            timeout=None,
                            current_time=None):
        """Generate a hash of the given token contents that can be verified.

        :param token_string:
            A string containing the hashed token (generated by
            `generate_token_string`).
        :param action:
            A string containing the action that is being verified.
        :param timeout:
            An int or float representing the number of seconds that the token
            is valid for. If None then tokens are valid forever.
        :current_time:
            An int representing the number of seconds since the epoch. Will be
            used by to check for token expiry if `timeout` is set. If `None`
            then the current time will be used.
        :raises:
            XSRFTokenMalformed if the given token_string cannot be parsed.
            XSRFTokenExpiredException if the given token string is expired.
            XSRFTokenInvalid if the given token string does not match the
            contents of the `XSRFToken`. 
        """
        try:
          decoded_token_string = base64.b64decode(token_string)
        except TypeError:
          raise XSRFTokenMalformed()

        split_token = decoded_token_string.split(self._DELIMITER)
        if len(split_token) != 2:
          raise XSRFTokenMalformed()

        try:
          token_time = int(split_token[1])
        except ValueError:
          raise XSRFTokenMalformed()

        if timeout is not None:
          if current_time is None:
            current_time = time.time()
          # If an attacker modifies the plain text time then it will not match
          # the hashed time so this check is sufficient.
          if (token_time + timeout) < current_time:
            raise XSRFTokenExpiredException()

        expected_token = XSRFToken(self.user_id, self.secret, token_time)
        expected_token_string = expected_token.generate_token_string(action)
        if token_string != expected_token_string:
          raise XSRFTokenInvalid()
