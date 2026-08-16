# Harness

Read when a run touches a database, an external service, or spawns processes.

## Resolve the target first

The worst data loss does not come from a dangerous command. It comes from a
harmless one pointed at the wrong thing. A test suite that drops and recreates
its database is correct behaviour; it becomes an incident when the configured
test database name is the working one.

So before running, resolve and print what the run will actually act on. Django:

```
DJANGO_SETTINGS_MODULE=<project>.settings.test python -c "import django;\
django.setup();from django.db import connections as c;\
print(c['default'].creation._get_test_db_name())"
```

Expect a name that starts with `test_` and differs from every working store.
Same idea elsewhere: print the resolved schema, bucket, index, or directory and
read it before you run, not after.

If a guard exists because someone already lost data here, it is part of the
harness. Do not disable it to make a run proceed.

## Isolation

- Fixed seeds. A suite that passes only sometimes has told you something; note
  it rather than re-running until green.
- External calls mocked. Real endpoints make the suite a client of someone
  else's uptime, and a writer to someone else's data.
- Never point tests at a working or development store. Test stores are separate
  stores, not the same store with a convention around it.
- Fixtures are inputs, not knobs. Changing one to make an assertion pass
  changes what the test means.

## Teardown

- Terminate every process the run started, including ones a failing test left
  behind.
- Remove temp files, containers, and volumes it created.
- Check before reporting: a hung process from a "finished" run is why the next
  run behaves strangely.

## Backup before risk

Before a migration or a bulk operation on data: take the dump first. A backup
made after the operation records the damage. For code the equivalent is
`git stash create` or a `checkpoint/...` branch (G14).
