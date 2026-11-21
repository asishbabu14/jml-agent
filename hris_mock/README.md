# Synthetic HR feed

`employees.csv` is invented. Addresses are `@lab.example`. There are no dates of birth, no government ids, and no health information. Status `hired`, `mover`, and `leaving` are the rows `make demo` turns into joiner, mover, and leaver requests. Active rows are already in the mock directory.

```bash
python -m hris_mock.emit_event
```
