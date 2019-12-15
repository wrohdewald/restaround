FROM python:3-slim

COPY restic /usr/bin

# restaround selftest scans the correct source file for tests but does not find any.
# works outside of docker.

COPY strace /usr/bin
COPY libunwind.so.8 /usr/lib
COPY libunwind-ptrace.so.0 /usr/lib
COPY libunwind-x86_64.so.8 /usr/lib

RUN pip install --upgrade pip
RUN pip install --index-url https://test.pypi.org/pypi/ --extra-index-url https://pypi.org/simple restaround

# comment the next line if you want to run the tests manually

RUN restaround selftest
