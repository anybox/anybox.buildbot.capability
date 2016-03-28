A static capability system for buildbot
=======================================

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

- it spawns several BuilderConfigs according to available capabilities on the full swarm, in a configurable way
  (e.g., one for each postgresql version greater than 9.3 or for 9.1)

- at build time, the optional capability parameters are available as
  properties, so that, e.g., a build running integration tests against
  postgresql 9.5 would be able to use the right port (5433 in the
  example above) to access the database.

