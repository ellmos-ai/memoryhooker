# Contributing

This public repository owns the `memoryhooker` runtime and its behavioral tests.
Private deployments consume a pinned public revision; private settings, memory
data and historical evidence are not published as part of the package.

Use a separate private extension only for actual private executable behavior.
It must not shadow `memoryhooker` or duplicate the public core. The historical
private repository retains its Git history and can act as a consumer fixture.
Never force-push one repository's history over the other.

Start changes from the public default branch, check `git remote -v`, run the
behavioral suite and test the built wheel in a clean environment outside the
checkout. Preserve local-first output policies and default start suppression.
Do not commit personal memories, host configuration, credentials or transcripts.
