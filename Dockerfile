FROM kbase/sdkbase2:python
MAINTAINER KBase Developer
# -----------------------------------------
# In this section, you can install any system dependencies required
# to run your App.  For instance, you could place an apt-get update or
# install line here, a git checkout to download code, or run any other
# installation scripts.

# RUN apt-get update

# Here we install a python coverage tool and an
# https library that is out of date in the base image.

RUN pip install coverage
# Lock the dependency to prevent the write_gpickle AttributeError
RUN rm -rf /miniconda/lib/python3.6/site-packages/ruamel* && pip install --upgrade pip && pip install "networkx<3.0" "swiglpk==5.0.10" "python-libsbml==5.19.2" "cobra==0.26.2"

# update security libraries in the base image
RUN pip install cffi --upgrade \
    && pip install pyopenssl --upgrade \
    && pip install ndg-httpsclient --upgrade \
    && pip install pyasn1 --upgrade \
    && pip install requests --upgrade \
    && pip install 'requests[security]' --upgrade

# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

#------------edited----yash
RUN rm -rf /miniconda/lib/python3.6/site-packages/ruamel* && pip install --upgrade pip && pip install "networkx<3.0" "swiglpk==5.0.10" "python-libsbml==5.19.2" "cobra==0.26.2"


RUN pip install -e /kb/module/lib/metquest_core

#------------end-----yash
RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
