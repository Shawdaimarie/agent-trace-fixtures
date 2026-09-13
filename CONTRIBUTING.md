# Contributing

Explain the importer behavior being tested and why it matters. Keep fixtures
small, original, synthetic, and free of real credentials or personal information.
Link to the relevant public specification when claiming standards behavior.

Add the fixture generator, manifest expectation, and a regression test. Run:

```sh
python3 build_fixtures.py
python3 tracecheck.py
python3 -m unittest discover -s tests -v
```

Do not alter an expectation solely to make a failing checker pass. Describe
compatibility changes and remaining limits in the pull request. Maintainer review
is required before merging. Passing tests are not standards certification.
