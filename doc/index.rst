.. Buildbot capability documentation master file, created by
   sphinx-quickstart on Wed Mar 30 14:39:57 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Buildbot capability's documentation!
===============================================

Contents:

.. toctree::
   :maxdepth: 2

This package for buildbot >= 0.9 allows to declare that workers have
capabilities, and produce ``BuilderConfig`` instances accordingly.

- capabilities have a name (e.g. 'postgresql'), an optional version
  (9.5) and optional additional parameters (such as port=5433)

- one declares what are each worker's capabilities as part of the
  worker config.
  A given capability name can occur on a worker several times, but a
  given (name, version) must appear exactly once.

- it allows to express that a given build requires a given capability
  (e.g, access to a docker registry, presence of some helper program)

- it can spawn several :py:class:`BuilderConfigs` according to available capabilities on the full swarm, in a configurable way
  (e.g., one for each postgresql version greater than 9.3 or for 9.1)

- at build time, the optional capability parameters are available as
  properties, so that, e.g., a build running integration tests against
  postgresql 9.5 would be able to use the right port (5433 in the
  example above) to access the database.

Complete example
~~~~~~~~~~~~~~~~
In this example, we'll show how to spawn build variants according to
Python and PostgreSQL versions.

Worker capabilities are expressed in a big property::

  from buildbot.plugins import worker
  Worker = worker.Worker

  c = BuildMasterConfig
  c['workers'] = [Worker('wk1', 'pwd', properties={'capability':
    {'postgresql': {'9.2': {},
                    '9.3': {'port': '5433', 'bin': '/usr/lib/pg93'},
                    '9.4': {'port': '5434', 'bin': '/usr/lib/pg94'}
                    },
     'python': {'2.7': {},
                '2.6': {'bin': '/usr/local/bin/python2.6'},
                },
     'ssh_key': None,   # this one is just a marker, no versions, no options
    })

We need to supply information about how to use some of these capabilities::

  capabilities = {
      'python': {
          'version_prop': 'py_version',
          'abbrev': 'py',
          'environ': {'PYTHONBIN': '%(cap(bin):-python)s'},
      },
      'postgresql': {
          'version_prop': 'pg_version',
          'abbrev': 'pg',
          'environ': {'PGPORT': '%(cap(port):-)s',
                      'PATH': '%(cap(bin):-)s',
                      },
          }
      }

Now we are ready to dispatch a :class:`BuildFactory`::

  from anybox.buildbot.capability.dispatcher import BuilderDispatcher
  from anybox.buildbot.capability.version import Version, VersionFilter
  dispatcher = BuilderDispatcher(c['workers'], capabilities)
  factory = BuildFactory()

If we need to use information about used capabilities within the build, we
can add a special step::

  env = dispatcher.set_properties_make_environ(
      factory,
      ('python', 'postgresql')
  )

The subsequent build steps can then access information about
capability versions and options as properties ``py_version``,
``pg_version``, but also ``cap_pg_port``, ``cap_python_bin``, and the
returned ``env`` is a ready-made :class:`dict` with
:class:`Interpolate` values, that can be used for environment
variables.


Now let's create the :class:`BuilderConfig` instances::

  configs = dispatcher.make_builders(
      'bname', factory,
      build_for=[VersionFilter('postgresql', ['>', Version(9, 2)]),
                 VersionFilter('python', ()),
                 ],
      build_requires=[VersionFilter('ssh_key', ())]
  )

The configured builders in that example will have names such as
``bname-pg9.3-py2.7`` for all available PostgreSQL versions greater
than 9.2 and all available Python version.

To each one, all the workers that have the ``ssh_key`` capability and
the selected Python and PostgreSQL versions will be attached.

Of course this is far more streamlined if called through a layer
implementing a declarative configuration.

This package does not supply such a declarative layer, because that may involve
much more that capability filtering and dispatching.
There are facilities to parse versions and version filters from
strings (see :py:mod:`anybox.buildbot.capability.version`), yet the
format is somewhat naive and should not be considered to be stable.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

