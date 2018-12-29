"""
Copyright (c) 2015 Functional Software, Inc and individual contributors.
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
    this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
    following disclaimer in the documentation and/or other materials provided with the distribution.

    3. Neither the name of the Raven nor the names of its contributors may be used to endorse or promote products
    derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os.path


def fetch_git_sha(path, head=None):
    if not head:
        head_path = os.path.join(path, '.git', 'HEAD')
        if not os.path.exists(head_path):
            raise Exception(
                'Cannot identify HEAD for git repository at %s' % (path,))

        with open(head_path, 'r') as fp:
            head = str(fp.read()).strip()

        if head.startswith('ref: '):
            head = head[5:]
            revision_file = os.path.join(
                path, '.git', *head.split('/')
            )
        else:
            return head
    else:
        revision_file = os.path.join(path, '.git', 'refs', 'heads', head)

    if not os.path.exists(revision_file):
        if not os.path.exists(os.path.join(path, '.git')):
            raise Exception(
                '%s does not seem to be the root of a git repository' % (path,))

        # Check for our .git/packed-refs' file since a `git gc` may have run
        # https://git-scm.com/book/en/v2/Git-Internals-Maintenance-and-Data-Recovery
        packed_file = os.path.join(path, '.git', 'packed-refs')
        if os.path.exists(packed_file):
            with open(packed_file) as fh:
                for line in fh:
                    line = line.rstrip()
                    if line and line[:1] not in ('#', '^'):
                        try:
                            revision, ref = line.split(' ', 1)
                        except ValueError:
                            continue
                        if ref == head:
                            return str(revision)

        raise Exception(
            'Unable to find ref to head "%s" in repository' % (head,))

    with open(revision_file) as fh:
        return str(fh.read()).strip()
