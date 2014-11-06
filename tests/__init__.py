# Copyright 2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import time

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
    from unittest2 import SkipTest
else:
    import unittest
    from unittest import SkipTest


def assert_eventually(condition, message=None, max_tries=60):
    for i in range(max_tries):
        if condition():
            break
        time.sleep(1)
    else:
        raise AssertionError(message or "Failed after %d attempts." % max_tries)
