# coding: utf-8
#
# This file is taken from flask-testing extension by Dan Jacob
# https://github.com/rduplain/flask-testing
#
# This file is licensed under BSD 3-clause modified license. Here's the license:
#
#    Copyright (c) 2010 by Dan Jacob.
#
#    Some rights reserved.
#
#    Redistribution and use in source and binary forms, with or without
#    modification, are permitted provided that the following conditions are
#    met:
#
#    * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#
#    * The names of the contributors may not be used to endorse or
#    promote products derived from this software without specific
#    prior written permission.
#
#    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#    A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#    OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#    LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#    THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest
from werkzeug import cached_property

# Use Flask's preferred JSON module so that our runtime behavior matches.
from flask import json_available
if json_available:
    from flask import json

try:
    # we'll use signals for template-related tests if
    # available in this version of Flask
    import blinker
    from flask import template_rendered
    _is_signals = True
except ImportError:
    _is_signals = False

__all__ = ["TestCase", ]


class ContextVariableDoesNotExist(Exception):
    pass


class JsonResponseMixin(object):
    """
    Mixin with testing helper methods
    """
    @cached_property
    def json(self):
        if not json_available:
            raise NotImplementedError
        return json.loads(self.data)


def _make_test_response(response_class):
    class TestResponse(response_class, JsonResponseMixin):
        pass

    return TestResponse


class TestCase(unittest.TestCase):

    def create_app(self):
        """
        Create your Flask app here, with any
        configuration you need.
        """
        raise NotImplementedError

    def __call__(self, result=None):
        """
        Does the required setup, doing it here
        means you don't have to call super.setUp
        in subclasses.
        """
        try:
            self._pre_setup()
            super(TestCase, self).__call__(result)
        finally:
            self._post_teardown()

    def _pre_setup(self):
        self.app = self._ctx = None

        self.app = self.create_app()

        self._orig_response_class = self.app.response_class
        self.app.response_class = _make_test_response(self.app.response_class)

        self.client = self.app.test_client()

        self._ctx = self.app.test_request_context()
        self._ctx.push()

        self.templates = []
        if _is_signals:
            template_rendered.connect(self._add_template)

    def _add_template(self, app, template, context):
        self.templates.append((template, context))

    def _post_teardown(self):
        if self._ctx is not None:
            self._ctx.pop()
        if self.app is not None:
            self.app.response_class = self._orig_response_class
        if _is_signals:
            template_rendered.disconnect(self._add_template)

    def assertTemplateUsed(self, name):
        """
        Checks if a given template is used in the request.
        Only works if your version of Flask has signals
        support (0.6+) and blinker is installed.

        :versionadded: 0.2
        :param name: template name
        """
        if not _is_signals:
            raise RuntimeError("Signals not supported")

        for template, context in self.templates:
            if template.name == name:
                return True
        raise AssertionError("template %s not used" % name)

    assert_template_used = assertTemplateUsed

    def get_context_variable(self, name):
        """
        Returns a variable from the context passed to the
        template. Only works if your version of Flask
        has signals support (0.6+) and blinker is installed.

        Raises a ContextVariableDoesNotExist exception if does
        not exist in context.

        :versionadded: 0.2
        :param name: name of variable
        """
        if not _is_signals:
            raise RuntimeError("Signals not supported")

        for template, context in self.templates:
            if name in context:
                return context[name]
        raise ContextVariableDoesNotExist

    def assertContext(self, name, value):
        """
        Checks if given name exists in the template context
        and equals the given value.

        :versionadded: 0.2
        :param name: name of context variable
        :param value: value to check against
        """

        try:
            self.assertEqual(self.get_context_variable(name), value)
        except ContextVariableDoesNotExist:
            self.fail("Context variable does not exist: %s" % name)

    assert_context = assertContext

    def assertRedirects(self, response, location):
        """
        Checks if response is an HTTP redirect to the
        given location.

        :param response: Flask response
        :param location: relative URL (i.e. without **http://localhost**)
        """
        self.assertTrue(response.status_code in (301, 302))
        self.assertEqual(response.location, "http://localhost" + location)

    assert_redirects = assertRedirects

    def assertStatus(self, response, status_code):
        """
        Helper method to check matching response status.

        :param response: Flask response
        :param status_code: response status code (e.g. 200)
        """
        self.assertEqual(response.status_code, status_code)

    assert_status = assertStatus

    def assert200(self, response):
        """
        Checks if response status code is 200

        :param response: Flask response
        """

        self.assertStatus(response, 200)

    assert_200 = assert200

    def assert400(self, response):
        """
        Checks if response status code is 400

        :versionadded: 0.2.5
        :param response: Flask response
        """

        self.assertStatus(response, 400)

    assert_400 = assert400

    def assert401(self, response):
        """
        Checks if response status code is 401

        :versionadded: 0.2.1
        :param response: Flask response
        """

        self.assertStatus(response, 401)

    assert_401 = assert401

    def assert403(self, response):
        """
        Checks if response status code is 403

        :versionadded: 0.2
        :param response: Flask response
        """

        self.assertStatus(response, 403)

    assert_403 = assert403

    def assert404(self, response):
        """
        Checks if response status code is 404

        :param response: Flask response
        """

        self.assertStatus(response, 404)

    assert_404 = assert404

    def assert405(self, response):
        """
        Checks if response status code is 405

        :versionadded: 0.2
        :param response: Flask response
        """

        self.assertStatus(response, 405)

    assert_405 = assert405
